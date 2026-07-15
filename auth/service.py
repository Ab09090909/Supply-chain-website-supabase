"""
Auth service - thin wrapper around Supabase Auth + profiles table.

All functions return (success: bool, data_or_error: str|dict).

NOTE: database.connection is imported LAZILY inside each function so that
a broken database module doesn't prevent the auth pages from rendering.
"""
from __future__ import annotations

from typing import Tuple, Optional, Dict, Any
import streamlit as st

from .session import set_session, clear_session


VALID_ROLES = ("producer", "merchant", "customer", "admin")


def _get_client():
    """Lazy import of the Supabase client."""
    from database.connection import get_supabase_client
    return get_supabase_client()


def _get_admin_client():
    """Lazy import of the admin Supabase client."""
    from database.connection import get_supabase_admin_client
    return get_supabase_admin_client()


def sign_up(
    email: str,
    password: str,
    full_name: str,
    role: str,
    phone: str = "",
    location: str = "",
    company: str = "",
) -> Tuple[bool, str]:
    """Create a new auth user + profile row (via trigger)."""
    if role not in VALID_ROLES:
        return False, f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"

    try:
        client = _get_client()
        response = client.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "role": role,
                        "phone": phone,
                        "location": location,
                        "company": company,
                    }
                },
            }
        )
        user = response.user
        if not user:
            return False, "Signup failed - no user returned."

        # Fetch the profile row created by the handle_new_user trigger.
        # Use a small retry loop because the trigger runs in a separate
        # transaction and may not be visible immediately.
        profile_data = None
        for attempt in range(3):
            try:
                profile = (
                    client.table("profiles")
                    .select("*")
                    .eq("id", user.id)
                    .maybe_single()
                    .execute()
                )
                profile_data = profile.data if profile else None
                if profile_data:
                    break
            except Exception:
                pass
            import time
            time.sleep(0.3)

        # If the trigger didn't create the profile, try to create it manually.
        # This is a recovery path — the trigger SHOULD have done it, but if
        # it failed (e.g. RLS, search_path issue, etc.) we don't want to
        # leave the user stranded with an auth account but no profile.
        if not profile_data:
            try:
                admin_client = _get_admin_client()
                admin_client.table("profiles").insert({
                    "id": user.id,
                    "email": email,
                    "full_name": full_name,
                    "role": role,
                    "phone": phone,
                    "location": location,
                    "company": company,
                }).execute()
                profile = (
                    client.table("profiles")
                    .select("*")
                    .eq("id", user.id)
                    .single()
                    .execute()
                )
                profile_data = profile.data
            except Exception as insert_err:
                # Last resort: still log the user in, but warn them
                # their profile is incomplete.
                if response.session:
                    set_session(response.session.access_token, {
                        "id": user.id,
                        "email": email,
                        "full_name": full_name,
                        "role": role,
                        "phone": phone,
                        "location": location,
                        "company": company,
                    })
                    return True, (
                        "Account created, but profile setup was incomplete. "
                        f"Please contact admin. Detail: {insert_err}"
                    )
                return False, f"Account created but profile failed: {insert_err}"

        if not profile_data:
            return False, "Signup failed - profile could not be created."

        set_session(response.session.access_token, profile_data)
        return True, "Signup successful."
    except Exception as e:
        msg = str(e)
        if "already" in msg.lower() and "registered" in msg.lower():
            return False, "An account with this email already exists."
        if "Database error saving new user" in msg:
            return False, (
                "Supabase couldn't create your account. This is usually caused "
                "by a broken trigger. Run supabase_sql/fix_signup_trigger.sql in "
                "the Supabase SQL Editor, then try again. Detail: " + msg
            )
        return False, f"Signup failed: {msg}"


def sign_in(email: str, password: str) -> Tuple[bool, str]:
    """Login with email + password. Loads profile into session."""
    try:
        client = _get_client()
        response = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        user = response.user
        if not user:
            return False, "Login failed - no user returned."

        profile = (
            client.table("profiles")
            .select("*")
            .eq("id", user.id)
            .single()
            .execute()
        )
        profile_data = profile.data
        if not profile_data:
            return False, "Profile not found. Please contact admin."

        if not profile_data.get("is_active", True):
            return False, "Your account has been deactivated. Please contact admin."

        # Update last_login
        try:
            client.table("profiles").update(
                {"last_login": "now()"}
            ).eq("id", user.id).execute()
        except Exception:
            pass

        set_session(response.session.access_token, profile_data)
        return True, "Login successful."
    except Exception as e:
        msg = str(e).lower()
        if "invalid login" in msg or "invalid credentials" in msg:
            return False, "Invalid email or password."
        return False, f"Login failed: {e}"


def sign_out() -> None:
    """Clear local session + tell Supabase to revoke the token."""
    try:
        client = _get_client()
        client.auth.sign_out()
    except Exception:
        pass
    clear_session()


def request_password_reset(email: str) -> Tuple[bool, str]:
    """Send a password-reset email. Always returns success (security best practice)."""
    try:
        client = _get_client()
        app_url = st.secrets.get("APP_URL", "http://localhost:8501") if st else "http://localhost:8501"
        client.auth.reset_password_email(
            {"email": email, "options": {"redirect_to": f"{app_url}?page=reset-password"}}
        )
        return True, "If an account with that email exists, a reset link has been sent."
    except Exception as e:
        # Still return success to avoid leaking which emails are registered
        return True, "If an account with that email exists, a reset link has been sent."


def update_password(new_password: str) -> Tuple[bool, str]:
    """Update the current user's password (called after reset redirect)."""
    try:
        client = _get_client()
        client.auth.update_user({"password": new_password})
        return True, "Password updated. You can now log in with your new password."
    except Exception as e:
        return False, f"Password update failed: {e}"
