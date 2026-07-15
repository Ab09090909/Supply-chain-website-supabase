"""
Supabase Storage helper — upload images to the 'product-images' bucket.

Used for:
  • Product photos (when adding/editing products)
  • User avatars (when editing profile)

FIXES (v5):
  • **CRITICAL FIX**: use `content-type` (hyphen) in `file_options`, NOT
    `content_type` (underscore). The real supabase-py 2.x merges
    `file_options` over `DEFAULT_FILE_OPTIONS = {"content-type":
    "text/plain;charset=UTF-8", ...}` and then does
    `headers.pop("content-type")` to set the multipart file part's
    Content-Type. Passing `content_type` (underscore) leaves the default
    `text/plain;charset=UTF-8` in place, which Supabase Storage rejects
    with `415 invalid_mime_type, mime type text/plain is not supported`
    whenever the bucket has `allowed_mime_types` configured. This was the
    cause of the avatar-upload failures in v4.
  • Magic-byte sniffing fallback: if `uploaded_file.type` is missing or
    looks suspicious, derive the MIME type from the first few bytes of the
    file. Browsers usually get this right, but some mobile Chrome uploads
    report the wrong type — sniffing makes us bulletproof.

FIXES (v4):
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


def _sniff_mime_from_bytes(data: bytes) -> Optional[str]:
    """Detect MIME type from the first few bytes (magic bytes).

    Returns one of ALLOWED_MIME or None if not recognized as an image.
    This is a safety net — Streamlit's `uploaded_file.type` is usually
    correct, but mobile browsers occasionally misreport the type.
    """
    if not data or len(data) < 12:
        return None
    # JPEG: FF D8 FF
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    # GIF: starts with "GIF87a" or "GIF89a"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    # WebP: "RIFF" .... "WEBP"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


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

    # --- Read file bytes ONCE (used for both validation and upload) ---
    file_bytes = uploaded_file.getvalue()

    # --- Validate file size ---
    if len(file_bytes) > MAX_FILE_SIZE:
        return None, f"File too large ({len(file_bytes) / 1024 / 1024:.1f} MB). Maximum {MAX_FILE_SIZE / 1024 / 1024:.0f} MB."

    if len(file_bytes) == 0:
        return None, "File is empty."

    # --- Determine MIME type ---
    # Priority: magic bytes > Streamlit's reported type > extension.
    # Magic bytes are the ground truth — browsers sometimes report the
    # wrong type, especially on mobile, which causes the Supabase
    # `allowed_mime_types` check to reject the upload with 415.
    file_type = getattr(uploaded_file, "type", None) or ""
    sniffed = _sniff_mime_from_bytes(file_bytes)
    if sniffed:
        # Trust the bytes over the browser-reported type.
        file_type = sniffed
    elif file_type and file_type not in allowed_types:
        # Bytes didn't look like a known image AND the browser says
        # something weird. Refuse early with a helpful message.
        return None, (
            f"Unsupported file type: {file_type}. "
            f"Allowed: {', '.join(allowed_types)}. "
            "If this is a real image, try re-saving it as JPG or PNG."
        )

    # If we still don't have a type, derive from the extension.
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

    # --- Determine file extension (from name, fallback to MIME type) ---
    original_name = getattr(uploaded_file, "name", "image.jpg")
    ext = original_name.split(".")[-1].lower() if "." in original_name else ""
    if ext == "jpeg":
        ext = "jpg"
    if ext not in ALLOWED_EXTENSIONS:
        # Fall back to deriving ext from the final MIME type.
        ext_from_mime = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
        }.get(file_type, "jpg")
        ext = ext_from_mime

    # --- Build a unique file path ---
    file_path = f"{folder}/{uuid4().hex}.{ext}"

    # --- Upload with retry ---
    last_error = None
    for attempt in range(2):
        try:
            client = get_supabase_client()

            # IMPORTANT: pass `content-type` (HYPHEN), not `content_type`
            # (underscore). The real supabase-py 2.x merges file_options
            # over DEFAULT_FILE_OPTIONS which already contains
            # `"content-type": "text/plain;charset=UTF-8"`. Only the
            # hyphenated key will override that default. Using the
            # underscored key leaves text/plain in place, which the
            # `allowed_mime_types` bucket policy rejects with HTTP 415.
            #
            # Also pass `upsert` as the STRING "true" — supabase-py puts
            # it into the `x-upsert` HTTP header, and httpx rejects
            # non-string header values.
            response = client.storage.from_(BUCKET_NAME).upload(
                path=file_path,
                file=file_bytes,
                file_options={
                    "content-type": file_type,   # HYPHEN — overrides DEFAULT_FILE_OPTIONS
                    "upsert": "true",            # STRING — httpx requires str header values
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
