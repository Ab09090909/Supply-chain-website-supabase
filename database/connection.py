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
from functools import lru_cache
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
        import supabase as _supabase_mod
        _cc = getattr(_supabase_mod, "create_client", None)
        if callable(_cc):
            return _cc, getattr(_supabase_mod, "Client", object)
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

    # Strategy C: Try standard imports
    for imp_str in [
        "from database.supabase_lite import create_client, Client",
        "from .supabase_lite import create_client, Client",
    ]:
        try:
            exec(imp_str, globals())
            if "create_client" in globals() and callable(globals()["create_client"]):
                return globals()["create_client"], globals().get("Client", object)
        except Exception:
            continue

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


def _get_config(key: str) -> Optional[str]:
    aliases = _KEY_ALIASES.get(key, [key])
    for alias in aliases:
        val = os.environ.get(alias)
        if val and not val.startswith("your-"):
            return val
    if st is not None:
        try:
            for alias in aliases:
                val = st.secrets.get(alias)
                if val and not str(val).startswith("your-"):
                    return str(val)
        except Exception:
            pass
    secrets = _read_secrets_toml()
    for alias in aliases:
        val = secrets.get(alias)
        if val and not str(val).startswith("your-"):
            return str(val)
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


@lru_cache(maxsize=1)
def get_supabase_client():
    """User-scoped Supabase client (RLS enforced)."""
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
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_supabase_admin_client():
    """Admin Supabase client (service_role key). Falls back to anon if missing."""
    if create_client is None:
        return get_supabase_client()
    url = _get_config("SUPABASE_URL")
    key = _get_config("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return get_supabase_client()
    if key.startswith("gsk_"):
        return get_supabase_client()
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
