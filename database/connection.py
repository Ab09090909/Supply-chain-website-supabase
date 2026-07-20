"""
Supabase client connection - single source of truth.

This module ALWAYS works, even if:
  • The `supabase` Python package is not installed
  • The `supabase/` folder (SQL files) shadows the real package
  • Relative imports fail for any reason

It does this by loading `supabase_lite.py` directly via importlib
(absolute file path, no package dependency).
"""
from __future__ import annotations

import os
import sys
import importlib.util
from pathlib import Path
from typing import Optional

# Project root = parent of this file's directory (database/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 1. Load .env file at project root IMMEDIATELY
try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env")
    load_dotenv()  # also try CWD as fallback
except ImportError:
    pass

# 2. Try Streamlit (optional)
try:
    import streamlit as st
except ImportError:
    st = None


# 3. Load the Supabase client — ALWAYS succeeds (falls back to supabase_lite)
def _load_create_client():
    """Load create_client from supabase-py OR supabase_lite. Always returns a callable."""
    # Strategy A: Try the real supabase package
    try:
        import supabase as _supabase_mod  # noqa: F401
        from supabase import create_client as _cc
        from supabase import Client as _Client
        return _cc, _Client
    except Exception:
        pass

    # Strategy B: Load supabase_lite.py directly via file path (BULLETPROOF)
    lite_path = Path(__file__).resolve().parent / "supabase_lite.py"
    if lite_path.exists():
        try:
            spec = importlib.util.spec_from_file_location("supabase_lite", lite_path)
            if spec and spec.loader:
                lite_mod = importlib.util.module_from_spec(spec)
                sys.modules["supabase_lite"] = lite_mod
                spec.loader.exec_module(lite_mod)
                _cc = getattr(lite_mod, "create_client", None)
                if callable(_cc):
                    return _cc, getattr(lite_mod, "Client", object)
        except Exception:
            pass

    # Strategy C: Standard package import
    try:
        from database.supabase_lite import create_client as _cc
        from database.supabase_lite import Client as _Client
        return _cc, _Client
    except Exception:
        pass

    return None, None


create_client, Client = _load_create_client()


# 4. Fallback TOML parser for secrets.toml
def _read_secrets_toml() -> dict:
    secrets_path = _PROJECT_ROOT / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return {}
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(secrets_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


# 5. Key aliases
_KEY_ALIASES = {
    "SUPABASE_URL": ["SUPABASE_URL"],
    "SUPABASE_ANON_KEY": ["SUPABASE_ANON_KEY", "SUPABASE_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY"],
    "SUPABASE_SERVICE_ROLE_KEY": ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SERVICE_ROLE_KEY"],
    "APP_URL": ["APP_URL", "NEXT_PUBLIC_APP_URL"],
    "GROQ_API_KEY": ["GROQ_API_KEY", "GROQ_KEY", "GROQ_TOKEN"],
}

# Cache for config lookups (avoids re-reading env vars + secrets.toml on every call)
_config_cache: Dict[str, Optional[str]] = {}


def _get_config(key: str) -> Optional[str]:
    """Look up a config value, accepting several aliases and rejecting
    obvious placeholder values like ``your-…`` or ``eyJ-replace-…``.

    Order: 1) os.environ, 2) st.secrets, 3) .streamlit/secrets.toml.
    Results are cached in _config_cache so we don't re-read env vars
    and st.secrets on every Streamlit rerun.
    """
    if key in _config_cache:
        return _config_cache[key]

    aliases = _KEY_ALIASES.get(key, [key])
    # Reject any value that looks like a placeholder
    placeholder_prefixes = ("your-", "eyJ-replace", "gsk-replace", "replace-")

    def _is_real(val) -> bool:
        if not val:
            return False
        s = str(val).strip()
        if not s:
            return False
        return not any(s.startswith(p) for p in placeholder_prefixes)

    for alias in aliases:
        val = os.environ.get(alias)
        if _is_real(val):
            _config_cache[key] = val
            return val
    if st is not None:
        try:
            for alias in aliases:
                val = st.secrets.get(alias)
                if _is_real(val):
                    result = str(val)
                    _config_cache[key] = result
                    return result
        except Exception:
            pass
    secrets = _read_secrets_toml()
    for alias in aliases:
        val = secrets.get(alias)
        if _is_real(val):
            result = str(val)
            _config_cache[key] = result
            return result
    _config_cache[key] = None
    return None


def _debug_config_status() -> dict:
    return {
        "env_file_exists": (_PROJECT_ROOT / ".env").exists(),
        "secrets_toml_exists": (_PROJECT_ROOT / ".streamlit" / "secrets.toml").exists(),
        "streamlit_available": st is not None,
        "SUPABASE_URL_in_os_environ": bool(os.environ.get("SUPABASE_URL")),
        "SUPABASE_ANON_KEY_in_os_environ": bool(os.environ.get("SUPABASE_ANON_KEY")),
        "create_client_loaded": create_client is not None,
    }


def get_supabase_client():
    """User-scoped Supabase client (RLS enforced).

    Returns a *fresh* client on every call so that the auth token attached
    to the underlying transport is always read from the current Streamlit
    session. Streamlit workers are long-lived and reused across many users;
    caching this object at module scope would let one user's tokens leak
    into another user's requests (the ``supabase_lite`` transport stores
    the access token on the client instance).
    """
    if create_client is None:
        raise RuntimeError(
            "Could not load the Supabase client. The `supabase` package is not installed "
            "AND `database/supabase_lite.py` could not be loaded. "
            "Make sure `database/supabase_lite.py` exists in your repo."
        )
    url = _get_config("SUPABASE_URL")
    key = _get_config("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials not found. Set SUPABASE_URL and SUPABASE_ANON_KEY in secrets.")
    client = create_client(url, key)
    # Bind the current session's access token (if any) onto the new client
    # so subsequent REST calls use the right user identity. We read from
    # st.session_state rather than threading the token through every call
    # site, because Streamlit guarantees a stable session per browser.
    try:
        if st is not None:
            tok = st.session_state.get("access_token")
            if tok and getattr(client, "auth", None) is not None:
                client.auth._access_token = tok
                client.auth._refresh_token = st.session_state.get("refresh_token")
    except Exception:
        # Non-fatal: client will still work with anon key
        pass
    return client


def get_supabase_admin_client():
    """Admin Supabase client (service_role key, bypasses RLS).

    IMPORTANT: this client should ONLY be used from server-side admin
    code paths. It is intentionally NOT cached at module scope so the
    token cannot bleed across user sessions. There is no automatic
    fallback to the anon client — if the service_role key is missing,
    callers must handle that (and they should, because a missing
    service_role key is a configuration error, not a runtime fallback).
    """
    if create_client is None:
        raise RuntimeError(
            "Could not load the Supabase client. The `supabase` package "
            "is not installed AND `database/supabase_lite.py` could not "
            "be loaded."
        )
    url = _get_config("SUPABASE_URL")
    key = _get_config("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Admin client requested but SUPABASE_SERVICE_ROLE_KEY is not set. "
            "Add it to .streamlit/secrets.toml (or Streamlit Cloud Secrets)."
        )
    # Defence in depth: never accept a Groq key in this slot
    if str(key).startswith("gsk_"):
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY starts with 'gsk_'. That looks like a "
            "Groq key. Put your Supabase service_role key (starts with 'eyJ') here."
        )
    return create_client(url, key)


def validate_config() -> dict:
    issues = []
    supabase_url = _get_config("SUPABASE_URL")
    anon_key = _get_config("SUPABASE_ANON_KEY")
    service_key = _get_config("SUPABASE_SERVICE_ROLE_KEY")
    groq_key = _get_config("GROQ_API_KEY")
    if not supabase_url:
        issues.append("❌ `SUPABASE_URL` is missing.")
    if not anon_key:
        issues.append("❌ `SUPABASE_ANON_KEY` is missing.")
    elif not anon_key.startswith("eyJ"):
        issues.append("❌ `SUPABASE_ANON_KEY` should start with 'eyJ'.")
    if service_key:
        if service_key.startswith("gsk_"):
            issues.append("❌ `SUPABASE_SERVICE_ROLE_KEY` contains a Groq key (starts with 'gsk_'). Put your Supabase service_role key here (starts with 'eyJ').")
    if groq_key:
        if groq_key.startswith("eyJ"):
            issues.append("❌ `GROQ_API_KEY` contains a Supabase key (starts with 'eyJ'). Put your Groq key here (starts with 'gsk_').")
    if anon_key and service_key and anon_key == service_key:
        issues.append("⚠️ ANON and SERVICE_ROLE keys are the same. They must be different.")
    return {"issues": issues, "is_clean": len(issues) == 0}
