"""Producer dashboard - overview of stock, orders, AI predictions."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header, metric_card, stat_card
from utils.helpers import format_currency


def render_producer_dashboard():
    page_header("Producer Dashboard", "Monitor your products, orders, and AI insights")

    user = get_current_user()
    if not user:
        st.warning("Please log in to view this page.")
        return

    try:
        client = get_supabase_client()

        # Fetch producer's products
        products = (
            client.table("products")
            .select("*")
            .eq("producer_id", user["id"])
            .execute()
        ).data or []

        # Fetch producer's orders (as seller)
        orders = (
            client.table("orders")
            .select("*")
            .eq("seller_id", user["id"])
            .execute()
        ).data or []

        # Fetch AI predictions
        predictions = (
            client.table("ai_predictions")
            .select("*")
            .eq("producer_id", user["id"])
            .execute()
        ).data or []

    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    # KPIs
    total_products = len(products)
    low_stock = sum(1 for p in products if p["stock"] <= p["reorder_point"])
    total_revenue = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_orders = sum(1 for o in orders if o["status"] == "pending")

    # Full-width stacked metric cards (matching reference design)
    metric_card("Total Products", str(total_products), icon="📦")
    metric_card("Low Stock", str(low_stock), icon="⚠️", color="#ef4444" if low_stock > 0 else "#10b981")
    metric_card("Revenue", format_currency(total_revenue), icon="💰")
    metric_card("Pending Orders", str(pending_orders), icon="⏳")

    st.markdown("---")

    # Inventory snapshot
    st.markdown("##### Inventory Snapshot")
    if products:
        inventory_data = [
            {
                "SKU": p["sku"],
                "Name": p["name"],
                "Category": p.get("category", "—"),
                "Stock": p["stock"],
                "Unit": p.get("unit", ""),
                "Reorder Point": p["reorder_point"],
                "Status": "⚠️ Low" if p["stock"] <= p["reorder_point"] else "✅ OK",
            }
            for p in products
        ]
        st.dataframe(inventory_data, use_container_width=True, hide_index=True)
    else:
        st.info("No products yet. Add products from the Inventory page.")

    # Recent orders
    st.markdown("##### Recent Orders")
    if orders:
        recent = orders[:5]
        orders_data = [
            {
                "Order #": o["order_number"],
                "Status": o["status"].title(),
                "Total": format_currency(o["total"]),
                "Payment": o["payment_status"].title(),
                "Placed": o.get("placed_at", "—")[:10] if o.get("placed_at") else "—",
            }
            for o in recent
        ]
        st.dataframe(orders_data, use_container_width=True, hide_index=True)
    else:
        st.info("No orders yet.")

    # AI predictions
    st.markdown("##### AI Predictions")
    if predictions:
        pred_data = [
            {
                "Type": p["prediction_type"].replace("_", " ").title(),
                "Value": p.get("predicted_value", "—"),
                "Confidence": f"{float(p.get('confidence', 0) or 0) * 100:.1f}%",
                "Model": p.get("model_version", "—"),
            }
            for p in predictions[:5]
        ]
        st.dataframe(pred_data, use_container_width=True, hide_index=True)
    else:
        st.info("No AI predictions available.")
