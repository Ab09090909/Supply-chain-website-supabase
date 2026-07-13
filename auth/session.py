"""
Session helpers - stores authenticated user info in st.session_state.

Streamlit has no built-in auth, so we keep the Supabase access_token
in session_state and rehydrate the user from it.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
import streamlit as st


def is_logged_in() -> bool:
    return bool(st.session_state.get("access_token"))


def get_current_user() -> Optional[Dict[str, Any]]:
    """Returns the cached user profile dict, or None."""
    return st.session_state.get("user")


def get_current_role() -> Optional[str]:
    user = get_current_user()
    return user.get("role") if user else None


def set_session(access_token: str, user: Dict[str, Any]) -> None:
    st.session_state["access_token"] = access_token
    st.session_state["user"] = user


def clear_session() -> None:
    for key in ("access_token", "user"):
        st.session_state.pop(key, None)


def require_role(*roles: str) -> bool:
    """Returns True if the current user has one of the allowed roles."""
    role = get_current_role()
    return role in roles if role else False
