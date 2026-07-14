"""
Supabase client connection - single source of truth.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    _project_root = Path(__file__).resolve().parent.parent
    load_dotenv(_project_root / ".env")
    load_dotenv()
except ImportError:
    pass

try:
    import streamlit as st
except ImportError:
    st = None

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None


def _read_secrets_toml() -> dict:
    secrets_path = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"
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


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    if create_client is None:
        raise RuntimeError("The `supabase` package is not installed. Run `pip install -r requirements.txt`.")
    url = _get_config("SUPABASE_URL")
    key = _get_config("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials not found. Set SUPABASE_URL and SUPABASE_ANON_KEY in .env or secrets.toml")
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
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
