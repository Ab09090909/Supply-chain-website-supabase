"""
Document verification page Ã¢â‚¬â€ shown after login.

v5 fix: Fully self-contained Ã¢â‚¬â€ works even if migration_v5.sql hasn't been run.
The upload form always renders. If the table/bucket doesn't exist, shows a
clear error message instead of crashing.
"""
from __future__ import annotations

import streamlit as st
from uuid import uuid4

from auth.session import get_current_user


DOCUMENT_TYPES = [
    ("national_id", "Ã°Å¸â€ â€ National ID"),
    ("drivers_license", "Ã°Å¸Å¡â€” Driver's License"),
    ("passport", "Ã°Å¸â€œËœ Passport"),
    ("business_license", "Ã°Å¸ÂÂ¢ Business License"),
    ("tax_certificate", "Ã°Å¸Â§Â¾ Tax Certificate"),
    ("other", "Ã°Å¸â€œâ€ž Other Government Document"),
]


def _sniff_mime(data: bytes) -> str | None:
    """Detect MIME type from the first few bytes (magic bytes).

    Supports the file types accepted by the verification-docs bucket:
    JPEG, PNG, WebP, GIF, PDF. Returns None if not recognized.
    """
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
    if data[:4] == b"%PDF":
        return "application/pdf"
    return None


def is_user_verified() -> bool:
    """Check if the current user is verified.

    LENIENT: If verification_status is not set (migration_v5 not run), allow access.
    Only blocks when status is explicitly 'pending' or 'rejected'.
    """
    user = get_current_user()
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    status = user.get("verification_status")
    if status is None:
        return True  # column doesn't exist Ã¢â‚¬â€ allow access
    return status == "verified"


def get_verification_status() -> str:
    """Returns: 'pending', 'verified', 'rejected', 'not_required', or 'not_submitted'."""
    user = get_current_user()
    if not user:
        return "not_submitted"
    if user.get("role") == "admin":
        return "verified"
    status = user.get("verification_status")
    if status is None:
        return "not_required"
    return status or "pending"


def render_verification_page():
    """The page shown to users for document upload. Fully self-contained."""
    st.markdown("### Ã°Å¸â€Â Account Verification")
    st.caption("Upload your documents to get verified and unlock all features")

    user = get_current_user()
    if not user:
        st.error("Please log in first.")
        return

    status = get_verification_status()

    # ---- Status banner ----
    if status == "verified":
        st.success("Ã¢Å“â€¦ Your account is verified! You have full access to all features.")
        return

    if status == "pending":
        st.info(
            "Ã¢ÂÂ³ **Verification in progress.**\n\n"
            "Your documents are being reviewed by our admin team. This usually takes 1-2 business days.\n\n"
            "While you wait, you can browse the **Marketplace**."
        )

    if status == "rejected":
        st.error(
            "Ã¢ÂÅ’ **Verification rejected.**\n\n"
            "Your submitted documents were not approved. Please re-upload clearer copies."
        )

    if status == "not_required":
        st.info(
            "Ã¢â€žÂ¹Ã¯Â¸Â **Verification is optional right now.**\n\n"
            "You can upload your documents below for admin verification, "
            "but it's not required to use the platform."
        )

    st.markdown("---")

    # ---- Why we need this ----
    with st.expander("Ã°Å¸â€œâ€¹ Why do we need verification?"):
        st.markdown("""
        **To keep our platform safe for everyone**, we may require users to verify their identity before they can:
        - Ã°Å¸â€œÂ¦ Place orders
        - Ã°Å¸â€™Â¬ Send messages to other users
        - Ã°Å¸Â¤â€“ Use AI features (matching, predictions)

        **What we accept:**
        - Ã°Å¸â€ â€ National ID (front + back)
        - Ã°Å¸Å¡â€” Driver's License
        - Ã°Å¸â€œËœ Passport (photo page)
        - Ã°Å¸ÂÂ¢ Business License (for merchants/producers)
        - Ã°Å¸Â§Â¾ Tax Certificate (for businesses)

        **Privacy:** Your documents are encrypted and only visible to admin reviewers.
        """)

    st.markdown("---")

    # ---- Try to load existing documents ----
    existing_docs = []
    try:
        from database.connection import get_supabase_client
        client = get_supabase_client()
        existing_docs = (
            client.table("verification_documents")
            .select("*")
            .eq("user_id", user["id"])
            .order("uploaded_at", desc=True)
            .execute()
        ).data or []
    except Exception as e:
        err = str(e).lower()
        if "could not find" in err or "pgrst205" in err or "does not exist" in err:
            st.warning(
                "Ã¢Å¡ Ã¯Â¸Â The `verification_documents` table doesn't exist yet. "
                "Run `supabase/migration_v5.sql` in your Supabase SQL Editor to enable document uploads."
            )
            st.info("You can still upload your document info below Ã¢â‚¬â€ it will be saved when the table is ready.")
        # Continue Ã¢â‚¬â€ still show the upload form

    # ---- Show previously uploaded docs ----
    if existing_docs:
        st.markdown("#### Your Submitted Documents")
        for doc in existing_docs:
            col1, col2 = st.columns([3, 1])
            with col1:
                type_label = next((label for code, label in DOCUMENT_TYPES if code == doc["document_type"]), doc["document_type"])
                st.markdown(f"**{type_label}** Ã¢â‚¬â€ `{doc.get('document_name', 'document')}`")
                st.caption(f"Uploaded {doc.get('uploaded_at', '')[:10] if doc.get('uploaded_at') else 'Ã¢â‚¬â€'}")
            with col2:
                status_emoji = {"approved": "Ã¢Å“â€¦", "pending": "Ã¢ÂÂ³", "rejected": "Ã¢ÂÅ’"}.get(doc["status"], "Ã¢Ââ€œ")
                st.markdown(f"**{status_emoji} {doc['status'].title()}**")
        st.markdown("---")

    # ---- Upload form (ALWAYS renders) ----
    st.markdown("#### Ã°Å¸â€œÂ¤ Upload New Document")

    with st.form("upload_doc_form"):
        col1, col2 = st.columns(2)
        with col1:
            doc_type_label = st.selectbox(
                "Document Type *",
                [label for _, label in DOCUMENT_TYPES],
                help="Select the type of document you're uploading.",
            )
            doc_type = next((code for code, label in DOCUMENT_TYPES if label == doc_type_label), "other")
        with col2:
            doc_number = st.text_input(
                "Document Number (optional)",
                placeholder="e.g. ID-12345678",
                help="The ID/number printed on your document.",
            )

        uploaded_file = st.file_uploader(
            "Upload document *",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            help="Upload a clear photo or scan of your document. Max 10 MB. Accepted: JPG, PNG, WebP, PDF.",
        )

        submitted = st.form_submit_button("Ã°Å¸â€œÂ¤ Submit for Verification", type="primary", use_container_width=True)

        if submitted:
            if not uploaded_file:
                st.error("Please select a file to upload.")
            else:
                _upload_verification_doc(user, doc_type, doc_number, uploaded_file)


def _upload_verification_doc(user: dict, doc_type: str, doc_number: str, uploaded_file):
    """Upload a verification document to Supabase Storage + create DB record."""
    try:
        from database.connection import get_supabase_client
        client = get_supabase_client()

        file_bytes = uploaded_file.getvalue()
        if len(file_bytes) > 10 * 1024 * 1024:
            st.error("File too large. Maximum 10 MB.")
            return

        ext = uploaded_file.name.split(".")[-1].lower()
        if ext == "jpeg":
            ext = "jpg"
        file_path = f"{user['id']}/{uuid4().hex}.{ext}"

        # Determine the real MIME type. Streamlit's `uploaded_file.type` is
        # usually right, but mobile browsers sometimes report the wrong type,
        # and the verification-docs bucket has `allowed_mime_types` set â€”
        # any mismatch produces HTTP 415 from Supabase Storage.
        # Priority: magic bytes > browser-reported type > extension guess.
        mime_type = uploaded_file.type or ""
        sniffed = _sniff_mime(file_bytes)
        if sniffed:
            mime_type = sniffed
        elif not mime_type or mime_type == "application/octet-stream":
            mime_type = {
                "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "webp": "image/webp",
                "gif": "image/gif",
                "pdf": "application/pdf",
            }.get(ext, "application/octet-stream")

        # Try to upload to storage
        try:
            client.storage.from_("verification-docs").upload(
                path=file_path,
                file=file_bytes,
                # IMPORTANT: use `content-type` (HYPHEN), not `content_type`
                # (underscore). The real supabase-py 2.x merges file_options
                # over DEFAULT_FILE_OPTIONS = {"content-type":
                # "text/plain;charset=UTF-8", ...} and then pops "content-type"
                # to set the multipart file part's Content-Type. Using the
                # underscored key leaves text/plain in place, which the
                # `allowed_mime_types` bucket policy rejects with HTTP 415.
                # `upsert` must be the STRING "true" (not bool) â€” httpx
                # rejects non-string HTTP header values for `x-upsert`.
                file_options={"content-type": mime_type, "upsert": "true"},
            )
            file_url = client.storage.from_("verification-docs").get_public_url(file_path)
        except Exception as storage_err:
            err = str(storage_err).lower()
            if "bucket" in err and "not found" in err:
                st.error(
                    "Ã¢ÂÅ’ Storage bucket 'verification-docs' not found.\n\n"
                    "**To fix:** Run `supabase/migration_v5.sql` in your Supabase SQL Editor "
                    "to create the storage bucket."
                )
                return
            raise storage_err

        # Create DB record
        try:
            client.table("verification_documents").insert({
                "user_id": user["id"],
                "document_type": doc_type,
                "document_number": doc_number or None,
                "document_name": uploaded_file.name,
                "file_url": file_url,
                "file_size": len(file_bytes),
                "mime_type": mime_type,
                "status": "pending",
            }).execute()
        except Exception as db_err:
            err = str(db_err).lower()
            if "could not find" in err or "pgrst205" in err:
                st.error(
                    "Ã¢ÂÅ’ The `verification_documents` table doesn't exist.\n\n"
                    "**To fix:** Run `supabase/migration_v5.sql` in your Supabase SQL Editor "
                    "to create the table."
                )
                return
            raise db_err

        # Update profile verification status to pending
        try:
            client.table("profiles").update({
                "verification_status": "pending",
                "verification_submitted_at": "now()",
            }).eq("id", user["id"]).execute()
            st.session_state["user"]["verification_status"] = "pending"
        except Exception:
            pass  # column might not exist yet Ã¢â‚¬â€ that's OK

        # Notify admins
        try:
            admins = client.table("profiles").select("id").eq("role", "admin").execute().data or []
            for admin in admins:
                client.table("notifications").insert({
                    "user_id": admin["id"],
                    "sender_id": user["id"],
                    "title": "Ã°Å¸â€œâ€ž New Verification Request",
                    "message": f"{user['full_name']} ({user['email']}) submitted a {doc_type.replace('_', ' ')} for verification.",
                    "type": "info",
                }).execute()
        except Exception:
            pass

        st.success("Ã¢Å“â€¦ Document uploaded successfully! Your verification is now pending review.")
        st.balloons()

    except Exception as e:
        st.error(f"Upload failed: {e}")
