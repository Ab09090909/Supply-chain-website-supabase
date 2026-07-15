"""
Admin Management page — comprehensive admin control center.

Three sub-tabs:
  A) 👥 User Management  — verify users, view uploaded documents, activate/deactivate, delete
  B) 📦 Product Management — view/remove/delete any posted product
  C) 🗄️ Database Management — view/edit/add/delete rows in any table
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime

from auth.session import get_current_user
from database.connection import get_supabase_admin_client, get_supabase_client
from utils.ui import page_header, role_badge
from utils.helpers import format_currency, format_datetime
from utils.db_health import is_table_available


def render_admin_management():
    page_header("⚙️ Management", "Comprehensive admin control center")

    user = get_current_user()
    if not user:
        return

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
    st.markdown("### 👥 User Management")
    st.caption("Verify users, view their documents, activate/deactivate, or delete accounts.")

    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    try:
        users = client.table("profiles").select("*").order("created_at", desc=True).execute().data or []
    except Exception as e:
        st.error(f"Failed to load users: {e}")
        return

    # Summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Users", len(users))
    with col2:
        pending_verification = sum(1 for u in users if u.get("verification_status") == "pending")
        st.metric("⏳ Pending Verification", pending_verification)
    with col3:
        verified = sum(1 for u in users if u.get("verification_status") == "verified")
        st.metric("✅ Verified", verified)
    with col4:
        active = sum(1 for u in users if u.get("is_active"))
        st.metric("🟢 Active", active)

    st.markdown("---")

    # Filter
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
    """Render a single user card with verification + management actions."""
    is_self = u["id"] == admin["id"]
    verif_status = u.get("verification_status", "pending")
    verif_color = {"verified": "#10b981", "pending": "#f59e0b", "rejected": "#ef4444"}.get(verif_status, "#64748b")
    verif_emoji = {"verified": "✅", "pending": "⏳", "rejected": "❌"}.get(verif_status, "❓")

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        with col1:
            avatar_url = u.get("avatar_url")
            if avatar_url:
                st.markdown(
                    f"<div style='display:flex; align-items:center; gap:0.75rem;'>"
                    f"<img src='{avatar_url}' style='width:40px; height:40px; border-radius:50%; object-fit:cover;' />"
                    f"<div><strong>{u.get('full_name', '—')}</strong><br/>"
                    f"<span style='color:#64748b; font-size:0.85rem;'>{u.get('email', '')}</span></div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**{u.get('full_name', '—')}**")
                st.caption(u.get("email", ""))
            st.markdown(role_badge(u.get("role", "")), unsafe_allow_html=True)
        with col2:
            st.markdown(f"**Verification:** <span style='color:{verif_color};'>{verif_emoji} {verif_status.title()}</span>", unsafe_allow_html=True)
            st.caption(f"📞 {u.get('phone', '—')} · 📍 {u.get('location', '—')}")
            st.caption(f"Joined: {format_datetime(u.get('created_at'), '%Y-%m-%d')}")
        with col3:
            st.metric("Active", "✅" if u.get("is_active") else "❌")
        with col4:
            if is_self:
                st.caption("(You)")
            else:
                if st.button("Manage", key=f"manage_{u['id']}", use_container_width=True):
                    st.session_state["managing_user"] = u["id"]
                    st.rerun()

        # Expandable management panel
        if st.session_state.get("managing_user") == u["id"]:
            with st.expander(f"📋 Manage {u.get('full_name', 'User')}", expanded=True):
                _render_user_management_panel(u, admin)


def _render_user_management_panel(u: dict, admin: dict):
    """Detailed management panel for a single user."""
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
            col1, col2, col3 = st.columns([2, 1, 2])
            with col1:
                doc_type = doc.get("document_type", "unknown").replace("_", " ").title()
                st.markdown(f"**{doc_type}**")
                st.caption(f"File: {doc.get('document_name', '—')}")
                if doc.get("document_number"):
                    st.caption(f"Number: `{doc['document_number']}`")
                st.caption(f"Uploaded: {format_datetime(doc.get('uploaded_at'))}")
            with col2:
                doc_status = doc.get("status", "pending")
                st.markdown(f"**Status:** {doc_status.title()}")
            with col3:
                # Preview the document. The file_url is the *path* inside
                # the verification-docs bucket (a PRIVATE bucket), so the
                # public URL we stored at upload time is a 404. We need a
                # signed URL for the preview to actually work.
                file_url = doc.get("file_url")
                if not file_url:
                    st.caption("No file URL")
                else:
                    # file_url is a public-storage URL like
                    # "https://xxx.supabase.co/storage/v1/object/public/verification-docs/{user}/{uuid}.jpg"
                    # Extract the path inside the bucket (everything after /verification-docs/)
                    preview_url = None
                    try:
                        marker = "/verification-docs/"
                        idx = file_url.find(marker)
                        if idx >= 0:
                            bucket_path = file_url[idx + len(marker):]
                            # Use the admin client to create a signed URL.
                            try:
                                admin_storage = get_supabase_admin_client().storage
                                preview_url = admin_storage.from_("verification-docs").create_signed_url(
                                    bucket_path, expires_in=300
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass
                    if not preview_url:
                        # Fall back to the stored public URL (will 404 on
                        # private buckets but at least gives a clickable link).
                        preview_url = file_url
                    if doc.get("mime_type", "").startswith("image/"):
                        try:
                            st.image(preview_url, caption="Document preview", width=200)
                        except Exception:
                            st.markdown(f"📄 [View document]({preview_url})")
                    else:
                        st.markdown(f"📄 [View document]({preview_url})")

            # Approve / Reject buttons for the document
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
            st.markdown("---")
    else:
        st.info("No verification documents uploaded.")

    # ---- User actions ----
    st.markdown("#### ⚙️ User Actions")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("✅ Verify User", key=f"verify_user_{u['id']}", use_container_width=True, type="primary"):
            _verify_user(u, admin)
    with col2:
        if st.button("❌ Reject Verification", key=f"reject_user_{u['id']}", use_container_width=True):
            _reject_user(u, admin)
    with col3:
        if u.get("is_active"):
            if st.button("🚫 Deactivate", key=f"deact_{u['id']}", use_container_width=True):
                _toggle_user_active(u, False, admin)
        else:
            if st.button("✅ Activate", key=f"act_{u['id']}", use_container_width=True):
                _toggle_user_active(u, True, admin)
    with col4:
        if st.button("🗑️ Delete User", key=f"delete_user_{u['id']}", use_container_width=True):
            _delete_user(u, admin)

    # Close button
    if st.button("← Close Management Panel", key=f"close_{u['id']}"):
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
    st.markdown("### 📦 Product Management")
    st.caption("View, search, and remove any product posted on the platform.")

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

    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Products", len(products))
    with col2:
        active = sum(1 for p in products if p.get("status") == "active")
        st.metric("🟢 Active", active)
    with col3:
        low_stock = sum(1 for p in products if int(p.get("stock", 0)) <= int(p.get("reorder_point", 0)))
        st.metric("⚠️ Low Stock", low_stock)

    st.markdown("---")

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
    producer = p.get("profiles") or {}
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([1, 3, 1, 1, 1])
        with col1:
            if p.get("image_url"):
                try:
                    st.image(p["image_url"], width=70)
                except Exception:
                    st.markdown("📦")
            else:
                st.markdown("📦")
        with col2:
            st.markdown(f"**{p['name']}**  `{p['sku']}`")
            st.caption(f"by {producer.get('full_name', '—')} · 🏷️ {p.get('category', '—')}")
            if p.get("quality_grade") or p.get("brand"):
                meta = []
                if p.get("quality_grade"): meta.append(f"⭐ {p['quality_grade']}")
                if p.get("brand"): meta.append(f"🏷️ {p['brand']}")
                st.caption(" · ".join(meta))
        with col3:
            st.metric("Price", format_currency(p.get("price")))
        with col4:
            st.metric("Stock", p.get("stock", 0))
        with col5:
            status = p.get("status", "active")
            st.metric("Status", status.title())
            if st.button("Manage", key=f"admin_prod_{p['id']}", use_container_width=True):
                st.session_state["managing_product"] = p["id"]
                st.rerun()

    if st.session_state.get("managing_product") == p["id"]:
        with st.expander(f"📋 Manage {p['name']}", expanded=True):
            _render_product_admin_panel(p, admin)


def _render_product_admin_panel(p: dict, admin: dict):
    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    # Show full details
    st.markdown("#### Product Details")
    st.json({
        "id": p["id"],
        "sku": p.get("sku"),
        "name": p.get("name"),
        "description": p.get("description"),
        "category": p.get("category"),
        "price": p.get("price"),
        "stock": p.get("stock"),
        "unit": p.get("unit"),
        "quality_grade": p.get("quality_grade"),
        "brand": p.get("brand"),
        "model": p.get("model"),
        "origin": p.get("origin"),
        "certifications": p.get("certifications"),
        "status": p.get("status"),
    })

    # Actions
    st.markdown("#### Actions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if p.get("status") != "active":
            if st.button("✅ Activate", key=f"act_prod_{p['id']}", use_container_width=True):
                client.table("products").update({"status": "active"}).eq("id", p["id"]).execute()
                _log_admin_action(admin, "activate_product", "products", p["id"])
                st.success("Product activated.")
                st.rerun()
    with col2:
        if st.button("🚫 Mark Inactive", key=f"inact_prod_{p['id']}", use_container_width=True):
            client.table("products").update({"status": "inactive"}).eq("id", p["id"]).execute()
            _log_admin_action(admin, "deactivate_product", "products", p["id"])
            st.success("Product marked inactive.")
            st.rerun()
    with col3:
        if st.button("🗑️ Delete Product", key=f"del_prod_{p['id']}", use_container_width=True, type="primary"):
            client.table("products").delete().eq("id", p["id"]).execute()
            _log_admin_action(admin, "delete_product", "products", p["id"])
            st.success("Product deleted.")
            st.session_state.pop("managing_product", None)
            st.rerun()
    with col4:
        if st.button("← Close", key=f"close_prod_{p['id']}", use_container_width=True):
            st.session_state.pop("managing_product", None)
            st.rerun()


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
    st.markdown("### 🗄️ Database Management")
    st.caption("View, edit, add, and delete rows in any database table. Use with caution!")

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

    # Summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Rows in view", len(rows))
    with col2:
        is_editable = table in EDITABLE_TABLES
        st.metric("Editable", "✅ Yes" if is_editable else "❌ Read-only")

    st.markdown("---")

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
    selected_row_idx = st.selectbox(
        "Select a row to edit/delete",
        range(len(rows)),
        format_func=lambda i: f"Row {i+1}: {rows[i].get('id', '?')[:8]}...",
    )

    if selected_row_idx is not None:
        selected_row = rows[selected_row_idx]
        _render_row_editor(table, selected_row, admin)

    # ---- Add new row ----
    st.markdown("#### ➕ Add New Row")
    with st.expander("Add a new row to " + table, expanded=False):
        _render_row_adder(table, rows[0] if rows else {}, admin)


def _render_row_editor(table: str, row: dict, admin: dict):
    """Render an editor for a single row."""
    with st.form(f"edit_row_{table}_{row.get('id', 'new')}"):
        st.markdown(f"**Editing row** `{row.get('id', '?')}`")
        edited_values = {}
        for col, val in row.items():
            if col in ("id", "created_at", "updated_at"):
                st.text_input(f"{col} (locked)", value=str(val) if val else "", disabled=True, key=f"edit_{col}")
                continue
            # Render appropriate input based on type
            if isinstance(val, bool):
                edited_values[col] = st.checkbox(col, value=val, key=f"edit_{col}")
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                edited_values[col] = st.number_input(col, value=val, key=f"edit_{col}")
            elif val is None:
                edited_values[col] = st.text_input(f"{col} (null)", value="", key=f"edit_{col}") or None
            else:
                edited_values[col] = st.text_area(col, value=str(val), height=60, key=f"edit_{col}")

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
                client.table(table).update(update_payload).eq("id", row["id"]).execute()
                _log_admin_action(admin, "edit_row", table, str(row.get("id")), {"changes": update_payload})
                st.success("Row updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Update failed: {e}")

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
