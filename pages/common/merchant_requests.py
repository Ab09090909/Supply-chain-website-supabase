"""
Merchant Requests page — merchants view incoming match requests from producers.

Merchant can:
  • Preview the proposed agreement
  • Confirm the agreement (sets status to 'confirmed')
  • Cancel the request (sets status to 'cancelled')
"""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header, role_badge
from utils.helpers import format_currency, format_datetime
from utils.db_health import is_table_available, render_db_health_warning


def render_merchant_requests():
    page_header("📨 Merchant Requests", "Review supply agreement requests from producers")

    user = get_current_user()
    if not user:
        return

    # Check if the merchant_requests table exists
    if not is_table_available("merchant_requests"):
        st.error("❌ The `merchant_requests` table doesn't exist yet.")
        st.info(
            "**To fix this:** Run `supabase/migration_v4.sql` in your Supabase SQL Editor.\n\n"
            "Go to: **Supabase Dashboard → SQL Editor → New Query** → "
            "paste the contents of `supabase/migration_v4.sql` → click **Run**."
        )
        render_db_health_warning()
        return

    try:
        client = get_supabase_client()
        requests = (
            client.table("merchant_requests")
            .select("*, profiles!merchant_requests_producer_id_fkey(full_name, email, company, location, phone, avatar_url, is_verified)")
            .eq("merchant_id", user["id"])
            .order("created_at", desc=True)
            .execute()
        ).data or []
    except Exception as e:
        err = str(e)
        if "PGRST205" in err or "could not find" in err.lower():
            st.error("❌ The `merchant_requests` table doesn't exist yet.")
            st.info(
                "**To fix this:** Run `supabase/migration_v4.sql` in your Supabase SQL Editor.\n\n"
                "Go to: **Supabase Dashboard → SQL Editor → New Query** → "
                "paste the contents of `supabase/migration_v4.sql` → click **Run**."
            )
        else:
            st.error(f"Failed to load requests: {e}")
        return

    if not requests:
        st.info("No merchant requests yet. Producers can send you match requests from their AI Merchant Match tab.")
        return

    # Summary
    pending = [r for r in requests if r["status"] == "pending"]
    confirmed = [r for r in requests if r["status"] == "confirmed"]
    cancelled = [r for r in requests if r["status"] == "cancelled"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("⏳ Pending", len(pending))
    with col2:
        st.metric("✅ Confirmed", len(confirmed))
    with col3:
        st.metric("❌ Cancelled", len(cancelled))

    st.markdown("---")

    # Filter
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "pending", "confirmed", "cancelled"],
        help="Show only requests with a specific status.",
    )

    filtered = [r for r in requests if status_filter == "All" or r["status"] == status_filter]

    for req in filtered:
        _render_request_card(req, user)


def _render_request_card(req: dict, merchant: dict):
    """Render a single merchant request card."""
    producer = req.get("profiles") or {}
    pct = float(req.get("match_percentage") or 0)

    # Status colors
    status_colors = {
        "pending": "#f59e0b",
        "confirmed": "#10b981",
        "cancelled": "#ef4444",
    }
    color = status_colors.get(req["status"], "#64748b")

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 3, 2])

        with col1:
            # Match percentage
            st.markdown(
                f"""
                <div style='text-align:center; padding:0.75rem; border-radius:10px;
                            background:{color}11; border:2px solid {color};'>
                    <div style='font-size:1.5rem; font-weight:700; color:{color};'>{pct}%</div>
                    <div style='font-size:0.7rem; color:{color}; font-weight:600;'>Match</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            # Producer info
            avatar = producer.get("avatar_url")
            if avatar:
                st.markdown(
                    f"<div style='display:flex; align-items:center; gap:0.75rem;'>"
                    f"<img src='{avatar}' style='width:40px; height:40px; border-radius:50%; object-fit:cover;' />"
                    f"<div><strong>{producer.get('full_name', 'Unknown')}</strong> {role_badge('producer')}<br/>"
                    f"<span style='color:#64748b; font-size:0.85rem;'>{producer.get('company') or 'Independent Producer'}</span>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**{producer.get('full_name', 'Unknown')}**  {role_badge('producer')}", unsafe_allow_html=True)
                st.caption(producer.get("company") or "Independent Producer")

            st.caption(f"📍 {producer.get('location', 'Unknown')} · 📧 {producer.get('email', '—')}")
            st.caption(f"📨 Received: {format_datetime(req.get('created_at'))}")
            if req.get("agreement_code"):
                st.caption(f"📋 Agreement: `{req['agreement_code']}`")

        with col3:
            # Status badge
            st.markdown(
                f"<div style='text-align:center; padding:0.5rem; background:{color}11; "
                f"border-radius:8px; border:1px solid {color};'>"
                f"<strong style='color:{color};'>{req['status'].upper()}</strong></div>",
                unsafe_allow_html=True,
            )

        # --- Producer message ---
        if req.get("producer_message"):
            st.markdown("**💬 Message from producer:**")
            st.info(req["producer_message"])

        # --- Agreement preview ---
        with st.expander("📜 Preview Agreement Terms", expanded=False):
            st.markdown(f"""
            <div style='padding:1rem; border-radius:8px; background:#fffbeb;
                        border:1px dashed #f59e0b; font-size:0.9rem;'>
            <strong>📋 Agreement Preview</strong><br/>
            <hr style='border-color:#fde68a; margin:0.5rem 0;'/>
            <strong>Agreement Code:</strong> {req.get('agreement_code', '—')}<br/>
            <strong>Producer:</strong> {producer.get('full_name', '—')}<br/>
            <strong>Merchant:</strong> {merchant.get('full_name', '—')}<br/>
            <strong>Match Score:</strong> {pct}%<br/>
            <strong>Status:</strong> {req['status'].title()}<br/>
            <hr style='border-color:#fde68a; margin:0.5rem 0;'/>
            <strong>Proposed Terms:</strong><br/>
            {req.get('proposed_terms', 'No terms specified.')}
            </div>
            """, unsafe_allow_html=True)

        # --- Actions ---
        if req["status"] == "pending":
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Confirm Agreement", key=f"confirm_{req['id']}", type="primary", use_container_width=True):
                    _confirm_request(req, merchant)
            with col_b:
                if st.button("❌ Cancel", key=f"cancel_req_{req['id']}", use_container_width=True):
                    _cancel_request(req, merchant)
        elif req["status"] == "confirmed":
            st.success("✅ You have confirmed this agreement. The producer has been notified.")
        elif req["status"] == "cancelled":
            st.error("❌ This request was cancelled.")

        st.markdown("---")


def _confirm_request(req: dict, merchant: dict):
    """Confirm a merchant request."""
    try:
        client = get_supabase_client()
        # Update the request status
        client.table("merchant_requests").update({
            "status": "confirmed",
            "merchant_response": "Agreement confirmed by merchant.",
            "responded_at": "now()",
        }).eq("id", req["id"]).execute()

        # Update the agreement status if it exists
        if req.get("agreement_code"):
            try:
                client.table("agreements").update({
                    "status": "active",
                }).eq("agreement_code", req["agreement_code"]).execute()
            except Exception:
                pass

        # Notify the producer
        try:
            client.table("notifications").insert({
                "user_id": req["producer_id"],
                "sender_id": merchant["id"],
                "title": "✅ Agreement Confirmed!",
                "message": (
                    f"{merchant['full_name']} has confirmed your supply agreement "
                    f"({req.get('agreement_code', '—')}). You can now start processing orders!"
                ),
                "type": "success",
            }).execute()
        except Exception:
            pass

        st.success("✅ Agreement confirmed! The producer has been notified.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to confirm: {e}")


def _cancel_request(req: dict, merchant: dict):
    """Cancel/decline a merchant request."""
    try:
        client = get_supabase_client()
        client.table("merchant_requests").update({
            "status": "cancelled",
            "merchant_response": "Declined by merchant.",
            "responded_at": "now()",
        }).eq("id", req["id"]).execute()

        # Update the agreement status
        if req.get("agreement_code"):
            try:
                client.table("agreements").update({
                    "status": "cancelled",
                }).eq("agreement_code", req["agreement_code"]).execute()
            except Exception:
                pass

        # Notify the producer
        try:
            client.table("notifications").insert({
                "user_id": req["producer_id"],
                "sender_id": merchant["id"],
                "title": "❌ Agreement Declined",
                "message": (
                    f"{merchant['full_name']} has declined your supply agreement "
                    f"({req.get('agreement_code', '—')})."
                ),
                "type": "warning",
            }).execute()
        except Exception:
            pass

        st.info("Request declined. The producer has been notified.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to decline: {e}")
