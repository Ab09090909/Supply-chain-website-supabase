"""Admin dashboard - platform-wide stats."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_admin_client
from utils.ui import page_header, metric_card
from utils.helpers import format_currency


def render_admin_dashboard():
    page_header("Admin Dashboard", "Platform-wide overview and system health")

    user = get_current_user()
    if not user:
        return

    try:
        client = get_supabase_admin_client()

        users = client.table("profiles").select("*").execute().data or []
        products = client.table("products").select("*").execute().data or []
        orders = client.table("orders").select("*").execute().data or []
        fraud = client.table("fraud_logs").select("*").execute().data or []
    except Exception as e:
        st.error(f"Failed to load stats: {e}")
        return

    # Counts by role
    role_counts = {"producer": 0, "merchant": 0, "customer": 0, "admin": 0}
    for u in users:
        role_counts[u.get("role", "customer")] = role_counts.get(u.get("role", "customer"), 0) + 1

    total_revenue = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_fraud = sum(1 for f in fraud if f["status"] == "pending")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Users", str(len(users)))
    with col2:
        metric_card("Products", str(len(products)))
    with col3:
        metric_card("Total Revenue", format_currency(total_revenue))
    with col4:
        metric_card("Pending Fraud Alerts", str(pending_fraud), color="#ef4444" if pending_fraud > 0 else "#10b981")

    st.markdown("---")
    st.markdown("##### Users by Role")
    role_cols = st.columns(4)
    for i, (role, count) in enumerate(role_counts.items()):
        with role_cols[i]:
            st.metric(role.capitalize(), count)

    st.markdown("##### Recent Orders (last 10)")
    if orders:
        st.dataframe([
            {
                "Order #": o["order_number"],
                "Total": format_currency(o["total"]),
                "Status": o["status"].title(),
                "Payment": o["payment_status"].title(),
                "Date": (o.get("placed_at") or "")[:10],
            }
            for o in orders[:10]
        ], use_container_width=True, hide_index=True)
    else:
        st.info("No orders yet.")
