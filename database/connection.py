"""Auth package - login, signup, password reset, session, verification."""
from .session import (
    is_logged_in,
    get_current_user,
    get_current_role,
    set_session,
    clear_session,
    require_role,
)
from .service import (
    sign_up,
    sign_in,
    sign_out,
    request_password_reset,
    update_password,
)
from .verification import (
    is_user_verified,
    get_verification_status,
    render_verification_page,
)

__all__ = [
    "is_logged_in",
    "get_current_user",
    "get_current_role",
    "set_session",
    "clear_session",
    "require_role",
    "sign_up",
    "sign_in",
    "sign_out",
    "request_password_reset",
    "update_password",
    "is_user_verified",
    "get_verification_status",
    "render_verification_page",
]
