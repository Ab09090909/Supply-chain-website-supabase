"""Merchant pages."""
from .dashboard import render_merchant_dashboard
from .orders import render_merchant_orders
from .profile import render_merchant_profile

__all__ = [
    "render_merchant_dashboard",
    "render_merchant_orders",
    "render_merchant_profile",
]
