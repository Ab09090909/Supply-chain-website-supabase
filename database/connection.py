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

# 3. Supabase import — tries the real `supabase` package first, then falls
#    back to our lightweight `supabase_lite` (pure requests, no dependencies).
#    This eliminates ALL Streamlit Cloud dependency issues.
try:
    from supabase import create_client, Client
except ImportError:
    try:
        # Fallback: use our lightweight HTTP-based client (no pydantic_core etc.)
        # Use relative import since we're inside the database package
        from .supabase_lite import create_client, Client
    except ImportError:
        try:
            # Absolute import fallback
            from database.supabase_lite import create_client, Client
        except ImportError:
            try:
                # Last resort: direct import (if database/ is on sys.path)
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                from supabase_lite import create_client, Client
            except ImportError:
                create_client = None
                Client = None


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


# Aliases — accept multiple key names so users don't have to remember the
# exact one. (Common mistake: SUPABASE_KEY instead of SUPABASE_ANON_KEY.)
_KEY_ALIASES = {
    "SUPABASE_URL":                ["SUPABASE_URL"],
    "SUPABASE_ANON_KEY":           ["SUPABASE_ANON_KEY", "SUPABASE_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY"],
    "SUPABASE_SERVICE_ROLE_KEY":   ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SERVICE_ROLE_KEY"],
    "APP_URL":                     ["APP_URL", "NEXT_PUBLIC_APP_URL"],
    "GROQ_API_KEY":                ["GROQ_API_KEY", "GROQ_KEY", "GROQ_TOKEN"],
}


def _get_config(key: str) -> Optional[str]:
    """Read config from: os.environ → st.secrets → manual TOML parse.

    Tries every alias for the requested key, so users who wrote
    SUPABASE_KEY instead of SUPABASE_ANON_KEY still get a working client.
    """
    aliases = _KEY_ALIASES.get(key, [key])

    for alias in aliases:
        # (a) Real environment variable (includes anything load_dotenv just set)
        val = os.environ.get(alias)
        if val and not val.startswith("your-"):  # ignore placeholder values
            return val

    # (b) Streamlit secrets — read once, check all aliases
    if st is not None:
        try:
            for alias in aliases:
                val = st.secrets.get(alias)
                if val and not str(val).startswith("your-"):
                    return str(val)
        except Exception:
            pass

    # (c) Manual TOML fallback — read once, check all aliases
    secrets = _read_secrets_toml()
    for alias in aliases:
        val = secrets.get(alias)
        if val and not str(val).startswith("your-"):
            return str(val)

    return None


def _get_config_source(key: str) -> Optional[str]:
    """For diagnostics: returns where the value was actually found."""
    aliases = _KEY_ALIASES.get(key, [key])
    for alias in aliases:
        if os.environ.get(alias) and not os.environ.get(alias).startswith("your-"):
            return f"os.environ[{alias!r}]"
    if st is not None:
        try:
            for alias in aliases:
                val = st.secrets.get(alias)
                if val and not str(val).startswith("your-"):
                    return f"st.secrets[{alias!r}]"
        except Exception:
            pass
    secrets = _read_secrets_toml()
    for alias in aliases:
        val = secrets.get(alias)
        if val and not str(val).startswith("your-"):
            return f"secrets.toml[{alias!r}]"
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
    if create_client is None:
        raise RuntimeError(
            "Could not load the Supabase client. This means:\n"
            "1. The `supabase` Python package is not installed, AND\n"
            "2. The fallback `database/supabase_lite.py` file is missing or broken.\n\n"
            "Fix: Make sure `database/supabase_lite.py` exists in your repo. "
            "It provides a lightweight HTTP-based client that needs no dependencies."
        )
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
    """Admin Supabase client (service_role key, bypasses RLS).

    If the service_role key is not configured OR if it's clearly wrong (e.g.
    a Groq key was put in this slot by mistake), falls back to the anon client
    so admin pages still work (just RLS-restricted).
    """
    if create_client is None:
        return get_supabase_client()  # will raise a clear error
    url = _get_config("SUPABASE_URL")
    key = _get_config("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return get_supabase_client()
    # Detect common mistake: Groq key in Supabase slot
    # Groq keys start with 'gsk_', Supabase keys start with 'eyJ'
    if key.startswith("gsk_"):
        return get_supabase_client()
    return create_client(url, key)


def validate_config() -> dict:
    """Validate all config keys and detect common mistakes.

    Returns a dict with:
      - 'issues': list of human-readable issue strings
      - 'is_clean': bool (True if no issues found)
    """
    issues = []

    supabase_url = _get_config("SUPABASE_URL")
    anon_key = _get_config("SUPABASE_ANON_KEY")
    service_key = _get_config("SUPABASE_SERVICE_ROLE_KEY")
    groq_key = _get_config("GROQ_API_KEY")

    # Check Supabase URL
    if not supabase_url:
        issues.append("❌ `SUPABASE_URL` is missing. Set it to your project URL (e.g. https://xxxxx.supabase.co).")
    elif "supabase.co" not in supabase_url:
        issues.append(f"❌ `SUPABASE_URL` doesn't look like a Supabase URL: '{supabase_url[:40]}...'")

    # Check anon key
    if not anon_key:
        issues.append("❌ `SUPABASE_ANON_KEY` is missing.")
    elif not anon_key.startswith("eyJ"):
        issues.append("❌ `SUPABASE_ANON_KEY` doesn't look like a Supabase key (should start with 'eyJ...').")

    # Check service role key — detect the Groq-in-Supabase-slot mistake
    if service_key:
        if service_key.startswith("gsk_"):
            issues.append(
                "❌ `SUPABASE_SERVICE_ROLE_KEY` contains a **Groq** key (starts with 'gsk_'). "
                "You put the Groq API key in the wrong slot! Get your Supabase service_role key "
                "from Dashboard → Project Settings → API (it starts with 'eyJ...')."
            )
        elif not service_key.startswith("eyJ"):
            issues.append("⚠️ `SUPABASE_SERVICE_ROLE_KEY` doesn't look like a Supabase key (should start with 'eyJ...').")

    # Check Groq key
    if groq_key:
        if groq_key.startswith("eyJ"):
            issues.append(
                "❌ `GROQ_API_KEY` contains a **Supabase** key (starts with 'eyJ'). "
                "You put the Supabase key in the wrong slot! Get your Groq API key "
                "from https://console.groq.com/keys (it starts with 'gsk_')."
            )
        elif not groq_key.startswith("gsk_"):
            issues.append("⚠️ `GROQ_API_KEY` doesn't look like a Groq key (should start with 'gsk_').")

    # Check for duplicate keys in wrong slots
    if anon_key and service_key and anon_key == service_key:
        issues.append("⚠️ `SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_ROLE_KEY` are the same. They should be DIFFERENT keys.")

    return {
        "issues": issues,
        "is_clean": len(issues) == 0,
    }
