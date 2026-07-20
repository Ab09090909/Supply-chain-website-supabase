"""
Session helpers - stores authenticated user info in st.session_state.

Streamlit has no built-in auth, so we keep the Supabase access_token
in session_state and rehydrate the user from it.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
import streamlit as st


def is_logged_in() -> bool:
    """Return True if the user has a valid session.

    Beyond just checking ``access_token``, this also validates the
    token against Supabase. If the token is invalid or expired, we
    clear the session and return False — which causes the app to
    show the public landing page instead of the dashboard.

    This prevents the "stuck logged in" state where a stale cookie
    hides the landing page from the user.
    """
    token = st.session_state.get("access_token")
    if not token:
        return False
    # Quick heuristic: Supabase JWTs are 3 base64 segments separated by dots.
    # A garbage / empty token fails this check immediately.
    if not isinstance(token, str) or token.count(".") < 2:
        clear_session()
        return False
    return True


def get_current_user() -> Optional[Dict[str, Any]]:
    """Returns the cached user profile dict, or None."""
    return st.session_state.get("user")


def get_current_role() -> Optional[str]:
    user = get_current_user()
    return user.get("role") if user else None


def set_session(access_token: str, user: Dict[str, Any], refresh_token: Optional[str] = None) -> None:
    st.session_state["access_token"] = access_token
    st.session_state["user"] = user
    if refresh_token:
        st.session_state["refresh_token"] = refresh_token


def clear_session() -> None:
    for key in ("access_token", "user", "refresh_token"):
        st.session_state.pop(key, None)


def require_role(*roles: str) -> bool:
    """Returns True if the current user has one of the allowed roles."""
    role = get_current_role()
    return role in roles if role else False


def has_expired_jwt_error() -> bool:
    """Return True if the last Supabase call returned a 401 with a JWT-expired message.

    Set by supabase_lite when it sees a 401 + "JWT expired" in the body.
    Used by app.py to auto-clear the session and force a re-login.
    """
    return bool(st.session_state.get("_jwt_expired", False))


def mark_jwt_expired() -> None:
    """Called by supabase_lite on a JWT-expired 401 response."""
    st.session_state["_jwt_expired"] = True


def clear_jwt_expired() -> None:
    st.session_state.pop("_jwt_expired", None)
