"""Producer pages."""
from .dashboard import render_producer_dashboard
from .inventory import render_producer_inventory
from .orders import render_producer_orders
from .profile import render_producer_profile

__all__ = [
    "render_producer_dashboard",
    "render_producer_inventory",
    "render_producer_orders",
    "render_producer_profile",
]
