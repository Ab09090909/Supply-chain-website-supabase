"""
Document verification page — shown after signup.

Users must upload a national ID, driver's license, or business license before
they can access any page except the marketplace.

Flow:
  1. User signs up → verification_status = 'pending'
  2. App routes them here (verification page)
  3. User uploads document(s)
  4. Admin reviews → sets verification_status to 'verified' or 'rejected'
  5. Until verified, user can ONLY access marketplace + this verification page
"""
from __future__ import annotations

import streamlit as st
from uuid import uuid4

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.storage import upload_image


DOCUMENT_TYPES = [
    ("national_id", "🆔 National ID"),
    ("drivers_license", "🚗 Driver's License"),
    ("passport", "📘 Passport"),
    ("business_license", "🏢 Business License"),
    ("tax_certificate", "🧾 Tax Certificate"),
    ("other", "📄 Other Government Document"),
]


def is_user_verified() -> bool:
    """Check if the current user is verified.

    LENIENT: If verification_status is not set (e.g. migration_v5 not run yet,
    or the column doesn't exist), returns True so the user can access the app.
    Only blocks access when verification_status is explicitly 'pending' or 'rejected'.
    """
    user = get_current_user()
    if not user:
        return False
    # Admins are always considered verified
    if user.get("role") == "admin":
        return True
    # If verification_status is not set at all, allow access (graceful degradation)
    status = user.get("verification_status")
    if status is None:
        return True  # column doesn't exist or value is null — allow access
    return status == "verified"


def get_verification_status() -> str:
    """Returns: 'pending', 'verified', 'rejected', or 'not_submitted'."""
    user = get_current_user()
    if not user:
        return "not_submitted"
    if user.get("role") == "admin":
        return "verified"
    status = user.get("verification_status")
    if status is None:
        return "not_required"  # column doesn't exist — verification not enforced
    return status or "pending"


def render_verification_page():
    """The page shown to unverified users for document upload."""
    page_header("🔐 Account Verification", "Upload your documents to get verified and unlock all features")

    user = get_current_user()
    if not user:
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
            "While you wait, you can browse the **Marketplace** to see available products. "
            "All other features will unlock once you're verified."
        )

    if status == "rejected":
        st.error(
            "❌ **Verification rejected.**\n\n"
            "Your submitted documents were not approved. Please re-upload clearer copies "
            "of your documents. See the review notes below (if any)."
        )
        if user.get("verification_notes"):
            st.warning(f"**Admin notes:** {user['verification_notes']}")

    st.markdown("---")

    # ---- Why we need this ----
    with st.expander("📋 Why do we need verification?"):
        st.markdown("""
        **To keep our platform safe for everyone**, we require all users to verify their identity before they can:
        - 📦 Place orders
        - 💬 Send messages to other users
        - 🤖 Use AI features (matching, predictions)
        - 👤 Edit their profile

        **What we accept:**
        - 🆔 National ID (front + back)
        - 🚗 Driver's License
        - 📘 Passport (photo page)
        - 🏢 Business License (for merchants/producers)
        - 🧾 Tax Certificate (for businesses)

        **Privacy:** Your documents are encrypted and only visible to admin reviewers. They are never shared with other users.

        **Marketplace access:** You can browse products immediately — verification is only needed to interact (order, message, etc.).
        """)

    st.markdown("---")

    # ---- Upload form ----
    st.markdown("### 📤 Upload Your Documents")

    client = get_supabase_client()

    # Show previously uploaded docs
    try:
        existing_docs = (
            client.table("verification_documents")
            .select("*")
            .eq("user_id", user["id"])
            .order("uploaded_at", desc=True)
            .execute()
        ).data or []
    except Exception:
        existing_docs = []

    if existing_docs:
        st.markdown("#### Your Submitted Documents")
        for doc in existing_docs:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                type_label = next((label for code, label in DOCUMENT_TYPES if code == doc["document_type"]), doc["document_type"])
                st.markdown(f"**{type_label}** — `{doc.get('document_name', 'document')}`")
                st.caption(f"Uploaded {doc.get('uploaded_at', '')[:10] if doc.get('uploaded_at') else '—'}")
                if doc.get("review_notes"):
                    st.caption(f"Admin notes: {doc['review_notes']}")
            with col2:
                status_emoji = {"approved": "✅", "pending": "⏳", "rejected": "❌"}.get(doc["status"], "❓")
                st.markdown(f"**Status:** {status_emoji} {doc['status'].title()}")
            with col3:
                if doc.get("file_url"):
                    # Try to show image preview
                    if doc.get("mime_type", "").startswith("image/"):
                        try:
                            st.image(doc["file_url"], width=80)
                        except Exception:
                            st.markdown("📄 [View](doc_url)")
                    else:
                        st.markdown("📄 PDF")

        st.markdown("---")

    # Upload new document
    st.markdown("#### Upload New Document")

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
                help="The ID/number printed on your document. Helps us verify faster.",
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
        # Upload to the verification-docs bucket (private)
        from database.connection import _get_config
        from supabase import create_client

        # We need to upload to a private bucket — use the regular client
        client = get_supabase_client()

        file_bytes = uploaded_file.getvalue()
        if len(file_bytes) > 10 * 1024 * 1024:
            st.error("File too large. Maximum 10 MB.")
            return

        ext = uploaded_file.name.split(".")[-1].lower()
        if ext == "jpeg":
            ext = "jpg"
        file_path = f"{user['id']}/{uuid4().hex}.{ext}"
        mime_type = uploaded_file.type or "application/octet-stream"

        # Upload to storage
        client.storage.from_("verification-docs").upload(
            path=file_path,
            file=file_bytes,
            file_options={"content_type": mime_type, "upsert": True},
        )

        # Get URL (for admin to view; bucket is private so this URL requires auth)
        file_url = client.storage.from_("verification-docs").get_public_url(file_path)

        # Create DB record
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

        # Update profile verification status to pending
        client.table("profiles").update({
            "verification_status": "pending",
            "verification_submitted_at": "now()",
        }).eq("id", user["id"]).execute()

        # Update session state
        st.session_state["user"]["verification_status"] = "pending"

        # Notify admins
        try:
            admins = client.table("profiles").select("id").eq("role", "admin").execute().data or []
            for admin in admins:
                client.table("notifications").insert({
                    "user_id": admin["id"],
                    "sender_id": user["id"],
                    "title": "📄 New Verification Request",
                    "message": f"{user['full_name']} ({user['email']}) submitted a {doc_type.replace('_', ' ')} for verification.",
                    "type": "info",
                }).execute()
        except Exception:
            pass

        st.success("✅ Document uploaded successfully! Your verification is now pending review.")
        st.balloons()
        st.rerun()

    except Exception as e:
        err = str(e).lower()
        if "bucket" in err and "not found" in err:
            st.error("❌ Storage bucket 'verification-docs' not found. Run `supabase/migration_v5.sql` first.")
        else:
            st.error(f"Upload failed: {e}")
