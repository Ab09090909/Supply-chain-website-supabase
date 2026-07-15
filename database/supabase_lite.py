"""
Lightweight Supabase client using requests (no supabase-py dependency).

This replaces the `supabase` Python package with direct HTTP calls to the
Supabase REST API. This eliminates all dependency issues on Streamlit Cloud
(pydantic_core, cryptography, etc.).

Provides:
  • auth.sign_up(email, password, metadata) → creates auth user
  • auth.sign_in_with_password(email, password) → returns session
  • auth.sign_out() → invalidates session
  • auth.reset_password_email(email) → sends reset email
  • auth.update_user(token, updates) → updates user
  • table(name).select(filters).eq(column, value).execute() → query
  • table(name).insert(data).execute() → create
  • table(name).update(data).eq(column, value).execute() → update
  • table(name).delete().eq(column, value).execute() → delete
  • storage.from_(bucket).upload(path, file, options) → upload file
  • storage.from_(bucket).get_public_url(path) → get URL
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
        self._single: bool = False

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
        self._filters.append(f"{column}=lt.{_format_value(value)}")
        return self

    def gte(self, column: str, value: Any):
        self._filters.append(f"{column}=gte.{_format_value(value)}")
        return self

    def lte(self, column: str, value: Any):
        self._filters.append(f"{column}=lte.{_format_value(value)}")
        return self

    def in_(self, column: str, values: list):
        if not values:
            # Empty list — add an impossible filter so the query returns nothing
            self._filters.append(f"{column}=eq.__EMPTY_LIST__")
            return self
        vals = ",".join(_format_value(v) for v in values)
        self._filters.append(f"{column}=in.({vals})")
        return self

    def like(self, column: str, pattern: str):
        self._filters.append(f"{column}=like.{pattern}")
        return self

    def limit(self, n: int):
        self._limit_val = n
        return self

    def order(self, column: str, desc: bool = False):
        self._order_col = column
        self._order_desc = desc
        return self

    def maybe_single(self):
        self._single = True
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        # Build URL
        url = f"{self._client.url}/rest/v1/{self._table}?select={self._select_cols}"
        for f in self._filters:
            url += f"&{f}"
        if self._order_col:
            direction = "desc" if self._order_desc else "asc"
            url += f"&order={self._order_col}.{direction}"
        if self._limit_val:
            url += f"&limit={self._limit_val}"

        headers = self._client._headers()
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code >= 400:
            raise Exception(r.text)
        data = r.json()
        # Handle .single() / .maybe_single()
        if getattr(self, "_single", False):
            return _Response(data[0] if data else None)
        return _Response(data)

    def insert(self, data: Union[dict, list]):
        return _InsertBuilder(self, data)

    def update(self, data: dict):
        return _UpdateBuilder(self, data)

    def delete(self):
        return _DeleteBuilder(self)

    def upsert(self, data: dict, on_conflict: Optional[str] = None):
        return _UpsertBuilder(self, data, on_conflict)


class _InsertBuilder:
    def __init__(self, query: _QueryBuilder, data: Union[dict, list]):
        self._query = query
        self._data = data

    def execute(self):
        url = f"{self._query._client.url}/rest/v1/{self._query._table}"
        headers = self._query._client._headers()
        headers["Prefer"] = "return=representation"
        r = requests.post(url, headers=headers, json=self._data, timeout=30)
        if r.status_code >= 400:
            raise Exception(r.text)
        data = r.json() if r.text else []
        return _Response(data)


class _UpdateBuilder:
    def __init__(self, query: _QueryBuilder, data: dict):
        self._query = query
        self._data = data

    def eq(self, column: str, value: Any):
        self._query.eq(column, value)
        return self

    def execute(self):
        url = f"{self._query._client.url}/rest/v1/{self._query._table}"
        for f in self._query._filters:
            url += f"&{f}" if "?" in url else f"?{f}"
        headers = self._query._client._headers()
        headers["Prefer"] = "return=representation"
        r = requests.patch(url, headers=headers, json=self._data, timeout=30)
        if r.status_code >= 400:
            raise Exception(r.text)
        data = r.json() if r.text else []
        return _Response(data)


class _DeleteBuilder:
    def __init__(self, query: _QueryBuilder):
        self._query = query

    def eq(self, column: str, value: Any):
        self._query.eq(column, value)
        return self

    def execute(self):
        url = f"{self._query._client.url}/rest/v1/{self._query._table}"
        for f in self._query._filters:
            url += f"&{f}" if "?" in url else f"?{f}"
        headers = self._query._client._headers()
        r = requests.delete(url, headers=headers, timeout=30)
        if r.status_code >= 400:
            raise Exception(r.text)
        data = r.json() if r.text else []
        return _Response(data)


class _UpsertBuilder:
    def __init__(self, query: _QueryBuilder, data: dict, on_conflict: Optional[str] = None):
        self._query = query
        self._data = data
        self._on_conflict = on_conflict

    def execute(self):
        url = f"{self._query._client.url}/rest/v1/{self._query._table}"
        headers = self._query._client._headers()
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        if self._on_conflict:
            url += f"?on_conflict={self._on_conflict}"
        r = requests.post(url, headers=headers, json=self._data, timeout=30)
        if r.status_code >= 400:
            raise Exception(r.text)
        data = r.json() if r.text else []
        return _Response(data)


class _Response:
    """Mimics supabase-py response object."""

    def __init__(self, data):
        self.data = data


class _StorageBucket:
    def __init__(self, client: "SupabaseClient", bucket: str):
        self._client = client
        self._bucket = bucket

    def upload(self, path: str, file: bytes, file_options: Optional[dict] = None):
        url = f"{self._client.url}/storage/v1/object/{self._bucket}/{path}"
        headers = self._client._headers()
        headers.pop("Content-Type", None)  # multipart will set it
        if file_options:
            content_type = file_options.get("content_type", "application/octet-stream")
            headers["Content-Type"] = content_type
        r = requests.post(url, headers=headers, data=file, timeout=60)
        if r.status_code >= 400:
            raise Exception(r.text)
        return r.json() if r.text else {}

    def get_public_url(self, path: str) -> str:
        return f"{self._client.url}/storage/v1/object/public/{self._bucket}/{path}"


class _Storage:
    def __init__(self, client: "SupabaseClient"):
        self._client = client

    def from_(self, bucket: str) -> _StorageBucket:
        return _StorageBucket(self._client, bucket)


def _format_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        # PostgREST requires string values to be enclosed in double quotes
        # if they contain special characters (commas, parentheses, spaces, etc.)
        # For safety, always quote string values for PostgREST filters.
        escaped = v.replace('"', '\\"')
        return f'"{escaped}"'
    return str(v)


class SupabaseClient:
    """Drop-in replacement for supabase.create_client()."""

    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.anon_key = key
        self.auth = SupabaseAuth(url, key)
        self.storage = _Storage(self)

    def _headers(self) -> dict:
        # Use the current user's token if available, else anon key
        token = self.auth._access_token or self.anon_key
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def table(self, name: str) -> _QueryBuilder:
        return _QueryBuilder(self, name)


def create_client(url: str, key: str) -> SupabaseClient:
    """Drop-in replacement for supabase.create_client()."""
    return SupabaseClient(url, key)


# Type alias for compatibility
Client = SupabaseClient
