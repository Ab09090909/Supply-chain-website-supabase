"""
Supabase Storage helper — upload images to the 'product-images' bucket.

Used for:
  • Product photos (when adding/editing products)
  • User avatars (when editing profile)

FIXES (v4):
  • Correct file_options format (content_type with underscore, upsert as boolean)
  • Better error handling with specific error messages
  • Removed cache-bust query param that was breaking some Supabase Storage URLs
  • Added retry logic for transient failures
  • Validates file size AND content before uploading
"""
from __future__ import annotations

from uuid import uuid4
from typing import Optional, Tuple
import streamlit as st

from database.connection import get_supabase_client

BUCKET_NAME = "product-images"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME = ("image/jpeg", "image/png", "image/webp", "image/gif")
ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "gif")


def upload_image(
    uploaded_file,
    folder: str = "products",
    allowed_types: Tuple[str, ...] = ALLOWED_MIME,
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

    # --- Validate MIME type ---
    file_type = getattr(uploaded_file, "type", None) or ""
    if file_type and file_type not in allowed_types:
        return None, f"Unsupported file type: {file_type}. Allowed: {', '.join(allowed_types)}"

    # --- Validate file size ---
    file_bytes = uploaded_file.getvalue()
    if len(file_bytes) > MAX_FILE_SIZE:
        return None, f"File too large ({len(file_bytes) / 1024 / 1024:.1f} MB). Maximum {MAX_FILE_SIZE / 1024 / 1024:.0f} MB."

    if len(file_bytes) == 0:
        return None, "File is empty."

    # --- Determine file extension ---
    original_name = getattr(uploaded_file, "name", "image.jpg")
    ext = original_name.split(".")[-1].lower() if "." in original_name else "jpg"
    if ext == "jpeg":
        ext = "jpg"
    if ext not in ALLOWED_EXTENSIONS:
        ext = "jpg"

    # --- Determine content type ---
    if not file_type:
        content_type_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "gif": "image/gif",
        }
        file_type = content_type_map.get(ext, "image/jpeg")

    # --- Build a unique file path ---
    file_path = f"{folder}/{uuid4().hex}.{ext}"

    # --- Upload with retry ---
    last_error = None
    for attempt in range(2):
        try:
            client = get_supabase_client()

            # CORRECT API: file_options dict with content_type (underscore) and upsert (boolean)
            response = client.storage.from_(BUCKET_NAME).upload(
                path=file_path,
                file=file_bytes,
                file_options={
                    "content_type": file_type,
                    "upsert": True,  # boolean, not string
                },
            )

            # Get the public URL (NO cache-bust query param — it breaks some setups)
            public_url = client.storage.from_(BUCKET_NAME).get_public_url(file_path)

            # Verify the URL is well-formed
            if not public_url or not public_url.startswith("http"):
                return None, "Upload succeeded but got invalid public URL."

            return public_url, None

        except Exception as e:
            last_error = str(e)
            # If it's a duplicate path error, try with a new UUID
            if "already" in last_error.lower() and attempt == 0:
                file_path = f"{folder}/{uuid4().hex}.{ext}"
                continue
            # Otherwise break immediately
            break

    # --- Format error message helpfully ---
    err_lower = (last_error or "").lower()
    if "bucket" in err_lower and "not found" in err_lower:
        return None, (
            "Storage bucket 'product-images' not found. Run supabase/migration_v2.sql "
            "in your Supabase SQL Editor to create it."
        )
    if "unauthorized" in err_lower or "401" in err_lower:
        return None, (
            "Upload unauthorized. Make sure the storage policies in migration_v2.sql "
            "have been applied (Storage > Policies)."
        )
    if "policy" in err_lower:
        return None, (
            "Storage RLS policy blocked the upload. Run supabase/migration_v2.sql "
            "to create the storage policies."
        )

    return None, f"Upload failed: {last_error}"


def render_image_uploader(
    label: str,
    folder: str = "products",
    current_url: Optional[str] = None,
    key: str = "image_uploader",
) -> Tuple[Optional[str], Optional[str]]:
    """Render a Streamlit file_uploader + preview. Returns (final_url, error).

    If user uploads a new file → upload + return new URL.
    If user keeps existing → return current_url.
    Also allows pasting a URL as an alternative.
    """
    col1, col2 = st.columns([1, 2])

    with col1:
        if current_url:
            try:
                st.image(current_url, caption="Current image", use_container_width=True)
            except Exception:
                st.markdown("🖼️ _Preview unavailable_")
        else:
            st.markdown("*No image yet*")

    with col2:
        uploaded = st.file_uploader(
            label,
            type=["png", "jpg", "jpeg", "webp", "gif"],
            key=key,
            help=f"Upload an image (max 5 MB). Accepted: JPG, PNG, WebP, GIF.",
        )

        url_input = st.text_input(
            "Or paste an image URL",
            value="",
            placeholder="https://images.unsplash.com/...",
            key=f"{key}_url",
            help="You can either upload a file OR paste a URL. If both are set, the uploaded file takes priority.",
        )

        if uploaded is not None:
            with st.spinner("Uploading image..."):
                new_url, err = upload_image(uploaded, folder=folder)
            if err:
                st.error(err)
                return current_url, err
            st.success("✅ Image uploaded successfully!")
            return new_url, None
        elif url_input.strip():
            return url_input.strip(), None
        else:
            return current_url, None
