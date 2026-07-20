"""
App URL detection — works on Streamlit Cloud, Render, and localhost.

This module gives the rest of the app a single, reliable way to figure
out the public URL of the running instance. It's used to:

  • Build correct public card URLs (in QR codes and shared links)
  • Build correct password-reset email links
  • Show the right URL in the footer / business card / "share" buttons
  • Set the Open Graph / favicon base URL

The detection order is:

  1. ``APP_URL`` env var (explicit override — recommended on Render)
  2. ``NEXT_PUBLIC_APP_URL`` env var (Next.js convention — same value)
  3. ``RENDER_EXTERNAL_URL`` env var (auto-set by Render on every deploy)
  4. ``STREAMLIT_SHARING`` or streamlit.io hostname detection
  5. ``st.secrets["APP_URL"]`` (Streamlit Cloud secrets)
  6. ``http://localhost:8501`` (local dev fallback)

Why so many fallbacks?
  Different platforms set different env vars, and the user might have
  hard-coded their own ``APP_URL`` in secrets. We try them all so the
  app works correctly on any platform without code changes.
"""
from __future__ import annotations

import os
from typing import Optional

import streamlit as st


# The default — used when nothing else matches. localhost for dev,
# the public domain for "unknown" production.
_DEFAULT_URL = "http://localhost:8501"


def _from_st_secrets() -> Optional[str]:
    """Try to read APP_URL from Streamlit secrets.

    Wrapped in try/except because st.secrets raises if the file doesn't
    exist (which is the case on Render — Render uses env vars, not the
    secrets.toml file).
    """
    try:
        v = st.secrets.get("APP_URL")
        if v and isinstance(v, str) and v.strip():
            return v.strip().rstrip("/")
    except Exception:
        pass
    return None


def get_app_url(force_default: bool = False) -> str:
    """Return the public URL of the running app.

    Args:
        force_default: if True, return the localhost default without
                      trying to detect the platform. Useful for tests
                      or when you explicitly want the dev URL.

    Returns:
        The public URL (no trailing slash), e.g.
        ``https://eschain.yourdomain.com`` or ``http://localhost:8501``.

    The result is cached in ``st.session_state`` so we only do the
    env-var scan once per session. This is important because some env
    var lookups (like reading ``st.secrets``) can be slow.
    """
    if force_default:
        return _DEFAULT_URL

    # Cache the result in session_state (Streamlit reruns this on every
    # interaction, so we don't want to redo the env-var scan each time).
    cached = st.session_state.get("_app_url_cache")
    if cached:
        return cached

    # 1) Explicit APP_URL env var (best — set this in Render's env)
    url = os.environ.get("APP_URL")
    if url and url.strip():
        return _cache(url.strip().rstrip("/"))

    # 2) NEXT_PUBLIC_APP_URL (Next.js convention)
    url = os.environ.get("NEXT_PUBLIC_APP_URL")
    if url and url.strip():
        return _cache(url.strip().rstrip("/"))

    # 3) RENDER_EXTERNAL_URL (auto-set by Render — e.g.
    #    ``https://eschain-app.onrender.com``)
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if url and url.strip():
        return _cache(url.strip().rstrip("/"))

    # 4) Detect Streamlit Cloud (no env var, but we can sniff st.secrets
    #    or the special STREAMLIT_RUNTIME_ENV if it's set)
    if os.environ.get("STREAMLIT_RUNTIME_ENV") or os.environ.get("STREAMLIT_SHARING"):
        # On Streamlit Cloud the public URL is the one the user deployed to.
        # We can't get it from env, but st.secrets usually has it.
        url = _from_st_secrets()
        if url:
            return _cache(url)

    # 5) st.secrets APP_URL (covers Streamlit Cloud)
    url = _from_st_secrets()
    if url:
        return _cache(url)

    # 6) Local dev fallback
    return _cache(_DEFAULT_URL)


def _cache(url: str) -> str:
    """Cache the result in session_state and return it."""
    try:
        st.session_state["_app_url_cache"] = url
    except Exception:
        # No session_state available (e.g. during very early init)
        pass
    return url


def get_public_card_url(user_id: str) -> str:
    """Build the full public card URL for a given user.

    Args:
        user_id: the user's UUID.

    Returns:
        A full URL like
        ``https://eschain.yourdomain.com/?card=abc-123-def``
    """
    base = get_app_url()
    return f"{base}/?card={user_id}"


def get_password_reset_url() -> str:
    """Build the URL Supabase emails link to for password reset.

    Returns:
        A full URL like
        ``https://eschain.yourdomain.com/?page=reset-password``
    """
    base = get_app_url()
    return f"{base}/?page=reset-password"


def get_app_url_display() -> str:
    """Return the app URL for display in the UI (e.g. footer text).

    Strips ``https://`` and trailing slashes for a cleaner look.
    """
    url = get_app_url()
    return url.replace("https://", "").replace("http://", "").rstrip("/")


# -----------------------------------------------------------------------
# Module-level test (only runs when executed directly)
# -----------------------------------------------------------------------
if __name__ == "__main__":
    print("App URL detection test")
    print("-" * 40)
    print(f"  APP_URL env:          {os.environ.get('APP_URL')!r}")
    print(f"  RENDER_EXTERNAL_URL:  {os.environ.get('RENDER_EXTERNAL_URL')!r}")
    print(f"  STREAMLIT_RUNTIME_ENV:{os.environ.get('STREAMLIT_RUNTIME_ENV')!r}")
    print(f"  Resolved:             {get_app_url()!r}")
    print(f"  Force default:        {get_app_url(force_default=True)!r}")
