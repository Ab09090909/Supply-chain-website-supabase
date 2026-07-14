"""
Supabase Storage helper — upload images to the 'product-images' bucket.

Used for:
  • Product photos (when adding/editing products)
  • User avatars (when editing profile)
"""
from __future__ import annotations

from uuid import uuid4
from typing import Optional, Tuple
import streamlit as st

from database.connection import get_supabase_client

BUCKET_NAME = "product-images"


def upload_image(
    uploaded_file,
    folder: str = "products",
    allowed_types: Tuple[str, ...] = ("image/jpeg", "image/png", "image/webp", "image/gif"),
) -> Tuple[Optional[str], Optional[str]]:
    """Upload a Streamlit UploadedFile to Supabase Storage.

    Args:
        uploaded_file: st.file_uploader result (or None)
        folder: 'products' or 'avatars'
        allowed_types: MIME types to accept

    Returns:
        (public_url, error_message) — one of them is None on success/failure.
    """
    if uploaded_file is None:
        return None, "No file provided."

    if uploaded_file.type not in allowed_types:
        return None, f"Unsupported file type: {uploaded_file.type}. Allowed: {', '.join(allowed_types)}"

    # 5 MB limit
    file_bytes = uploaded_file.getvalue()
    if len(file_bytes) > 5 * 1024 * 1024:
        return None, "File too large. Maximum 5 MB."

    # Build a unique file path
    ext = uploaded_file.name.split(".")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"
    file_path = f"{folder}/{uuid4().hex}.{ext}"

    try:
        client = get_supabase_client()
        # Upload (upsert=True so re-uploads replace)
        client.storage.from_(BUCKET_NAME).upload(
            file_path,
            file_bytes,
            {"content-type": uploaded_file.type, "upsert": "true"},
        )
        # Get public URL
        public_url = client.storage.from_(BUCKET_NAME).get_public_url(file_path)
        # Cache-bust so the new image shows immediately
        public_url = f"{public_url}?t={uuid4().hex[:8]}"
        return public_url, None
    except Exception as e:
        return None, f"Upload failed: {e}"


def render_image_uploader(
    label: str,
    folder: str = "products",
    current_url: Optional[str] = None,
    key: str = "image_uploader",
) -> Tuple[Optional[str], Optional[str]]:
    """Render a Streamlit file_uploader + preview. Returns (final_url, error).

    If user uploads a new file → upload + return new URL.
    If user keeps existing → return current_url.
    """
    col1, col2 = st.columns([1, 2])

    with col1:
        if current_url:
            st.image(current_url, caption="Current image", use_container_width=True)
        else:
            st.markdown("*No image yet*")

    with col2:
        uploaded = st.file_uploader(
            label,
            type=["png", "jpg", "jpeg", "webp", "gif"],
            key=key,
        )

        url_input = st.text_input(
            "Or paste an image URL",
            value="",
            placeholder="https://images.unsplash.com/...",
            key=f"{key}_url",
            help="You can either upload a file OR paste a URL.",
        )

        if uploaded is not None:
            new_url, err = upload_image(uploaded, folder=folder)
            if err:
                st.error(err)
                return current_url, err
            st.success("✅ Image uploaded")
            return new_url, None
        elif url_input.strip():
            return url_input.strip(), None
        else:
            return current_url, None
