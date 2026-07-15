"""
Lightweight Supabase client using requests (no supabase-py dependency).

This replaces the `supabase` Python package with direct HTTP calls to the
Supabase REST API. This eliminates all dependency issues on Streamlit Cloud
(pydantic_core, cryptography, etc.).

Provides:
  Ã¢â‚¬Â¢ auth.sign_up(email, password, metadata) Ã¢â€ â€™ creates auth user
  Ã¢â‚¬Â¢ auth.sign_in_with_password(email, password) Ã¢â€ â€™ returns session
  Ã¢â‚¬Â¢ auth.sign_out() Ã¢â€ â€™ invalidates session
  Ã¢â‚¬Â¢ auth.reset_password_email(email) Ã¢â€ â€™ sends reset email
  Ã¢â‚¬Â¢ auth.update_user(token, updates) Ã¢â€ â€™ updates user
  Ã¢â‚¬Â¢ table(name).select(filters).eq(column, value).execute() Ã¢â€ â€™ query
  Ã¢â‚¬Â¢ table(name).insert(data).execute() Ã¢â€ â€™ create
  Ã¢â‚¬Â¢ table(name).update(data).eq(column, value).execute() Ã¢â€ â€™ update
  Ã¢â‚¬Â¢ table(name).delete().eq(column, value).execute() Ã¢â€ â€™ delete
  Ã¢â‚¬Â¢ storage.from_(bucket).upload(path, file, options) Ã¢â€ â€™ upload file
  Ã¢â‚¬Â¢ storage.from_(bucket).get_public_url(path) Ã¢â€ â€™ get URL
"""
from __future__ import annotations

import json
import requests
from typing import Any, Dict, List, Optional, Union


class SupabaseAuth:
    """Auth methods using Supabase Auth API."""

    def __init__(self, url: str, anon_key: str):
        self.url = url.rstrip("/")
        self.anon_key = anon_key
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    def _headers(self, token: Optional[str] = None) -> dict:
        h = {
            "apikey": self.anon_key,
            "Content-Type": "application/json",
        }
        if token:
            h["Authorization"] = f"Bearer {token}"
        else:
            h["Authorization"] = f"Bearer {self.anon_key}"
        return h

    def sign_up(self, credentials: dict) -> dict:
        """Sign up a new user. credentials = {email, password, options: {data: {...}}}."""
        r = requests.post(
            f"{self.url}/auth/v1/signup",
            headers=self._headers(),
            json=credentials,
            timeout=30,
        )
        if r.status_code >= 400:
            raise Exception(r.text)
        data = r.json()
        # Store tokens if returned
        if data.get("access_token"):
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token")
        return _AuthResponse(data)

    def sign_in_with_password(self, credentials: dict) -> dict:
        """Sign in with email + password."""
        r = requests.post(
            f"{self.url}/auth/v1/token?grant_type=password",
            headers=self._headers(),
            json=credentials,
            timeout=30,
        )
        if r.status_code >= 400:
            raise Exception(r.text)
        data = r.json()
        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")
        return _AuthResponse(data)

    def sign_out(self):
        """Sign out current user."""
        if self._access_token:
            try:
                requests.post(
                    f"{self.url}/auth/v1/logout",
                    headers=self._headers(self._access_token),
                    timeout=10,
                )
            except Exception:
                pass
        self._access_token = None
        self._refresh_token = None

    def reset_password_email(self, email: str, options: Optional[dict] = None):
        """Send password reset email."""
        payload = {"email": email}
        if options:
            payload.update(options)
        r = requests.post(
            f"{self.url}/auth/v1/recover",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        if r.status_code >= 400:
            raise Exception(r.text)

    def update_user(self, updates: dict, token: Optional[str] = None):
        """Update current user (password, email, metadata)."""
        use_token = token or self._access_token
        r = requests.put(
            f"{self.url}/auth/v1/user",
            headers=self._headers(use_token),
            json=updates,
            timeout=30,
        )
        if r.status_code >= 400:
            raise Exception(r.text)
        return r.json()

    def get_user(self, token: Optional[str] = None):
        """Get current user info from token."""
        use_token = token or self._access_token
        r = requests.get(
            f"{self.url}/auth/v1/user",
            headers=self._headers(use_token),
            timeout=30,
        )
        if r.status_code >= 400:
            return None
        return r.json()


class _AuthResponse:
    """Mimics the supabase-py auth response object."""

    def __init__(self, data: dict):
        self._data = data
        self.user = _User(data.get("user") or {})
        self.session = _Session(data) if data.get("access_token") else None


class _User:
    def __init__(self, data: dict):
        self._data = data
        self.id = data.get("id")
        self.email = data.get("email")
        self.user_metadata = data.get("user_metadata", {})
        # Alias for compatibility
        self.raw_user_meta_data = self.user_metadata


class _Session:
    def __init__(self, data: dict):
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        self.expires_at = data.get("expires_at")


class _QueryBuilder:
    """Chainable query builder for table operations."""

    def __init__(self, client: "SupabaseClient", table: str):
        self._client = client
        self._table = table
        self._filters: List[str] = []
        self._select_cols: str = "*"
        self._limit_val: Optional[int] = None
        self._order_col: Optional[str] = None
        self._order_desc: bool = False

    def select(self, cols: str = "*"):
        self._select_cols = cols
        return self

    def eq(self, column: str, value: Any):
        self._filters.append(f"{column}=eq.{_format_value(value)}")
        return self

    def neq(self, column: str, value: Any):
        self._filters.append(f"{column}=neq.{_format_value(value)}")
        return self

    def gt(self, column: str, value: Any):
        self._filters.append(f"{column}=gt.{_format_value(value)}")
        return self

    def lt(self, column: str, value: Any):
