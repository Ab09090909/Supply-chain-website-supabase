"""Merchant dashboard - procurement, agreements, spending, and supplier insights."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.helpers import format_currency, format_datetime


def render_merchant_dashboard():
    st.title("🏪 Merchant Dashboard")
    st.caption("Track your procurement, supplier agreements, and spending")

    user = get_current_user()
    if not user:
        st.warning("Please log in to view this page.")
        return

    try:
        client = get_supabase_client()
        orders = (
            client.table("orders")
            .select("*")
            .eq("buyer_id", user["id"])
            .execute()
        ).data or []

        agreements = (
            client.table("agreements")
            .select("*")
            .eq("merchant_id", user["id"])
            .execute()
        ).data or []

        # Fetch favorites count
        favorites = (
            client.table("favorites")
            .select("product_id")
            .eq("user_id", user["id"])
            .execute()
        ).data or []

        # Fetch merchant requests
        requests = (
            client.table("merchant_requests")
            .select("id, status")
            .eq("merchant_id", user["id"])
            .execute()
        ).data or []

        # Fetch notifications count
        notifications = (
            client.table("notifications")
            .select("id")
            .eq("user_id", user["id"])
            .execute()
        ).data or []

    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    # ── Compute KPIs ──────────────────────────────────────────────────────────
    total_spent = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_orders = sum(1 for o in orders if o["status"] in ("pending", "processing"))
    delivered_orders = sum(1 for o in orders if o["status"] == "delivered")
    active_agreements = sum(1 for a in agreements if a["status"] == "active")
    pending_agreements = sum(1 for a in agreements if a["status"] == "pending")
    saved_products = len(favorites)
    incoming_requests = sum(1 for r in requests if r["status"] == "pending")
    total_orders = len(orders)

    # ── KPI Row 1: Core Metrics ───────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Core Metrics")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Spent", format_currency(total_spent), help="Total amount on paid orders")
        c2.metric("Open Orders", pending_orders, help="Orders pending or processing")
        c3.metric("Delivered", delivered_orders, help="Completed deliveries")
        c4.metric("Saved Products", saved_products, help="Products you have favorited")
        c5.metric("Notifications", len(notifications), help="Unread notifications")

    # ── KPI Row 2: Agreements & Requests ──────────────────────────────────────
    with st.container(border=True):
        st.subheader("Agreements & Match Requests")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Active Agreements", active_agreements, help="Supplier agreements currently in effect")
        c2.metric("Pending Agreements", pending_agreements, help="Awaiting acceptance")
        c3.metric("Total Agreements", len(agreements), help="All agreements")
        c4.metric("Match Requests", incoming_requests, help="Pending producer match requests")
        c5.metric("Total Orders", total_orders, help="All orders you have placed")

    # ── Recent Orders ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Recent Orders")
        if orders:
            orders_data = [
                {
                    "Order #": o["order_number"],
                    "Total": format_currency(o["total"]),
                    "Status": o["status"].title(),
                    "Payment": o["payment_status"].title(),
                    "Date": format_datetime(o.get("placed_at"), "%Y-%m-%d"),
                }
                for o in orders[:10]
            ]
            st.dataframe(orders_data, use_container_width=True, hide_index=True)
        else:
            st.info("No orders placed yet. Browse the Marketplace to find products.")

    # ── Agreements ────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Agreements")
        if agreements:
            agreements_data = [
                {
                    "Code": a["agreement_code"],
                    "Title": a.get("title", "—"),
                    "Status": a["status"].title(),
                    "Start": str(a.get("start_date", "—"))[:10],
                    "End": str(a.get("end_date", "—"))[:10],
                }
                for a in agreements
            ]
            st.dataframe(agreements_data, use_container_width=True, hide_index=True)
        else:
            st.info("No agreements yet. Use Merchant Match to find suppliers.")

    # ── Quick Actions ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Quick Actions")
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            if st.button("🛒 Marketplace", use_container_width=True):
                st.session_state["force_nav"] = "marketplace"
                st.rerun()
        with a2:
            if st.button("📨 Match Requests", use_container_width=True):
                st.session_state["force_nav"] = "merchant_requests"
                st.rerun()
        with a3:
            if st.button("🛍️ My Orders", use_container_width=True):
                st.session_state["force_nav"] = "orders"
                st.rerun()
        with a4:
            if st.button("🔔 Notifications", use_container_width=True):
                st.session_state["force_nav"] = "notifications"
                st.rerun()
