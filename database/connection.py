"""
Supabase client connection - single source of truth.

Two clients:
  • get_supabase_client()         -> anon key, RLS-enforced (use for user actions)
  • get_supabase_admin_client()   -> service_role key, bypasses RLS (use for admin/system)

Reads credentials from environment variables OR Streamlit secrets,
whichever is set first.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

try:
    import streamlit as st
except ImportError:  # allow running scripts outside Streamlit
    st = None

from supabase import create_client, Client


def _get_config(key: str) -> Optional[str]:
    """Read config from os.environ first, then Streamlit secrets."""
    val = os.environ.get(key)
    if val:
        return val
    if st is not None:
        try:
            return st.secrets.get(key)
        except Exception:
            return None
    return None


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """User-scoped Supabase client (RLS enforced)."""
    url = _get_config("SUPABASE_URL")
    key = _get_config("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            "Supabase credentials not found. Set SUPABASE_URL and SUPABASE_ANON_KEY "
            "in .env or .streamlit/secrets.toml"
        )
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """Admin Supabase client (service_role key, bypasses RLS).

    Use ONLY for trusted server-side admin operations.
    """
    url = _get_config("SUPABASE_URL")
    key = _get_config("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Supabase service role key not found. Set SUPABASE_SERVICE_ROLE_KEY "
            "in .env or .streamlit/secrets.toml"
        )
    return create_client(url, key)
