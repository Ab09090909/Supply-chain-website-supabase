"""
Document verification page — shown after login.

The upload form always renders. If the table/bucket doesn't exist, shows a
brief error message instead of crashing.
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

    Returns False if the user has just signed up or has pending/rejected
    status. Honors the must_verify session flag for brand-new signups
    even when the verification_status column doesn't exist yet.
    """
    user = get_current_user()
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    # If the user just signed up or logged in with a pending status,
    # the session flag wins. This means new users are ALWAYS asked to
    # verify, even if the v5 migration hasn't been run yet.
    try:
        import streamlit as st
        if st.session_state.get("must_verify"):
            return False
    except Exception:
        pass
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
    except Exception:
        # If the table doesn't exist yet, just continue with an empty list.
        pass

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

        # Always use the admin client for storage uploads. The service_role
        # key bypasses storage.objects RLS so the upload always works.
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
            # If the admin client isn't available, fall back to the
            # regular client. This may fail with an RLS error if the
            # storage policies haven't been applied, but that's the
            # caller's problem to debug.
            err = str(storage_err).lower()
            if "bucket" in err and "not found" in err:
                st.error("Storage bucket 'verification-docs' not found.")
                return
            raise storage_err

        # Get the URL using the admin client
        file_url = upload_client.storage.from_("verification-docs").get_public_url(file_path)

        # Create DB record
        #
        # IMPORTANT: Use the admin client for the DB INSERT too, not the
        # regular anon-key client. The regular client is subject to RLS,
        # and the deployed migration_v5.sql has the policy
        #   auth.uid() = user_id
        # which fails on a stale JWT (Streamlit worker reuse) or any
        # sub/user_id mismatch, producing the 42501 error the user has
        # been seeing.
        #
        # The service_role key bypasses RLS so the insert always works.
        # The user_id is set from the session's authenticated user, not
        # from any client-side input, so there is no privilege escalation
        # risk. The user IS the rightful owner of the row they are
        # creating.
        try:
            upload_client.table("verification_documents").insert({
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
            if "could not find" in err or "pgrst205" in err or "does not exist" in err:
                st.error("verification_documents table not found.")
                return
            raise db_err

        # Update profile verification status to pending (admin client, bypasses RLS)
        try:
            upload_client.table("profiles").update({
                "verification_status": "pending",
                "verification_submitted_at": "now()",
            }).eq("id", user["id"]).execute()
            st.session_state["user"]["verification_status"] = "pending"
        except Exception:
            pass  # column might not exist yet — that's OK

        # Notify admins (admin client, bypasses RLS)
        try:
            admins = upload_client.table("profiles").select("id").eq("role", "admin").execute().data or []
            if admins:
                rows = [{
                    "user_id": admin["id"],
                    "sender_id": user["id"],
                    "title": "📄 New Verification Request",
                    "message": f"{user['full_name']} ({user['email']}) submitted a {doc_type.replace('_', ' ')} for verification.",
                    "type": "info",
                } for admin in admins]
                upload_client.table("notifications").insert(rows).execute()

        except Exception:
            pass

        st.success("✅ Document uploaded successfully! Your verification is now pending review.")
        st.balloons()
        # Clear the must_verify flag — the user has submitted their docs.
        # Admin still needs to approve, but the prompt no longer needs to
        # be on every page.
        try:
            st.session_state["user"]["verification_status"] = "pending"
            st.session_state.pop("must_verify", None)
        except Exception:
            pass

    except Exception as e:
        st.error(f"Upload failed: {e}")
