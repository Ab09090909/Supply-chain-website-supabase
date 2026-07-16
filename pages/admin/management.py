"""
Admin Management page — comprehensive admin control center.

Three sub-tabs:
  A) 👥 User Management  — verify users, view uploaded documents, activate/deactivate, delete
  B) 📦 Product Management — view/remove/delete any posted product
  C) 🗄️ Database Management — view/edit/add/delete rows in any table

The summary card on each tab uses the same green-gradient + metric-grid
design as the admin dashboard's "Orders & Products" card for visual
consistency across the admin section.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional

from auth.session import get_current_user
from database.connection import get_supabase_admin_client, get_supabase_client
from utils.ui import page_header, role_badge
from utils.helpers import format_currency, format_datetime
from utils.db_health import is_table_available
from pages.admin._card import (
    inject_card_css,
    admin_card as _card,
    admin_metric_box as _metric_box,
)


# ─── CSS for user management card + document cards ──────────────────────────
# Injected by render_admin_management() right after inject_card_css(). Scoped
# to the .um- class prefix to avoid collisions with the dashboard's CSS.
_USER_MANAGEMENT_CSS = """
<style>
.um-user-card {
    background: #ffffff;
    border: 1px solid #e4ece6;
    border-radius: 14px;
    padding: 16px 18px;
    margin-bottom: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    display: flex;
    align-items: center;
    gap: 18px;
    transition: box-shadow 0.2s ease, transform 0.15s ease;
}
.um-user-card:hover {
    box-shadow: 0 4px 14px rgba(16,185,129,0.10);
    transform: translateY(-1px);
}
.um-user-card-left {
    display: flex;
    align-items: center;
    gap: 14px;
    flex: 1 1 50%;
    min-width: 0;
}
.um-user-info { min-width: 0; }
.um-user-name {
    font-size: 1.05rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.2;
    word-break: break-word;
}
.um-user-email {
    font-size: 0.82rem;
    color: #64748b;
    margin-top: 2px;
    word-break: break-all;
}
.um-user-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
}
.um-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.um-user-card-right {
    flex: 1 1 50%;
    min-width: 0;
    padding-left: 14px;
    border-left: 1px solid #f1f5f9;
}
.um-user-verif {
    font-size: 0.92rem;
    font-weight: 600;
    margin-bottom: 4px;
}
.um-user-meta {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 2px;
}

.um-doc-card {
    background: #f8fafc;
    border: 1px solid #e4ece6;
    border-radius: 12px;
    padding: 14px 16px;
    margin: 8px 0 10px 0;
}
.um-doc-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
}
.um-doc-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
}
.um-doc-filename {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 2px;
    word-break: break-all;
}
.um-doc-status {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
}
.um-doc-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    margin-top: 10px;
    font-size: 0.78rem;
    color: #64748b;
}
</style>
"""


def _resolve_doc_preview_url(doc: dict, client) -> tuple[Optional[str], str]:
    """Resolve a usable preview URL for a verification document.

    Tries, in order:
      1. Signed URL via the admin client (works on private buckets)
      2. The stored public URL (works on public buckets)
      3. Returns (None, "no-url") if neither works.

    Returns:
        (url, source_label) where source_label is one of
        "signed", "public", "no-url" — shown as a small caption next
        to the preview so the admin knows which access path is in use.
    """
    file_url = doc.get("file_url")
    if not file_url:
        return None, "no-url"

    # Clean up: if the stored value is itself malformed (e.g. someone
    # accidentally saved a JSON-encoded dict), extract the URL from it.
    if file_url.startswith("[") or file_url.startswith("{"):
        import json as _json
        try:
            parsed = _json.loads(file_url)
            if isinstance(parsed, dict):
                file_url = (
                    parsed.get("signedURL")
                    or parsed.get("signedUrl")
                    or parsed.get("url")
                    or file_url
                )
            elif isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                file_url = (
                    parsed[0].get("signedURL")
                    or parsed[0].get("signedUrl")
                    or parsed[0].get("url")
                    or file_url
                )
        except Exception:
            pass  # leave as-is, will be used as a (broken) URL

    # Try to get a signed URL (works on private buckets)
    try:
        marker = "/verification-docs/"
        idx = file_url.find(marker)
        if idx >= 0:
            bucket_path = file_url[idx + len(marker):]
            # Strip any query string before passing to create_signed_url
            if "?" in bucket_path:
                bucket_path = bucket_path.split("?", 1)[0]
            try:
                admin_client = get_supabase_admin_client()
                signed = admin_client.storage.from_("verification-docs").create_signed_url(
                    bucket_path, expires_in=300
                )
                if signed and signed.startswith("http"):
                    return signed, "signed"
            except Exception:
                pass
    except Exception:
        pass

    # Fall back to whatever URL is in the DB
    if file_url.startswith("http"):
        return file_url, "public"
    return None, "no-url"


def render_admin_management():
    page_header("⚙️ Management", "Comprehensive admin control center")

    user = get_current_user()
    if not user:
        return

    # Inject the card CSS once for the whole page (idempotent).
    inject_card_css()
    st.markdown(_USER_MANAGEMENT_CSS, unsafe_allow_html=True)

    sub1, sub2, sub3 = st.tabs([
        "👥 User Management",
        "📦 Product Management",
        "🗄️ Database Management",
    ])

    with sub1:
        _render_user_management(user)
    with sub2:
        _render_product_management(user)
    with sub3:
        _render_database_management(user)


# ---------------------------------------------------------------------------
# A) USER MANAGEMENT
# ---------------------------------------------------------------------------
def _render_user_management(admin: dict):
    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    try:
        users = client.table("profiles").select("*").order("created_at", desc=True).execute().data or []
    except Exception as e:
        st.error(f"Failed to load users: {e}")
        return

    # Summary card — same design as the dashboard's "Orders & Products"
    pending_verification = sum(1 for u in users if u.get("verification_status") == "pending")
    verified = sum(1 for u in users if u.get("verification_status") == "verified")
    rejected = sum(1 for u in users if u.get("verification_status") == "rejected")
    active = sum(1 for u in users if u.get("is_active"))

    _card(
        icon="👥",
        title="User Management",
        subtitle="Verify users, view their documents, activate/deactivate, or delete accounts.",
        metrics_html=(
            _metric_box(str(len(users)), "Total Users", "👥")
            + _metric_box(
                str(pending_verification),
                "Pending Verification",
                "⏳",
                alert=pending_verification > 0,
            )
            + _metric_box(str(verified), "Verified", "✅")
            + _metric_box(str(rejected), "Rejected", "❌", alert=rejected > 0)
            + _metric_box(str(active), "Active", "🟢")
        ),
    )

    # Filter row
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("🔍 Search by name or email", placeholder="Search...")
    with col2:
        verif_filter = st.selectbox(
            "Filter by verification status",
            ["All", "pending", "verified", "rejected"],
            help="Show only users with a specific verification status.",
        )

    filtered = [
        u for u in users
        if (not search or search.lower() in u.get("email", "").lower() or search.lower() in u.get("full_name", "").lower())
        and (verif_filter == "All" or u.get("verification_status") == verif_filter)
    ]

    st.markdown(f"###### {len(filtered)} user(s)")

    for u in filtered:
        _render_user_card(u, admin)


def _render_user_card(u: dict, admin: dict):
    """Render a single user card with verification + management actions.

    Visual design: a modern card with:
      • Left: avatar + name + email (with gradient ring around avatar)
      • Middle: role badge + verification status pill
      • Right: action status (active/deactivated) + Manage button
      • Bottom: compact meta line (phone, location, joined)
    """
    is_self = u["id"] == admin["id"]
    verif_status = u.get("verification_status", "pending")
    verif_color = {"verified": "#10b981", "pending": "#f59e0b", "rejected": "#ef4444"}.get(verif_status, "#64748b")
    verif_emoji = {"verified": "✅", "pending": "⏳", "rejected": "❌"}.get(verif_status, "❓")
    is_active = bool(u.get("is_active"))
    role = u.get("role", "—").title()

    # Render the card as a styled HTML block — looks consistent and clean
    avatar_url = u.get("avatar_url")
    if avatar_url:
        avatar_html = (
            f"<img src='{avatar_url}' "
            f"style='width:56px; height:56px; border-radius:50%; object-fit:cover; "
            f"border:3px solid #10b981; box-shadow:0 2px 8px rgba(16,185,129,0.25);' />"
        )
    else:
        # Initials avatar
        initials = "".join(
            p[0].upper() for p in (u.get("full_name") or u.get("email") or "?").split()[:2]
        )
        avatar_html = (
            f"<div style='width:56px; height:56px; border-radius:50%; "
            f"background:linear-gradient(135deg,#10b981 0%,#059669 100%); "
            f"display:flex; align-items:center; justify-content:center; "
            f"color:#fff; font-weight:700; font-size:1.2rem; "
            f"box-shadow:0 2px 8px rgba(16,185,129,0.3);'>{initials}</div>"
        )

    # Role badge colors
    role_colors = {
        "Producer": ("#dcfce7", "#166534"),
        "Merchant": ("#dbeafe", "#1e40af"),
        "Customer": ("#fef3c7", "#92400e"),
        "Admin":    ("#fee2e2", "#991b1b"),
    }
    role_bg, role_fg = role_colors.get(role, ("#f1f5f9", "#475569"))

    # Active status pill
    active_bg = "#dcfce7" if is_active else "#fee2e2"
    active_fg = "#166534" if is_active else "#991b1b"
    active_text = "Active" if is_active else "Deactivated"

    # Phone + location line (hide None values)
    phone = u.get("phone") or "—"
    location = u.get("location") or "—"
    joined = format_datetime(u.get("created_at"), "%Y-%m-%d") if u.get("created_at") else "—"

    st.markdown(
        f"""
        <div class="um-user-card">
          <div class="um-user-card-left">
            {avatar_html}
            <div class="um-user-info">
              <div class="um-user-name">{u.get('full_name', '—')}</div>
              <div class="um-user-email">{u.get('email', '')}</div>
              <div class="um-user-badges">
                <span class="um-pill" style="background:{role_bg}; color:{role_fg};">{role}</span>
                <span class="um-pill" style="background:{active_bg}; color:{active_fg};">● {active_text}</span>
              </div>
            </div>
          </div>
          <div class="um-user-card-right">
            <div class="um-user-verif" style="color:{verif_color};">
              {verif_emoji} <span>Verification: <strong>{verif_status.title()}</strong></span>
            </div>
            <div class="um-user-meta">
              📞 {phone} &nbsp;·&nbsp; 📍 {location}
            </div>
            <div class="um-user-meta">
              📅 Joined {joined}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Action button (right-aligned, below the card)
    if is_self:
        st.caption("👤 (This is your own account)")
    else:
        # Two side-by-side buttons: Manage and quick Activate/Deactivate
        col_a, col_b, _spacer = st.columns([1, 1, 4])
        with col_a:
            label = "📋 Manage" if st.session_state.get("managing_user") != u["id"] else "✕ Close"
            btn_type = "secondary" if st.session_state.get("managing_user") != u["id"] else "primary"
            if st.button(label, key=f"manage_{u['id']}", use_container_width=True, type=btn_type):
                if st.session_state.get("managing_user") == u["id"]:
                    st.session_state.pop("managing_user", None)
                else:
                    st.session_state["managing_user"] = u["id"]
                st.rerun()
        with col_b:
            toggle_label = "🚫 Deactivate" if is_active else "✅ Activate"
            if st.button(toggle_label, key=f"toggle_{u['id']}", use_container_width=True):
                _toggle_user_active(u, not is_active, admin)

    # Expandable management panel — only renders for the selected user
    if st.session_state.get("managing_user") == u["id"]:
        _render_user_management_panel(u, admin)


def _render_user_management_panel(u: dict, admin: dict):
    """Detailed management panel for a single user.

    Visual design: a clean white panel with three sections:
      1) Header (gradient green) showing the user being managed
      2) Verification Documents (with previews + actions)
      3) User Actions (verify, reject, activate, delete, close)
    """
    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    # ---- Verification documents ----
    st.markdown("#### 📄 Verification Documents")
    try:
        docs = (
            client.table("verification_documents")
            .select("*")
            .eq("user_id", u["id"])
            .order("uploaded_at", desc=True)
            .execute()
        ).data or []
    except Exception:
        docs = []

    if docs:
        for doc in docs:
            doc_type = doc.get("document_type", "unknown").replace("_", " ").title()
            doc_status = doc.get("status", "pending")
            doc_status_color = {
                "approved": "#10b981", "pending": "#f59e0b", "rejected": "#ef4444"
            }.get(doc_status, "#64748b")
            doc_status_emoji = {
                "approved": "✅", "pending": "⏳", "rejected": "❌"
            }.get(doc_status, "❓")
            mime = doc.get("mime_type", "")
            file_size_kb = (doc.get("file_size") or 0) / 1024

            # Header row with document info
            st.markdown(
                f"""
                <div class="um-doc-card">
                  <div class="um-doc-header">
                    <div>
                      <div class="um-doc-title">📄 {doc_type}</div>
                      <div class="um-doc-filename">{doc.get('document_name', '—')}</div>
                    </div>
                    <div class="um-doc-status" style="background:{doc_status_color}1A; color:{doc_status_color};">
                      {doc_status_emoji} {doc_status.title()}
                    </div>
                  </div>
                  <div class="um-doc-meta">
                    {f'<span>🔢 #{doc["document_number"]}</span>' if doc.get("document_number") else ''}
                    <span>📦 {file_size_kb:.0f} KB</span>
                    <span>🗓️ {format_datetime(doc.get('uploaded_at'))}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Preview area — try signed URL first, fall back to public URL
            preview_url, preview_source = _resolve_doc_preview_url(doc, client)
            if preview_url:
                if mime.startswith("image/"):
                    try:
                        st.image(preview_url, caption=f"Document preview ({preview_source})", width=300)
                    except Exception:
                        st.markdown(
                            f"📄 [**View document**]({preview_url}) "
                            f"<span style='color:#94a3b8;font-size:0.75rem;'>({preview_source})</span>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        f"📄 [**Open document in new tab**]({preview_url}) "
                        f"<span style='color:#94a3b8;font-size:0.75rem;'>({preview_source})</span>",
                        unsafe_allow_html=True,
                    )
            else:
                st.warning(
                    "⚠️ Could not generate a preview URL for this document. "
                    "It may have been deleted from storage, or the storage "
                    "bucket is misconfigured."
                )

            # Approve / Reject / Delete buttons
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("✅ Approve Document", key=f"approve_doc_{doc['id']}", use_container_width=True):
                    _approve_document(doc, u, admin)
            with col_b:
                if st.button("❌ Reject Document", key=f"reject_doc_{doc['id']}", use_container_width=True):
                    _reject_document(doc, u, admin)
            with col_c:
                if st.button("🗑️ Delete Document", key=f"delete_doc_{doc['id']}", use_container_width=True):
                    _delete_document(doc, admin)
            st.markdown("<br/>", unsafe_allow_html=True)
    else:
        st.info("No verification documents uploaded.")

    # ---- User actions (destructive section) ----
    st.markdown("---")
    st.markdown("#### ⚙️ User Actions")

    is_active = bool(u.get("is_active"))
    is_self = u["id"] == admin["id"]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button(
            "✅ Verify User",
            key=f"verify_user_{u['id']}",
            use_container_width=True,
            type="primary",
            disabled=is_self,
            help="Mark this user as verified (no effect on your own account).",
        ):
            _verify_user(u, admin)
    with col2:
        if st.button(
            "❌ Reject Verification",
            key=f"reject_user_{u['id']}",
            use_container_width=True,
            disabled=is_self,
        ):
            _reject_user(u, admin)
    with col3:
        if is_active:
            if st.button(
                "🚫 Deactivate",
                key=f"deact_{u['id']}",
                use_container_width=True,
                disabled=is_self,
                help="Deactivated users cannot log in but their data is preserved.",
            ):
                _toggle_user_active(u, False, admin)
        else:
            if st.button(
                "✅ Activate",
                key=f"act_{u['id']}",
                use_container_width=True,
                disabled=is_self,
            ):
                _toggle_user_active(u, True, admin)
    with col4:
        if st.button(
            "🗑️ Delete User",
            key=f"delete_user_{u['id']}",
            use_container_width=True,
            disabled=is_self,
            help="Permanently delete this user. Will fail if they have order history — use Deactivate instead.",
        ):
            _delete_user(u, admin)

    # Close button
    if st.button("← Close Management Panel", key=f"close_{u['id']}", use_container_width=True):
        st.session_state.pop("managing_user", None)
        st.rerun()


def _approve_document(doc: dict, user: dict, admin: dict):
    try:
        client = get_supabase_admin_client()
        client.table("verification_documents").update({
            "status": "approved",
            "reviewed_by": admin["id"],
            "reviewed_at": "now()",
        }).eq("id", doc["id"]).execute()

        # Auto-verify the user when a doc is approved
        client.table("profiles").update({
            "verification_status": "verified",
            "verification_reviewed_at": "now()",
            "is_verified": True,
        }).eq("id", user["id"]).execute()

        # Notify user
        try:
            client.table("notifications").insert({
                "user_id": user["id"],
                "sender_id": admin["id"],
                "title": "✅ Document Approved!",
                "message": f"Your {doc.get('document_type', '').replace('_', ' ')} was approved. Your account is now verified!",
                "type": "success",
            }).execute()
        except Exception:
            pass

        # Log
        _log_admin_action(admin, "approve_document", "verification_documents", doc["id"], {"user_id": user["id"]})

        st.success("Document approved. User is now verified!")
        st.rerun()
    except Exception as e:
        st.error(f"Failed: {e}")


def _reject_document(doc: dict, user: dict, admin: dict):
    notes = st.text_input("Reason for rejection (optional)", key=f"reject_notes_{doc['id']}")
    if st.button("Confirm Reject", key=f"confirm_reject_{doc['id']}", type="primary"):
        try:
            client = get_supabase_admin_client()
            client.table("verification_documents").update({
                "status": "rejected",
                "reviewed_by": admin["id"],
                "reviewed_at": "now()",
                "review_notes": notes or None,
            }).eq("id", doc["id"]).execute()

            client.table("profiles").update({
                "verification_status": "rejected",
                "verification_reviewed_at": "now()",
                "verification_notes": notes or None,
            }).eq("id", user["id"]).execute()

            # Notify user
            try:
                client.table("notifications").insert({
                    "user_id": user["id"],
                    "sender_id": admin["id"],
                    "title": "❌ Document Rejected",
                    "message": f"Your {doc.get('document_type', '').replace('_', ' ')} was rejected. {notes or 'Please re-upload a clearer copy.'}",
                    "type": "warning",
                }).execute()
            except Exception:
                pass

            _log_admin_action(admin, "reject_document", "verification_documents", doc["id"], {"user_id": user["id"], "notes": notes})
            st.success("Document rejected. User notified.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed: {e}")


def _delete_document(doc: dict, admin: dict):
    try:
        client = get_supabase_admin_client()
        client.table("verification_documents").delete().eq("id", doc["id"]).execute()
        _log_admin_action(admin, "delete_document", "verification_documents", doc["id"])
        st.success("Document deleted.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed: {e}")


def _verify_user(u: dict, admin: dict):
    try:
        client = get_supabase_admin_client()
        client.table("profiles").update({
            "verification_status": "verified",
            "verification_reviewed_at": "now()",
            "is_verified": True,
        }).eq("id", u["id"]).execute()
        _log_admin_action(admin, "verify_user", "profiles", u["id"])
        st.success(f"{u.get('full_name')} is now verified!")
        st.rerun()
    except Exception as e:
        st.error(f"Failed: {e}")


def _reject_user(u: dict, admin: dict):
    try:
        client = get_supabase_admin_client()
        client.table("profiles").update({
            "verification_status": "rejected",
            "verification_reviewed_at": "now()",
            "is_verified": False,
        }).eq("id", u["id"]).execute()
        _log_admin_action(admin, "reject_user", "profiles", u["id"])
        st.warning(f"{u.get('full_name')}'s verification rejected.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed: {e}")


def _toggle_user_active(u: dict, active: bool, admin: dict):
    try:
        client = get_supabase_admin_client()
        client.table("profiles").update({"is_active": active}).eq("id", u["id"]).execute()
        _log_admin_action(admin, f"{'activate' if active else 'deactivate'}_user", "profiles", u["id"])
        st.success(f"User {'activated' if active else 'deactivated'}.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed: {e}")


def _delete_user(u: dict, admin: dict):
    st.warning(f"⚠️ This will permanently delete {u.get('full_name')} and all their data.")
    confirm = st.text_input("Type the user's email to confirm deletion", key=f"confirm_del_{u['id']}")
    if st.button("🗑️ Confirm Delete", key=f"confirm_delete_btn_{u['id']}", type="primary"):
        if confirm == u.get("email"):
            try:
                client = get_supabase_admin_client()
                # Delete the profile (cascade will handle related rows).
                # NOTE: orders.buyer_id and orders.seller_id are
                # ON DELETE RESTRICT, so this will fail with an FK violation
                # if the user has any orders. Deactivate instead via the
                # "Deactivate" button below for users with order history.
                client.table("profiles").delete().eq("id", u["id"]).execute()
                _log_admin_action(admin, "delete_user", "profiles", u["id"])
                st.success("User deleted permanently. (Their auth account is orphaned and can no longer log in.)")
                st.session_state.pop("managing_user", None)
                st.rerun()
            except Exception as e:
                err = str(e).lower()
                if "foreign key" in err or "violates" in err or "restrict" in err:
                    st.error(
                        "Cannot delete this user because they have orders or "
                        "agreements that reference them. Use the **Deactivate** "
                        "button instead — it sets is_active=false, which blocks "
                        "login while preserving the order history. Detail: " + str(e)
                    )
                else:
                    st.error(f"Failed: {e}")
        else:
            st.error("Email doesn't match. Deletion cancelled.")


# ---------------------------------------------------------------------------
# B) PRODUCT MANAGEMENT
# ---------------------------------------------------------------------------
def _render_product_management(admin: dict):
    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    try:
        products = (
            client.table("products")
            .select("*, profiles!products_producer_id_fkey(full_name, email)")
            .order("created_at", desc=True)
            .execute()
        ).data or []
    except Exception as e:
        st.error(f"Failed to load products: {e}")
        return

    # Summary card — same design as the dashboard's "Orders & Products"
    active = sum(1 for p in products if p.get("status") == "active")
    inactive = sum(1 for p in products if p.get("status") == "inactive")
    draft = sum(1 for p in products if p.get("status") == "draft")
    low_stock = sum(
        1 for p in products
        if int(p.get("stock", 0)) <= int(p.get("reorder_point", 0))
    )
    out_of_stock = sum(1 for p in products if int(p.get("stock", 0)) == 0)

    _card(
        icon="📦",
        title="Product Management",
        subtitle="View, search, and remove any product posted on the platform.",
        metrics_html=(
            _metric_box(str(len(products)), "Total Products", "📦")
            + _metric_box(str(active), "Active", "🟢")
            + _metric_box(str(inactive), "Inactive", "⚪", alert=inactive > 0)
            + _metric_box(str(draft), "Draft", "📝", alert=draft > 0)
            + _metric_box(str(low_stock), "Low Stock", "⚠️", alert=low_stock > 0)
            + _metric_box(str(out_of_stock), "Out of Stock", "❌", alert=out_of_stock > 0)
        ),
    )

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Search products", placeholder="Name, SKU, or producer...")
    with col2:
        categories = ["All"] + sorted({p.get("category", "Other") for p in products})
        category = st.selectbox("Category", categories)
    with col3:
        status_filter = st.selectbox("Status", ["All", "active", "inactive", "draft"])

    filtered = [
        p for p in products
        if (not search or search.lower() in p.get("name", "").lower() or search.lower() in p.get("sku", "").lower())
        and (category == "All" or p.get("category") == category)
        and (status_filter == "All" or p.get("status") == status_filter)
    ]

    st.markdown(f"###### {len(filtered)} product(s)")

    for p in filtered:
        _render_product_admin_card(p, admin)


def _render_product_admin_card(p: dict, admin: dict):
    """Render a product row in the admin Product Management list.

    Visual design: matches the user card style — modern card with
    image, name, badges, key stats, and a Manage button. Hover effect
    on the card.
    """
    producer = p.get("profiles") or {}
    status = p.get("status", "active")
    stock = int(p.get("stock", 0) or 0)
    reorder = int(p.get("reorder_point", 0) or 0)
    is_low_stock = stock <= reorder
    is_out_of_stock = stock == 0
    is_active = status == "active"

    # Status pill colors
    status_colors = {
        "active":   ("#dcfce7", "#166534", "🟢"),
        "inactive": ("#fee2e2", "#991b1b", "⚪"),
        "draft":    ("#fef3c7", "#92400e", "📝"),
    }
    s_bg, s_fg, s_emoji = status_colors.get(status, ("#f1f5f9", "#475569", "❓"))

    # Image / placeholder
    image_url = p.get("image_url")
    if image_url:
        img_html = (
            f"<img src='{image_url}' "
            f"style='width:72px; height:72px; border-radius:10px; object-fit:cover; "
            f"border:1px solid #e4ece6; box-shadow:0 2px 6px rgba(0,0,0,0.08);' />"
        )
    else:
        img_html = (
            "<div style='width:72px; height:72px; border-radius:10px; "
            "background:linear-gradient(135deg,#f1f5f9 0%,#e2e8f0 100%); "
            "display:flex; align-items:center; justify-content:center; "
            "font-size:2rem; color:#94a3b8; border:1px solid #e4ece6;'>📦</div>"
        )

    # Stock alert pill
    if is_out_of_stock:
        stock_pill = ("#fee2e2", "#991b1b", "❌ Out of stock")
    elif is_low_stock:
        stock_pill = ("#fef3c7", "#92400e", f"⚠️ Low stock ({stock})")
    else:
        stock_pill = ("#dcfce7", "#166534", f"✅ {stock} in stock")

    sp_bg, sp_fg, sp_text = stock_pill

    st.markdown(
        f"""
        <div class="um-user-card">
          <div class="um-user-card-left">
            {img_html}
            <div class="um-user-info">
              <div class="um-user-name">{p.get('name', '—')}</div>
              <div class="um-user-email">SKU: <code>{p.get('sku', '—')}</code> · by {producer.get('full_name', 'Unknown')}</div>
              <div class="um-user-badges">
                <span class="um-pill" style="background:{s_bg}; color:{s_fg};">{s_emoji} {status.title()}</span>
                <span class="um-pill" style="background:{sp_bg}; color:{sp_fg};">{sp_text}</span>
                {f'<span class="um-pill" style="background:#ede9fe; color:#5b21b6;">🏷️ {p.get("category", "—")}</span>' if p.get("category") else ''}
                {f'<span class="um-pill" style="background:#fef3c7; color:#92400e;">⭐ {p["quality_grade"]}</span>' if p.get("quality_grade") else ''}
              </div>
            </div>
          </div>
          <div class="um-user-card-right">
            <div class="um-user-verif" style="color:#047857;">
              💰 <strong>{format_currency(p.get('price'))}</strong>
            </div>
            <div class="um-user-meta">
              📦 Stock: <strong>{stock}</strong> &nbsp;·&nbsp; 🔄 Reorder at: {reorder}
            </div>
            <div class="um-user-meta">
              🗓️ Listed: {format_datetime(p.get('created_at'), '%Y-%m-%d') if p.get('created_at') else '—'}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Manage button
    col_a, _, _ = st.columns([1, 1, 4])
    with col_a:
        label = "📋 Manage" if st.session_state.get("managing_product") != p["id"] else "✕ Close"
        btn_type = "secondary" if st.session_state.get("managing_product") != p["id"] else "primary"
        if st.button(label, key=f"admin_prod_{p['id']}", use_container_width=True, type=btn_type):
            if st.session_state.get("managing_product") == p["id"]:
                st.session_state.pop("managing_product", None)
            else:
                st.session_state["managing_product"] = p["id"]
            st.rerun()

    if st.session_state.get("managing_product") == p["id"]:
        _render_product_admin_panel(p, admin)


def _render_product_admin_panel(p: dict, admin: dict):
    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    # ---- Beautiful product details (no raw JSON) ----
    st.markdown("#### Product Details")

    detail_cols = st.columns([1, 1])
    with detail_cols[0]:
        st.markdown(f"**🆔 Product ID:**")
        st.code(p.get("id", "—"), language="text")
        st.markdown(f"**📦 Name:** {p.get('name', '—')}")
        st.markdown(f"**🏷️ SKU:** `{p.get('sku', '—')}`")
        st.markdown(f"**🗂️ Category:** {p.get('category', '—')}")
        st.markdown(f"**💰 Price:** {format_currency(p.get('price'))} / {p.get('unit', 'unit')}")
        st.markdown(f"**📊 Stock:** {p.get('stock', 0)} {p.get('unit', 'units')}")
        st.markdown(f"**🔄 Reorder at:** {p.get('reorder_point', 0)}")
    with detail_cols[1]:
        st.markdown(f"**⭐ Quality Grade:** {p.get('quality_grade') or '—'}")
        st.markdown(f"**🏢 Brand:** {p.get('brand') or '—'}")
        st.markdown(f"**🔖 Model:** {p.get('model') or '—'}")
        st.markdown(f"**📍 Origin:** {p.get('origin') or '—'}")
        certs = p.get('certifications') or []
        st.markdown(f"**🏅 Certifications:** {', '.join(certs) if certs else '—'}")
        status = p.get('status', 'active')
        status_colors = {
            "active":   ("#dcfce7", "#166534", "🟢"),
            "inactive": ("#fee2e2", "#991b1b", "⚪"),
            "draft":    ("#fef3c7", "#92400e", "📝"),
        }
        s_bg, s_fg, s_emoji = status_colors.get(status, ("#f1f5f9", "#475569", "❓"))
        st.markdown(
            f"**📌 Status:** <span class='um-pill' style='background:{s_bg}; color:{s_fg};'>{s_emoji} {status.title()}</span>",
            unsafe_allow_html=True,
        )
        if p.get('description'):
            st.markdown(f"**📝 Description:**")
            st.caption(p['description'])

    # ---- Activate (only if not active) ----
    if p.get("status") != "active":
        st.markdown("---")
        st.markdown("#### ⚙️ Actions")
        if st.button("✅ Activate Product", key=f"act_prod_{p['id']}", use_container_width=True, type="primary"):
            client.table("products").update({"status": "active"}).eq("id", p["id"]).execute()
            _log_admin_action(admin, "activate_product", "products", p["id"])
            st.success("Product activated.")
            st.rerun()

    # ---- Mark Inactive (with reason) ----
    st.markdown("---")
    st.markdown("#### 🚫 Mark Inactive")
    st.caption(
        "Inactive products are hidden from the marketplace but the data is preserved. "
        "Add a reason below so the producer knows why their product was taken down."
    )
    inactive_reason = st.text_area(
        "Reason (visible to the producer in their notification)",
        placeholder="e.g. Stock level too low, missing certifications, image quality issues...",
        key=f"inact_reason_{p['id']}",
        height=80,
    )
    notify_on_inactive = st.checkbox(
        "📨 Notify the producer",
        value=True,
        key=f"inact_notify_{p['id']}",
        help="Send a notification to the producer with the reason above.",
    )
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🚫 Confirm Mark Inactive", key=f"inact_prod_{p['id']}", use_container_width=True, type="primary"):
            try:
                client.table("products").update({"status": "inactive"}).eq("id", p["id"]).execute()
                _log_admin_action(
                    admin, "deactivate_product", "products", p["id"],
                    {"reason": inactive_reason, "notified": notify_on_inactive},
                )
                if notify_on_inactive:
                    try:
                        producer_id = p.get("producer_id")
                        if producer_id:
                            msg = f"Your product '{p.get('name', 'Unknown')}' (SKU: {p.get('sku', '—')}) was marked inactive by an admin."
                            if inactive_reason:
                                msg += f"\n\nReason: {inactive_reason}"
                            client.table("notifications").insert({
                                "user_id": producer_id,
                                "sender_id": admin["id"],
                                "title": "🚫 Product Marked Inactive",
                                "message": msg,
                                "type": "warning",
                            }).execute()
                    except Exception:
                        pass
                st.success("Product marked inactive.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")
    with col2:
        if st.button("← Close", key=f"close_inact_{p['id']}", use_container_width=True):
            st.session_state.pop("managing_product", None)
            st.rerun()

    # ---- Delete Product (with reason) ----
    st.markdown("---")
    st.markdown("#### 🗑️ Delete Product")
    st.warning(
        "⚠️ **This is permanent.** The product and all its data will be erased. "
        "If this product has orders, the delete will fail — use **Mark Inactive** instead."
    )
    delete_reason = st.text_area(
        "Reason for deletion (logged for audit trail)",
        placeholder="e.g. Duplicate listing, violates content policy, spam...",
        key=f"del_reason_{p['id']}",
        height=80,
    )
    confirm_delete = st.text_input(
        "Type the SKU to confirm deletion",
        key=f"del_confirm_{p['id']}",
        placeholder=f"Type '{p.get('sku', '')}' to confirm",
    )
    if st.button("🗑️ Delete Product Permanently", key=f"del_prod_{p['id']}", use_container_width=True, type="primary"):
        if confirm_delete != p.get("sku"):
            st.error("SKU doesn't match. Deletion cancelled.")
        else:
            try:
                client.table("products").delete().eq("id", p["id"]).execute()
                _log_admin_action(
                    admin, "delete_product", "products", p["id"],
                    {"reason": delete_reason, "sku_confirmed": True},
                )
                st.success("Product deleted permanently.")
                st.session_state.pop("managing_product", None)
                st.rerun()
            except Exception as e:
                err = str(e).lower()
                if "foreign key" in err or "violates" in err or "restrict" in err:
                    st.error(
                        "Cannot delete this product because it is referenced by "
                        "existing orders. Use **Mark Inactive** instead to hide it "
                        f"from the marketplace. Detail: {e}"
                    )
                else:
                    st.error(f"Delete failed: {e}")


# ---------------------------------------------------------------------------
# C) DATABASE MANAGEMENT
# ---------------------------------------------------------------------------
MANAGED_TABLES = [
    "profiles", "products", "orders", "order_items", "agreements",
    "fraud_logs", "favorites", "cart_items", "ai_predictions",
    "notifications", "messages", "user_preferences", "merchant_requests",
    "verification_documents", "admin_activity_logs",
]

# Tables where direct edit/add is safe. Others are read-only.
EDITABLE_TABLES = [
    "profiles", "products", "agreements", "fraud_logs", "ai_predictions",
    "notifications", "messages", "user_preferences", "merchant_requests",
    "verification_documents",
]

# Columns to hide from the table view (for readability)
HIDDEN_COLUMNS = {"metadata", "input_features", "transaction_data", "risk_factors", "shipping_address"}


def _render_database_management(admin: dict):
    st.warning("⚠️ **Warning:** Direct database edits can break the app. Only modify data if you know what you're doing.")

    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    # Table selector
    col1, col2 = st.columns([2, 1])
    with col1:
        table = st.selectbox(
            "Select a table",
            MANAGED_TABLES,
            help="Pick which table you want to view or edit.",
        )
    with col2:
        limit = st.number_input("Rows to show", min_value=10, max_value=500, value=50, step=10)

    if not table:
        return

    # Check if table exists
    if not is_table_available(table):
        st.error(f"❌ The `{table}` table doesn't exist in your database.")
        return

    # Fetch rows
    try:
        response = client.table(table).select("*").limit(limit).order("created_at", desc=True).execute()
        rows = response.data or []
    except Exception:
        # Some tables don't have created_at; try without ordering
        try:
            response = client.table(table).select("*").limit(limit).execute()
            rows = response.data or []
        except Exception as e:
            st.error(f"Failed to load {table}: {e}")
            return

    # Summary card — same design as the dashboard's "Orders & Products"
    is_editable = table in EDITABLE_TABLES
    _card(
        icon="🗄️",
        title="Database Management",
        subtitle="View, edit, add, and delete rows in any database table. Use with caution!",
        metrics_html=(
            _metric_box(str(len(rows)), f"Rows in `{table}`", "📋")
            + _metric_box(
                str(len(MANAGED_TABLES)),
                "Tables Available",
                "🗂️",
            )
            + _metric_box(
                "Yes" if is_editable else "No",
                "Editable",
                "✏️" if is_editable else "🔒",
                alert=not is_editable,
            )
            + _metric_box(str(limit), "Row Limit", "📏")
        ),
    )

    if not rows:
        st.info(f"No rows in `{table}`.")
        return

    # Convert to DataFrame for display
    df = pd.DataFrame(rows)
    # Hide bulky JSON columns for readability
    display_cols = [c for c in df.columns if c not in HIDDEN_COLUMNS]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

    if not is_editable:
        st.info("This table is read-only for safety. Use the dedicated management pages (User Management, Product Management) to modify it.")
        return

    # ---- Edit / Delete existing rows ----
    st.markdown("#### ✏️ Edit or Delete a Row")
    row_ids = [str(r.get("id", i)) for i, r in enumerate(rows)]

    def _format_row(i: int) -> str:
        """Build a human-readable label for a row in the dropdown."""
        r = rows[i]
        rid = str(r.get("id", "?"))[:8]

        if table == "profiles":
            email = r.get("email", "—")
            name = r.get("full_name") or "—"
            role = r.get("role", "—")
            return f"👤 {name} · {email} · {role} · {rid}…"
        if table == "products":
            return f"📦 {r.get('name', '—')} · {r.get('sku', '—')} · {format_currency(r.get('price', 0))} · {rid}…"
        if table == "orders":
            return f"🛒 {r.get('order_number', '—')} · {r.get('status', '—')} · {format_currency(r.get('total', 0))} · {rid}…"
        if table == "agreements":
            return f"📄 {r.get('agreement_code', '—')} · {r.get('title', '—')[:40]} · {rid}…"
        if table == "notifications":
            return f"🔔 {r.get('title', '—')[:50]} · {r.get('type', '—')} · {rid}…"
        if table == "verification_documents":
            return f"📄 {r.get('document_type', '—')} · {r.get('status', '—')} · {rid}…"
        # Default fallback
        return f"Row {i+1}: {rid}…"

    col_sel, col_action = st.columns([3, 1])
    with col_sel:
        selected_row_idx = st.selectbox(
            "📋 Select a row to edit/delete",
            range(len(rows)),
            format_func=_format_row,
            key=f"row_select_{table}",
        )
    with col_action:
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("🔄 Refresh list", key=f"refresh_rows_{table}", use_container_width=True):
            st.rerun()

    if selected_row_idx is not None:
        selected_row = rows[selected_row_idx]
        _render_row_editor(table, selected_row, admin)

    # ---- Add new row ----
    st.markdown("#### ➕ Add New Row")
    with st.expander("Add a new row to " + table, expanded=False):
        _render_row_adder(table, rows[0] if rows else {}, admin)


# ---- Field metadata for the row editor ----
# Maps (table, column) -> input widget type and options. Falls back to
# a text input for unknown fields.
_FIELD_WIDGETS = {
    # Profiles table — use dropdowns for enum-like fields
    ("profiles", "role"): {
        "type": "select",
        "options": ["customer", "merchant", "producer", "admin"],
    },
    ("profiles", "is_active"): {"type": "bool"},
    ("profiles", "is_verified"): {"type": "bool"},
    ("profiles", "verification_status"): {
        "type": "select",
        "options": ["pending", "verified", "rejected"],
    },
    # Products table
    ("products", "status"): {
        "type": "select",
        "options": ["active", "inactive", "draft"],
    },
    # Orders
    ("orders", "status"): {
        "type": "select",
        "options": ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"],
    },
    ("orders", "payment_status"): {
        "type": "select",
        "options": ["pending", "paid", "failed", "refunded"],
    },
    # Notifications
    ("notifications", "type"): {
        "type": "select",
        "options": ["info", "success", "warning", "error"],
    },
    ("notifications", "is_read"): {"type": "bool"},
    # Verification docs
    ("verification_documents", "status"): {
        "type": "select",
        "options": ["pending", "approved", "rejected"],
    },
    # Agreements
    ("agreements", "status"): {
        "type": "select",
        "options": ["draft", "pending", "active", "completed", "cancelled"],
    },
    # Fraud logs
    ("fraud_logs", "status"): {
        "type": "select",
        "options": ["pending", "investigating", "resolved", "dismissed"],
    },
    ("fraud_logs", "severity"): {
        "type": "select",
        "options": ["low", "medium", "high", "critical"],
    },
    # AI predictions
    ("ai_predictions", "model_version"): {"type": "text"},
}


def _render_row_editor(table: str, row: dict, admin: dict):
    """Render an editor for a single row.

    Uses dropdowns (selectbox) for known enum-like fields, checkboxes
    for booleans, and the right input type for dates / numbers / text.
    For the profiles table, also adds a password reset field that uses
    the Supabase Auth admin API to change the user's password.
    """
    with st.form(f"edit_row_{table}_{row.get('id', 'new')}"):
        st.markdown(f"**Editing row** `{row.get('id', '?')}`")
        edited_values = {}
        for col, val in row.items():
            if col in ("id", "created_at", "updated_at"):
                st.text_input(f"{col} (locked)", value=str(val) if val else "", disabled=True, key=f"edit_{col}")
                continue
            widget = _FIELD_WIDGETS.get((table, col))
            if widget is None:
                # Auto-detect from the column name
                if col.startswith("is_") or col.startswith("has_") or col.endswith("_active") or col.endswith("_verified"):
                    widget = {"type": "bool"}
                elif col == "role":
                    widget = {"type": "select", "options": ["customer", "merchant", "producer", "admin"]}
                elif col == "status" or col.endswith("_status"):
                    widget = {"type": "select", "options": ["pending", "active", "inactive", "completed", "cancelled", "rejected", "approved", "draft"]}
                elif col.endswith("_at"):
                    widget = {"type": "datetime"}
                elif col.endswith("_date"):
                    widget = {"type": "date"}
                elif isinstance(val, bool):
                    widget = {"type": "bool"}
                elif isinstance(val, (int, float)) and not isinstance(val, bool):
                    widget = {"type": "number"}
                elif val is None or isinstance(val, str):
                    widget = {"type": "text"}
                else:
                    widget = {"type": "text"}

            # Render the widget based on the type
            if widget["type"] == "select":
                options = widget["options"]
                if val is not None and val not in options:
                    options = [val] + list(options)  # preserve the current value
                default_idx = options.index(val) if val in options else 0
                edited_values[col] = st.selectbox(
                    col, options=options, index=default_idx, key=f"edit_{col}",
                )
            elif widget["type"] == "bool":
                edited_values[col] = st.checkbox(col, value=bool(val), key=f"edit_{col}")
            elif widget["type"] == "number":
                if isinstance(val, float) or (val is not None and "." in str(val)):
                    edited_values[col] = st.number_input(col, value=float(val or 0.0), key=f"edit_{col}")
                else:
                    edited_values[col] = st.number_input(col, value=int(val or 0), key=f"edit_{col}")
            elif widget["type"] == "date":
                from datetime import date as _date
                if val:
                    try:
                        d = _date.fromisoformat(str(val)[:10])
                        edited_values[col] = st.date_input(col, value=d, key=f"edit_{col}")
                    except Exception:
                        edited_values[col] = st.text_input(col, value=str(val) or "", key=f"edit_{col}")
                else:
                    edited_values[col] = st.date_input(col, value=None, key=f"edit_{col}")
            elif widget["type"] == "datetime":
                if val:
                    edited_values[col] = st.text_input(
                        f"{col} (ISO timestamp)",
                        value=str(val),
                        key=f"edit_{col}",
                        help="Format: 2026-07-16T14:30:00+00:00",
                    )
                else:
                    edited_values[col] = st.text_input(col, value="", key=f"edit_{col}")
            else:
                # text
                if val is None:
                    edited_values[col] = st.text_input(f"{col} (null)", value="", key=f"edit_{col}") or None
                else:
                    if len(str(val)) > 80:
                        edited_values[col] = st.text_area(col, value=str(val), height=60, key=f"edit_{col}")
                    else:
                        edited_values[col] = st.text_input(col, value=str(val), key=f"edit_{col}")

        # ---- PASSWORD RESET (profiles table only) ----
        new_password = None
        if table == "profiles":
            st.markdown("---")
            st.markdown("##### 🔐 Change Password")
            st.caption(
                "Optional. Leave blank to keep the current password. "
                "Min 8 characters. The change uses the Supabase Auth admin API."
            )
            new_password = st.text_input(
                "New password (leave blank to keep current)",
                type="password",
                key=f"edit_password_{row.get('id')}",
                placeholder="Min 8 characters",
            )

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 Save Changes", type="primary")
        with col2:
            deleted = st.form_submit_button("🗑️ Delete Row")

        if submitted:
            try:
                client = get_supabase_admin_client()
                # Filter out locked columns
                update_payload = {k: v for k, v in edited_values.items() if k not in ("id", "created_at", "updated_at")}
                # Convert date / datetime fields to strings
                from datetime import date as _date, datetime as _datetime
                for k, v in list(update_payload.items()):
                    if isinstance(v, _date):
                        update_payload[k] = v.isoformat()
                    elif isinstance(v, _datetime):
                        update_payload[k] = v.isoformat()
                client.table(table).update(update_payload).eq("id", row["id"]).execute()
                _log_admin_action(admin, "edit_row", table, str(row.get("id")), {"changes": list(update_payload.keys())})
                profile_updated = True
            except Exception as e:
                st.error(f"Update failed: {e}")
                profile_updated = False

            # ---- Password reset (profiles only) ----
            if profile_updated and table == "profiles" and new_password:
                if len(new_password) < 8:
                    st.warning("Password must be at least 8 characters — not changed.")
                else:
                    try:
                        admin_client = get_supabase_admin_client()
                        # Supabase-py exposes update_user_by_id on the admin client
                        admin_client.auth.admin.update_user_by_id(
                            row["id"],
                            {"password": new_password},
                        )
                        _log_admin_action(
                            admin, "reset_password", "auth.users", str(row.get("id")),
                            {"by_admin": admin.get("id")},
                        )
                        st.success("✅ Profile saved and password updated.")
                    except Exception as pw_err:
                        st.error(f"Profile saved, but password change failed: {pw_err}")
            elif profile_updated:
                st.success("Row updated!")
            if profile_updated:
                st.rerun()

        if deleted:
            try:
                client = get_supabase_admin_client()
                client.table(table).delete().eq("id", row["id"]).execute()
                _log_admin_action(admin, "delete_row", table, str(row.get("id")))
                st.success("Row deleted!")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")


def _render_row_adder(table: str, sample_row: dict, admin: dict):
    """Render a form to add a new row."""
    with st.form(f"add_row_{table}"):
        st.markdown("Fill in the values for the new row. Leave blank for null/auto-generated.")
        new_values = {}
        for col in sample_row.keys():
            if col in ("id", "created_at", "updated_at"):
                continue
            new_values[col] = st.text_input(col, value="", key=f"add_{col}")

        submitted = st.form_submit_button("➕ Add Row", type="primary")
        if submitted:
            try:
                client = get_supabase_admin_client()
                # Filter out empty strings
                payload = {k: v for k, v in new_values.items() if v.strip()}
                client.table(table).insert(payload).execute()
                _log_admin_action(admin, "add_row", table, None, {"payload": payload})
                st.success("Row added!")
                st.rerun()
            except Exception as e:
                st.error(f"Insert failed: {e}")


# ---------------------------------------------------------------------------
# Helper: log admin actions
# ---------------------------------------------------------------------------
def _log_admin_action(admin: dict, action: str, target_table: str, target_id: str = None, details: dict = None):
    """Log an admin action to the audit trail."""
    try:
        client = get_supabase_admin_client()
        client.table("admin_activity_logs").insert({
            "admin_id": admin["id"],
            "action": action,
            "target_table": target_table,
            "target_id": str(target_id) if target_id else None,
            "details": details or {},
        }).execute()
    except Exception:
        pass  # Logging is best-effort
