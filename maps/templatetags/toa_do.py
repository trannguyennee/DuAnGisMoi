from django import template
from django.utils.safestring import mark_safe

from maps.security import points_to_js

register = template.Library()


@register.filter
def toa_do_json(raw):
    """Dùng trong <script>: {{ p.du_lieu_toa_do|toa_do_json }} (thay cho |safe)."""
    # Đã review: points_to_js chỉ xuất mảng số đã chuẩn hoá và thoát < > &
    return mark_safe(points_to_js(raw))  # nosec B308 B703
