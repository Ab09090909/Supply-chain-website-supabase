"""Utils package - shared UI helpers, constants, formatting, storage, theme."""
from .ui import (
    page_header,
    role_badge,
    show_success_toast,
    show_error_message,
    show_info_message,
    metric_card,
    stat_card,
    sidebar_user_card,
)
from .constants import (
    ROLE_OPTIONS, ROLE_DESCRIPTIONS, ROLE_COLORS,
    UNIT_OPTIONS, UNIT_SHORT, QUALITY_GRADES, CERTIFICATION_OPTIONS,
    PAYMENT_TERMS, PRODUCT_CATEGORIES, CURRENCY_CODE, CURRENCY_SYMBOL,
)
from .helpers import format_currency, format_datetime, generate_order_number, format_unit
from .storage import upload_image, render_image_uploader
from .theme import init_theme, render_theme_toggle, apply_theme_css

__all__ = [
    "page_header",
    "role_badge",
    "show_success_toast",
    "show_error_message",
    "show_info_message",
    "metric_card",
    "stat_card",
    "sidebar_user_card",
    "ROLE_OPTIONS",
    "ROLE_DESCRIPTIONS",
    "ROLE_COLORS",
    "UNIT_OPTIONS",
    "UNIT_SHORT",
    "QUALITY_GRADES",
    "CERTIFICATION_OPTIONS",
    "PAYMENT_TERMS",
    "PRODUCT_CATEGORIES",
    "CURRENCY_CODE",
    "CURRENCY_SYMBOL",
    "format_currency",
    "format_datetime",
    "format_unit",
    "generate_order_number",
    "upload_image",
    "render_image_uploader",
    "init_theme",
    "render_theme_toggle",
    "apply_theme_css",
]
