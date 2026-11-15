"""Hàm tiện ích bảo mật dùng chung (không phụ thuộc GIS để dễ test).

- parse_points: kiểm tra & chuẩn hoá dữ liệu tọa độ người dùng gửi lên
- points_to_js: xuất tọa độ ra JSON an toàn để nhúng vào <script> (chống XSS)
- csv_safe: chống CSV/Excel formula injection khi xuất báo cáo
"""
import json
import math

MAX_POINTS = 100


def _to_point(lat, lng):
    lat, lng = float(lat), float(lng)
    if not (math.isfinite(lat) and math.isfinite(lng)):
        raise ValueError('Tọa độ không hợp lệ')
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError('Tọa độ nằm ngoài phạm vi')
    return {'lat': lat, 'lng': lng}


def parse_points(raw):
    """Nhận chuỗi JSON dạng [{"lat": .., "lng": ..}, ...] và trả về list đã chuẩn hoá.

    Ném ValueError nếu dữ liệu sai định dạng. Chỉ giữ lại đúng 2 khoá lat/lng
    dạng số, nên không thể chèn mã JavaScript qua trường này.
    """
    data = json.loads(raw)
    if not isinstance(data, list) or not data:
        raise ValueError('Cần ít nhất một điểm')
    if len(data) > MAX_POINTS:
        raise ValueError(f'Tối đa {MAX_POINTS} điểm')
    points = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError('Điểm không hợp lệ')
        points.append(_to_point(item.get('lat'), item.get('lng')))
    return points


def points_to_js(raw):
    """Chuyển dữ liệu tọa độ đã lưu (kể cả dữ liệu cũ) thành JSON an toàn cho <script>.

    Dữ liệu lỗi hoặc độc hại sẽ trả về "[]" thay vì được chèn nguyên văn.
    """
    points = []
    if raw:
        try:
            points = parse_points(raw)
        except (ValueError, TypeError):
            # Định dạng cũ "lat, lng"
            try:
                lat, lng = str(raw).split(',')[:2]
                points = [_to_point(lat.strip(), lng.strip())]
            except (ValueError, TypeError):
                points = []
    text = json.dumps(points)
    # Thoát các ký tự có thể đóng thẻ <script> hoặc mở HTML
    return text.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def csv_safe(value):
    """Thêm dấu ' trước ô bắt đầu bằng ký tự công thức để Excel không thực thi."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value
