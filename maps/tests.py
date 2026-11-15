"""Kiểm thử bảo mật — chạy: python manage.py test maps"""
import json
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from PIL import Image

from .models import PhanAnh
from .security import csv_safe, parse_points, points_to_js

VALID_POINTS = json.dumps([{'lat': 10.77, 'lng': 106.69}])


def png_file(name='a.png'):
    buf = BytesIO()
    Image.new('RGB', (2, 2)).save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


class SecurityHelpersTests(SimpleTestCase):
    def test_parse_points_valid(self):
        self.assertEqual(parse_points(VALID_POINTS), [{'lat': 10.77, 'lng': 106.69}])

    def test_parse_points_rejects_bad_input(self):
        for raw in ['[]', '{}', 'alert(1)', '[{"lat": 999, "lng": 0}]', '[{"lat": "x", "lng": 1}]']:
            with self.assertRaises((ValueError, TypeError)):
                parse_points(raw)

    def test_points_to_js_never_outputs_markup(self):
        out = points_to_js('</script><script>alert(1)</script>')
        self.assertEqual(out, '[]')
        self.assertNotIn('<', points_to_js(VALID_POINTS))

    def test_points_to_js_legacy_format(self):
        self.assertEqual(json.loads(points_to_js('10.5, 106.7')), [{'lat': 10.5, 'lng': 106.7}])

    def test_csv_safe(self):
        self.assertEqual(csv_safe('=HYPERLINK("http://x")'), '\'=HYPERLINK("http://x")')
        self.assertEqual(csv_safe('Ngập nước'), 'Ngập nước')


class StoredXssTests(TestCase):
    def test_malicious_coordinates_are_not_rendered_as_script(self):
        payload = '[];</script><script>alert(document.cookie)</script>'
        PhanAnh.objects.create(tieu_de='x', mo_ta='y', du_lieu_toa_do=payload)
        res = self.client.get(reverse('map_home'))
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('<script>alert(document.cookie)', res.content.decode())


class SubmitReportTests(TestCase):
    url = '/luu-phan-anh/'

    def test_valid_report_is_saved_with_normalized_points(self):
        res = self.client.post(self.url, {'tieu_de': 'Ngập', 'mo_ta': 'sâu 30cm', 'points_data': VALID_POINTS, 'hinh_anh': png_file()})
        self.assertEqual(res.status_code, 200, res.content)
        pa = PhanAnh.objects.get()
        self.assertEqual(json.loads(pa.du_lieu_toa_do), [{'lat': 10.77, 'lng': 106.69}])
        self.assertIsNotNone(pa.vi_tri)

    def test_invalid_points_rejected(self):
        res = self.client.post(self.url, {'tieu_de': 'x', 'points_data': '[];alert(1)'})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(PhanAnh.objects.exists())

    def test_non_image_upload_rejected(self):
        evil = SimpleUploadedFile('x.png', b'<html><script>alert(1)</script>', content_type='image/png')
        res = self.client.post(self.url, {'tieu_de': 'x', 'points_data': VALID_POINTS, 'hinh_anh': evil})
        self.assertEqual(res.status_code, 400)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class AdminActionTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staff', password='S3cure-pass!', is_staff=True)
        self.user = User.objects.create_user('dan', password='S3cure-pass!')
        self.victim = User.objects.create_user('victim', password='S3cure-pass!')
        self.pa = PhanAnh.objects.create(tieu_de='x', mo_ta='y', du_lieu_toa_do=VALID_POINTS, nguoi_gui=self.user)

    def test_state_changing_admin_urls_reject_get(self):
        self.client.force_login(self.staff)
        for url in [reverse('duyet_phan_anh', args=[self.pa.id]), reverse('admin_xoa_phan_anh', args=[self.pa.id]),
                    reverse('khoa_user', args=[self.victim.id]), reverse('xoa_user', args=[self.victim.id])]:
            self.assertEqual(self.client.get(url).status_code, 405, url)
        self.assertTrue(User.objects.filter(id=self.victim.id, is_active=True).exists())

    def test_non_staff_cannot_delete_users(self):
        self.client.force_login(self.user)
        self.client.post(reverse('xoa_user', args=[self.victim.id]))
        self.assertTrue(User.objects.filter(id=self.victim.id).exists())

    def test_staff_can_approve_and_delete_any_report(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('duyet_phan_anh', args=[self.pa.id]))
        self.pa.refresh_from_db()
        self.assertEqual(self.pa.trang_thai, 'dang_xu_ly')
        self.client.post(reverse('admin_xoa_phan_anh', args=[self.pa.id]))
        self.assertFalse(PhanAnh.objects.filter(id=self.pa.id).exists())

    def test_user_cannot_delete_someone_elses_report(self):
        self.client.force_login(self.victim)
        res = self.client.post(reverse('xoa_phan_anh', args=[self.pa.id]))
        self.assertEqual(res.status_code, 404)

    def test_owner_can_delete_pending_report(self):
        self.client.force_login(self.user)
        self.client.post(reverse('xoa_phan_anh', args=[self.pa.id]))
        self.assertFalse(PhanAnh.objects.filter(id=self.pa.id).exists())

    def test_export_requires_staff_and_escapes_formulas(self):
        PhanAnh.objects.create(tieu_de='=cmd|"/c calc"!A1', mo_ta='y', du_lieu_toa_do=VALID_POINTS)
        self.assertEqual(self.client.get(reverse('export_excel')).status_code, 302)
        self.client.force_login(self.staff)
        body = self.client.get(reverse('export_excel')).content.decode('utf-8-sig')
        self.assertIn('\'=cmd', body)


class LoginRedirectTests(TestCase):
    def setUp(self):
        User.objects.create_user('dan', password='S3cure-pass!')

    def test_external_next_is_ignored(self):
        res = self.client.post(reverse('login') + '?next=https://evil.example/phish',
                               {'username': 'dan', 'password': 'S3cure-pass!'})
        self.assertRedirects(res, reverse('map_home'), fetch_redirect_response=False)

    def test_internal_next_is_kept(self):
        res = self.client.post(reverse('login') + '?next=/ho-so-cua-toi/',
                               {'username': 'dan', 'password': 'S3cure-pass!'})
        self.assertRedirects(res, '/ho-so-cua-toi/', fetch_redirect_response=False)


class AreaScanApiTests(TestCase):
    def test_bad_params_return_400(self):
        res = self.client.get(reverse('api_quet_vung'), {'lat': 'abc'})
        self.assertEqual(res.status_code, 400)

    def test_finds_nearby_reports(self):
        self.client.post('/luu-phan-anh/', {'tieu_de': 'Ngập', 'points_data': VALID_POINTS})
        res = self.client.get(reverse('api_quet_vung'), {'lat': 10.77, 'lng': 106.69, 'radius': 100})
        self.assertEqual(res.json()['tong_so'], 1)
