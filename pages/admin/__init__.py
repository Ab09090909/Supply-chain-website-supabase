"""Admin pages."""
from .dashboard import render_admin_dashboard
from .users import render_admin_users
from .fraud import render_admin_fraud
from .profile import render_admin_profile

__all__ = [
    "render_admin_dashboard",
    "render_admin_users",
    "render_admin_fraud",
    "render_admin_profile",
]
