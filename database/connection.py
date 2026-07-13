"""
Supabase client connection - single source of truth.

Two clients:
  • get_supabase_client()         -> anon key, RLS-enforced (use for user actions)
  • get_supabase_admin_client()   -> service_role key, bypasses RLS (use for admin/system)

Reads credentials from (in order):
  1. Real OS environment variables
  2. .env file at project root (auto-loaded via python-dotenv)
  3. .streamlit/secrets.toml (Streamlit secrets)
  4. Local TOML fallback parse (in case st.secrets fails to initialize)

If none of the above has the key, a clear RuntimeError is raised listing
every location we checked.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

# 1. Load .env file at project root IMMEDIATELY (this was the bug)
try:
    from dotenv import load_dotenv
    # Walk up from this file to find the project root (where .env lives)
    _project_root = Path(__file__).resolve().parent.parent
    load_dotenv(_project_root / ".env")
    load_dotenv()  # also try CWD as fallback
except ImportError:
    # python-dotenv not installed - skip silently, OS env / st.secrets still work
    pass

# 2. Try Streamlit (optional - allows running scripts outside Streamlit)
try:
    import streamlit as st
except ImportError:
    st = None

from supabase import create_client, Client


# 3. Fallback TOML parser for .streamlit/secrets.toml (used only if st.secrets fails)
def _read_secrets_toml() -> dict:
    """Parse .streamlit/secrets.toml manually as a last-resort fallback."""
    secrets_path = _project_root / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return {}
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # type: ignore
        with open(secrets_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _get_config(key: str) -> Optional[str]:
    """Read config from: os.environ → st.secrets → manual TOML parse."""
    # (a) Real environment variable (includes anything load_dotenv just set)
    val = os.environ.get(key)
    if val and not val.startswith("your-"):  # ignore placeholder values
        return val

    # (b) Streamlit secrets
    if st is not None:
        try:
            val = st.secrets.get(key)
            if val and not str(val).startswith("your-"):
                return str(val)
        except Exception:
            pass

    # (c) Manual TOML fallback
    secrets = _read_secrets_toml()
    val = secrets.get(key)
    if val and not str(val).startswith("your-"):
        return str(val)

    return None


def _debug_config_status() -> dict:
    """Return a dict showing which config sources are available (for error messages)."""
    status = {
        "env_file_exists": (_project_root / ".env").exists(),
        "secrets_toml_exists": (_project_root / ".streamlit" / "secrets.toml").exists(),
        "streamlit_available": st is not None,
        "SUPABASE_URL_in_os_environ": bool(os.environ.get("SUPABASE_URL")),
        "SUPABASE_ANON_KEY_in_os_environ": bool(os.environ.get("SUPABASE_ANON_KEY")),
        "dotenv_installed": False,
    }
    try:
        import dotenv  # noqa: F401
        status["dotenv_installed"] = True
    except ImportError:
        pass
    return status


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """User-scoped Supabase client (RLS enforced)."""
    url = _get_config("SUPABASE_URL")
    key = _get_config("SUPABASE_ANON_KEY")
    if not url or not key:
        status = _debug_config_status()
        raise RuntimeError(
            "Supabase credentials not found.\n"
            f"  Checked: .env exists={status['env_file_exists']}, "
            f"secrets.toml exists={status['secrets_toml_exists']}, "
            f"dotenv installed={status['dotenv_installed']}\n"
            f"  SUPABASE_URL in env: {status['SUPABASE_URL_in_os_environ']}\n"
            f"  SUPABASE_ANON_KEY in env: {status['SUPABASE_ANON_KEY_in_os_environ']}\n"
            "Fix options (pick ONE):\n"
            "  1. Create .env at project root with SUPABASE_URL and SUPABASE_ANON_KEY\n"
            "  2. Create .streamlit/secrets.toml with SUPABASE_URL and SUPABASE_ANON_KEY\n"
            "  3. Run: export SUPABASE_URL=... && export SUPABASE_ANON_KEY=...\n"
            "Then restart streamlit."
        )
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """Admin Supabase client (service_role key, bypasses RLS). Use ONLY for trusted admin ops."""
    url = _get_config("SUPABASE_URL")
    key = _get_config("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Supabase service_role key not found. Set SUPABASE_SERVICE_ROLE_KEY "
            "in .env or .streamlit/secrets.toml"
        )
    return create_client(url, key)
