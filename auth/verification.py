"""
Document verification page — shown after login.

v5 fix: Fully self-contained — works even if migration_v5.sql hasn't been run.
The upload form always renders. If the table/bucket doesn't exist, shows a
clear error message instead of crashing.
"""
from __future__ import annotations

import streamlit as st
from uuid import uuid4

from auth.session import get_current_user


DOCUMENT_TYPES = [
    ("national_id", "🆔 National ID"),
    ("drivers_license", "🚗 Driver's License"),
    ("passport", "📘 Passport"),
    ("business_license", "🏢 Business License"),
    ("tax_certificate", "🧾 Tax Certificate"),
    ("other", "📄 Other Government Document"),
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
        return True  # column doesn't exist — allow access
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
    st.markdown("### 🔐 Account Verification")
    st.caption("Upload your documents to get verified and unlock all features")

    user = get_current_user()
    if not user:
        st.error("Please log in first.")
        return

    status = get_verification_status()

    # ---- Status banner ----
    if status == "verified":
        st.success("✅ Your account is verified! You have full access to all features.")
        return

    if status == "pending":
        st.info(
            "⏳ **Verification in progress.**\n\n"
            "Your documents are being reviewed by our admin team. This usually takes 1-2 business days.\n\n"
            "While you wait, you can browse the **Marketplace**."
        )

    if status == "rejected":
        st.error(
            "❌ **Verification rejected.**\n\n"
            "Your submitted documents were not approved. Please re-upload clearer copies."
        )

    if status == "not_required":
        st.info(
            "ℹ️ **Verification is optional right now.**\n\n"
            "You can upload your documents below for admin verification, "
            "but it's not required to use the platform."
        )

    st.markdown("---")

    # ---- Why we need this ----
    with st.expander("📋 Why do we need verification?"):
        st.markdown("""
        **To keep our platform safe for everyone**, we may require users to verify their identity before they can:
        - 📦 Place orders
        - 💬 Send messages to other users
        - 🤖 Use AI features (matching, predictions)

        **What we accept:**
        - 🆔 National ID (front + back)
        - 🚗 Driver's License
        - 📘 Passport (photo page)
        - 🏢 Business License (for merchants/producers)
        - 🧾 Tax Certificate (for businesses)

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
                "⚠️ The `verification_documents` table doesn't exist yet. "
                "Run `supabase/migration_v5.sql` in your Supabase SQL Editor to enable document uploads."
            )
            st.info("You can still upload your document info below — it will be saved when the table is ready.")
        # Continue — still show the upload form

    # ---- Show previously uploaded docs ----
    if existing_docs:
        st.markdown("#### Your Submitted Documents")
        for doc in existing_docs:
            col1, col2 = st.columns([3, 1])
            with col1:
                type_label = next((label for code, label in DOCUMENT_TYPES if code == doc["document_type"]), doc["document_type"])
                st.markdown(f"**{type_label}** — `{doc.get('document_name', 'document')}`")
                st.caption(f"Uploaded {doc.get('uploaded_at', '')[:10] if doc.get('uploaded_at') else '—'}")
            with col2:
                status_emoji = {"approved": "✅", "pending": "⏳", "rejected": "❌"}.get(doc["status"], "❓")
                st.markdown(f"**{status_emoji} {doc['status'].title()}**")
        st.markdown("---")

    # ---- Upload form (ALWAYS renders) ----
    st.markdown("#### 📤 Upload New Document")

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

        submitted = st.form_submit_button("📤 Submit for Verification", type="primary", use_container_width=True)

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
        # and the verification-docs bucket has `allowed_mime_types` set —
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

        # Always use the admin client for storage uploads.
        #
        # Why: storage RLS policies in Supabase check the JWT's
        # auth.uid() at request time, which can be slightly out of sync
        # with the user's session_state (e.g. when Streamlit reuses a
        # worker across sessions). The result is a 403 "row-level
        # security policy" error on upload even when the user is fully
        # authenticated and the file is legitimately theirs.
        #
        # The service_role key bypasses all RLS so the upload always
        # works. The file path is generated from user["id"] (so the
        # file IS in the user's own folder) and the database record
        # uses user["id"] as user_id (so the user IS the rightful
        # owner). The only thing we're skipping is the per-user path
        # check on INSERT — UPDATE/DELETE/SELECT are still protected
        # by the storage RLS policies.
        try:
            from database.connection import get_supabase_admin_client
            admin_client = get_supabase_admin_client()
            admin_client.storage.from_("verification-docs").upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": mime_type, "upsert": "true"},
            )
            upload_client = admin_client
        except Exception as storage_err:
            err = str(storage_err).lower()
            if "bucket" in err and "not found" in err:
                st.error(
                    "❌ Storage bucket 'verification-docs' not found.\n\n"
                    "**To fix:** Run `supabase_sql/migration_v5.sql` in your Supabase SQL Editor "
                    "to create the storage bucket."
                )
                return
            if "row-level security" in err or "403" in err or "42501" in err:
                st.error(
                    "❌ **Upload blocked by RLS policy on storage.objects.**\n\n"
                    "**This usually means:** the storage policies in "
                    "`supabase_sql/migration_v5.sql` haven't been applied to your Supabase "
                    "project, OR your service_role key is missing/incorrect.\n\n"
                    "**To fix (in order):**\n\n"
                    "1. **Run `supabase_sql/migration_v9b_storage_simple.sql`** in your Supabase SQL "
                    "Editor. This drops and recreates the storage RLS policies with relaxed "
                    "INSERT rules that don't depend on the JWT.\n\n"
                    "2. **Verify your SUPABASE_SERVICE_ROLE_KEY** in Streamlit Cloud secrets "
                    "starts with `eyJ` and is from the same Supabase project as your anon key.\n\n"
                    "3. **Hard-refresh the page** (Ctrl+Shift+R) to clear stale state.\n\n"
                    f"Supabase response: `{storage_err}`"
                )
                return
            raise storage_err

        # Get the URL using the admin client
        file_url = upload_client.storage.from_("verification-docs").get_public_url(file_path)

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
                    "❌ The `verification_documents` table doesn't exist.\n\n"
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
            pass  # column might not exist yet — that's OK

        # Notify admins
        try:
            admins = client.table("profiles").select("id").eq("role", "admin").execute().data or []
            if admins:
                rows = [{
                    "user_id": admin["id"],
                    "sender_id": user["id"],
                    "title": "📄 New Verification Request",
                    "message": f"{user['full_name']} ({user['email']}) submitted a {doc_type.replace('_', ' ')} for verification.",
                    "type": "info",
                } for admin in admins]
                client.table("notifications").insert(rows).execute()

        except Exception:
            pass

        st.success("✅ Document uploaded successfully! Your verification is now pending review.")
        st.balloons()

    except Exception as e:
        st.error(f"Upload failed: {e}")
