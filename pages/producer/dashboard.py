"""Producer dashboard - overview of stock, orders, revenue, and AI insights."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.helpers import format_currency, format_datetime


def render_producer_dashboard():
    st.title("🌾 Producer Dashboard")
    st.caption("Monitor your inventory, orders, and AI-powered insights")

    user = get_current_user()
    if not user:
        st.warning("Please log in to view this page.")
        return

    try:
        client = get_supabase_client()

        products = (
            client.table("products")
            .select("*")
            .eq("producer_id", user["id"])
            .execute()
        ).data or []

        orders = (
            client.table("orders")
            .select("*")
            .eq("seller_id", user["id"])
            .execute()
        ).data or []

        predictions = (
            client.table("ai_predictions")
            .select("*")
            .eq("producer_id", user["id"])
            .execute()
        ).data or []

        # Fetch notifications count for unread
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
    total_products = len(products)
    low_stock = sum(1 for p in products if p["stock"] <= p["reorder_point"])
    active_products = sum(1 for p in products if p.get("status") == "active")
    total_revenue = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_orders = sum(1 for o in orders if o["status"] == "pending")
    shipped_orders = sum(1 for o in orders if o["status"] == "shipped")
    delivered_orders = sum(1 for o in orders if o["status"] == "delivered")
    unread_notifications = len(notifications)

    # ── KPI Row 1: Core Metrics ───────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Core Metrics")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Products", total_products, help="All products you have listed")
        c2.metric("Active Listings", active_products, help="Products currently visible on marketplace")
        c3.metric("Low Stock Alerts", low_stock,
                  delta="Needs attention" if low_stock > 0 else "All good",
                  delta_color="inverse",
                  help="Products at or below reorder point")
        c4.metric("Revenue (Paid)", format_currency(total_revenue), help="Total from paid orders")
        c5.metric("Notifications", unread_notifications, help="Unread notifications")

    # ── KPI Row 2: Order Breakdown ────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Order Status")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Pending", pending_orders, help="Awaiting your acceptance")
        c2.metric("Shipped", shipped_orders, help="In transit to buyer")
        c3.metric("Delivered", delivered_orders, help="Completed orders")
        c4.metric("Total Orders", len(orders), help="All orders received")
        c5.metric("Avg Order Value",
                  format_currency(total_revenue / max(delivered_orders, 1)),
                  help="Average value of delivered orders")

    # ── Inventory Snapshot ────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Inventory Snapshot")
        if products:
            inventory_data = [
                {
                    "SKU": p["sku"],
                    "Name": p["name"],
                    "Category": p.get("category", "—"),
                    "Stock": p["stock"],
                    "Unit": p.get("unit", ""),
                    "Reorder Pt": p["reorder_point"],
                    "Price": format_currency(p.get("price", 0)),
                    "Status": "Low" if p["stock"] <= p["reorder_point"] else "OK",
                }
                for p in products
            ]
            st.dataframe(inventory_data, use_container_width=True, hide_index=True)
        else:
            st.info("No products yet — add them from the Inventory page.")

    # ── Recent Orders ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Recent Orders")
        if orders:
            orders_data = [
                {
                    "Order #": o["order_number"],
                    "Status": o["status"].title(),
                    "Total": format_currency(o["total"]),
                    "Payment": o["payment_status"].title(),
                    "Placed": format_datetime(o.get("placed_at"), "%Y-%m-%d"),
                }
                for o in orders[:10]
            ]
            st.dataframe(orders_data, use_container_width=True, hide_index=True)
        else:
            st.info("No orders yet.")

    # ── AI Predictions ────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("AI Predictions")
        if predictions:
            pred_data = [
                {
                    "Type": p["prediction_type"].replace("_", " ").title(),
                    "Value": p.get("predicted_value", "—"),
                    "Confidence": f"{float(p.get('confidence', 0) or 0) * 100:.1f}%",
                    "Model": p.get("model_version", "—"),
                    "Created": format_datetime(p.get("created_at"), "%Y-%m-%d"),
                }
                for p in predictions[:10]
            ]
            st.dataframe(pred_data, use_container_width=True, hide_index=True)
        else:
            st.info("No AI predictions available yet. Visit AI Insights to generate them.")

    # ── Quick Actions ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Quick Actions")
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            if st.button("📦 Add Product", use_container_width=True):
                st.session_state["force_nav"] = "inventory"
                st.rerun()
        with a2:
            if st.button("🛒 View Orders", use_container_width=True):
                st.session_state["force_nav"] = "orders"
                st.rerun()
        with a3:
            if st.button("🤝 Merchant Match", use_container_width=True):
                st.session_state["force_nav"] = "merchant_match"
                st.rerun()
        with a4:
            if st.button("🔔 Notifications", use_container_width=True):
                st.session_state["force_nav"] = "notifications"
                st.rerun()
