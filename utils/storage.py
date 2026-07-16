"""
Supabase Storage helper — upload images to the 'product-images' bucket.

Used for:
  • Product photos (when adding/editing products)
  • User avatars (when editing profile)

SIMPLIFIED (v6):
  • Always uses the admin (service_role) client for uploads. This
    bypasses storage.objects RLS entirely, so the upload always
    succeeds as long as the bucket exists.
  • Falls back to the regular client if the service_role key is not
    configured.
  • Removed all the RLS / migration_v2 / "Go to Supabase Dashboard"
    error messages. If the upload fails, we just say "Upload failed:
    <reason>" and the user can move on.
"""
from __future__ import annotations

from uuid import uuid4
from typing import Optional, Tuple
import streamlit as st

from database.connection import get_supabase_client, get_supabase_admin_client

BUCKET_NAME = "product-images"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME = ("image/jpeg", "image/png", "image/webp", "image/gif")
ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "gif")


def _sniff_mime_from_bytes(data: bytes) -> Optional[str]:
    """Detect MIME type from the first few bytes (magic bytes)."""
    if not data or len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _get_upload_client():
    """Get the best client for uploads. Admin (service_role) bypasses
    storage RLS entirely. Falls back to the regular client if the
    service_role key isn't configured.
    """
    try:
        return get_supabase_admin_client()
    except Exception:
        return get_supabase_client()


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

    file_bytes = uploaded_file.getvalue()

    # --- Validate file size ---
    if len(file_bytes) > MAX_FILE_SIZE:
        return None, f"File too large ({len(file_bytes) / 1024 / 1024:.1f} MB). Maximum {MAX_FILE_SIZE / 1024 / 1024:.0f} MB."
    if len(file_bytes) == 0:
        return None, "File is empty."

    # --- Determine MIME type (magic bytes first, then browser, then extension) ---
    file_type = getattr(uploaded_file, "type", None) or ""
    sniffed = _sniff_mime_from_bytes(file_bytes)
    if sniffed:
        file_type = sniffed
    elif file_type and file_type not in allowed_types:
        return None, (
            f"Unsupported file type: {file_type}. "
            f"Allowed: {', '.join(allowed_types)}. "
            "If this is a real image, try re-saving it as JPG or PNG."
        )

    if not file_type:
        content_type_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "gif": "image/gif",
        }
        original_name = getattr(uploaded_file, "name", "image.jpg")
        ext_guess = original_name.split(".")[-1].lower() if "." in original_name else "jpg"
        if ext_guess == "jpeg":
            ext_guess = "jpg"
        file_type = content_type_map.get(ext_guess, "image/jpeg")

    # --- Determine file extension ---
    original_name = getattr(uploaded_file, "name", "image.jpg")
    ext = original_name.split(".")[-1].lower() if "." in original_name else ""
    if ext == "jpeg":
        ext = "jpg"
    if ext not in ALLOWED_EXTENSIONS:
        ext = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
        }.get(file_type, "jpg")

    # --- Build a unique file path ---
    file_path = f"{folder}/{uuid4().hex}.{ext}"

    # --- Upload (with admin client to bypass storage RLS) ---
    upload_client = _get_upload_client()
    try:
        upload_client.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=file_bytes,
            file_options={
                "content-type": file_type,
                "upsert": "true",
            },
        )
        public_url = upload_client.storage.from_(BUCKET_NAME).get_public_url(file_path)
        if not public_url or not public_url.startswith("http"):
            return None, "Upload succeeded but got invalid public URL."
        return public_url, None
    except Exception as e:
        return None, f"Upload failed: {e}"


def render_image_uploader(
    label: str,
    folder: str = "products",
    current_url: Optional[str] = None,
    key: str = "image_uploader",
) -> Tuple[Optional[str], Optional[str]]:
    """Render a Streamlit file_uploader + preview. Returns (final_url, error)."""
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
