"""Merchant dashboard - orders placed, agreements, spending."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header, metric_card
from utils.helpers import format_currency, format_datetime


def render_merchant_dashboard():
    page_header("Merchant Dashboard", "Track your procurement and supplier agreements")

    user = get_current_user()
    if not user:
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
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    total_spent = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending = sum(1 for o in orders if o["status"] in ("pending", "processing"))
    active_agreements = sum(1 for a in agreements if a["status"] == "active")

    # Horizontal grid of metric cards (3 per row)
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("Total Spent", format_currency(total_spent), icon="💰")
    with col2:
        metric_card("Open Orders", str(pending), icon="📦")
    with col3:
        metric_card("Agreements", str(active_agreements), icon="📜")

    st.markdown("---")
    st.markdown("##### Recent Orders")
    if orders:
        st.dataframe([
            {
                "Order #": o["order_number"],
                "Total": format_currency(o["total"]),
                "Status": o["status"].title(),
                "Payment": o["payment_status"].title(),
                "Date": format_datetime(o.get("placed_at"), "%Y-%m-%d"),
            }
            for o in orders[:10]
        ], use_container_width=True, hide_index=True)
    else:
        st.info("No orders placed yet.")

    st.markdown("##### Active Agreements")
    if agreements:
        st.dataframe([
            {
                "Code": a["agreement_code"],
                "Title": a.get("title", "—"),
                "Status": a["status"].title(),
                "Start": str(a.get("start_date", "—")),
                "End": str(a.get("end_date", "—")),
            }
            for a in agreements
        ], use_container_width=True, hide_index=True)
    else:
        st.info("No agreements yet.")
