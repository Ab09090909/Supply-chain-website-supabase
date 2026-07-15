"""Admin dashboard - platform-wide stats, user breakdown, system health."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_admin_client, get_supabase_client
from utils.helpers import format_currency, format_datetime
from utils.db_health import render_db_health_warning


def render_admin_dashboard():
    st.title("🛡️ Admin Dashboard")
    st.caption("Platform-wide overview and system health")

    user = get_current_user()
    if not user:
        st.warning("Please log in to view this page.")
        return

    # Try admin client first; fall back to anon client (RLS-limited)
    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    try:
        users = client.table("profiles").select("*").execute().data or []
        products = client.table("products").select("*").execute().data or []
        orders = client.table("orders").select("*").execute().data or []
        fraud = client.table("fraud_logs").select("*").execute().data or []
        notifications = (
            client.table("notifications")
            .select("id")
            .eq("user_id", user["id"])
            .execute()
        ).data or []
    except Exception as e:
        err = str(e)
        if "401" in err or "Invalid API key" in err or "invalid api key" in err.lower():
            st.error("Admin access failed: Invalid Supabase API key.")
            st.info(
                "**To fix this:** Check your Supabase credentials in Streamlit secrets:\n\n"
                "1. `SUPABASE_URL` — your project URL\n"
                "2. `SUPABASE_ANON_KEY` — the anon public key (NOT the service_role key)\n"
                "3. `SUPABASE_SERVICE_ROLE_KEY` — the service_role key (for admin features)\n\n"
                "Get these from: **Supabase Dashboard > Project Settings > API**\n\n"
                "The admin dashboard needs the **service_role key** to see all users. "
                "If you only have the anon key, admin features will be limited by RLS."
            )
        elif "PGRST205" in err or "could not find" in err.lower():
            st.error("Database tables are missing.")
            st.info("Run `supabase_sql/schema.sql` and `supabase_sql/policies.sql` in your Supabase SQL Editor first.")
            render_db_health_warning()
        else:
            st.error(f"Failed to load stats: {e}")
        return

    # ── Compute KPIs ──────────────────────────────────────────────────────────
    role_counts = {"producer": 0, "merchant": 0, "customer": 0, "admin": 0}
    for u in users:
        role_counts[u.get("role", "customer")] = role_counts.get(u.get("role", "customer"), 0) + 1

    total_revenue = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_fraud = sum(1 for f in fraud if f["status"] == "pending")
    resolved_fraud = sum(1 for f in fraud if f["status"] == "resolved")
    pending_orders = sum(1 for o in orders if o["status"] == "pending")
    delivered_orders = sum(1 for o in orders if o["status"] == "delivered")
    active_products = sum(1 for p in products if p.get("status") == "active")
    verified_users = sum(1 for u in users if u.get("is_verified"))

    # ── KPI Row 1: Platform Overview ──────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Platform Overview")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Users", len(users), help="All registered users")
        c2.metric("Total Products", len(products), help="All products listed")
        c3.metric("Revenue (Paid)", format_currency(total_revenue), help="Total from paid orders")
        c4.metric("Orders", len(orders), help="Total orders on the platform")
        c5.metric("Fraud Alerts", pending_fraud,
                  delta="Needs review" if pending_fraud > 0 else "All clear",
                  delta_color="inverse",
                  help="Pending fraud investigations")

    # ── KPI Row 2: User Breakdown ─────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Users by Role")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Producers", role_counts["producer"], help="Users selling products")
        c2.metric("Merchants", role_counts["merchant"], help="Business buyers")
        c3.metric("Customers", role_counts["customer"], help="Individual buyers")
        c4.metric("Admins", role_counts["admin"], help="Platform administrators")
        c5.metric("Verified", verified_users, help="Users with verified identity")

    # ── KPI Row 3: Orders & Products ──────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Orders & Products")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Pending Orders", pending_orders, help="Awaiting action")
        c2.metric("Delivered", delivered_orders, help="Completed deliveries")
        c3.metric("Active Products", active_products, help="Listed on marketplace")
        c4.metric("Resolved Fraud", resolved_fraud, help="Closed fraud cases")
        c5.metric("Notifications", len(notifications), help="Your unread notifications")

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
            st.info("No orders yet.")

    # ── Recent Fraud Alerts ───────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Recent Fraud Alerts")
        if fraud:
            fraud_data = [
                {
                    "ID": f["id"][:8],
                    "Type": f.get("fraud_type", "—").replace("_", " ").title(),
                    "Status": f["status"].title(),
                    "Severity": f.get("severity", "—").title(),
                    "Created": format_datetime(f.get("created_at"), "%Y-%m-%d"),
                }
                for f in fraud[:10]
            ]
            st.dataframe(fraud_data, use_container_width=True, hide_index=True)
        else:
            st.info("No fraud alerts.")

    # ── Quick Actions ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Quick Actions")
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            if st.button("⚙️ User Management", use_container_width=True):
                st.session_state["force_nav"] = "management"
                st.rerun()
        with a2:
            if st.button("🚨 Fraud Center", use_container_width=True):
                st.session_state["force_nav"] = "fraud"
                st.rerun()
        with a3:
            if st.button("🔔 Notifications", use_container_width=True):
                st.session_state["force_nav"] = "notifications"
                st.rerun()
        with a4:
            if st.button("👤 Profile", use_container_width=True):
                st.session_state["force_nav"] = "profile"
                st.rerun()
