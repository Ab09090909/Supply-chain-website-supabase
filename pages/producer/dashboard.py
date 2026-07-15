"""Producer dashboard - overview of stock, orders, revenue, and AI insights."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.helpers import format_currency, format_datetime

# ── Shared card CSS ───────────────────────────────────────────────────────────
CARD_CSS = """
<style>
/* ── Banner card (green header + white body) ─────────────────────── */
.dash-card {
    background: #ffffff;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}
.dash-card-header {
    background: linear-gradient(135deg, #1a5c2e 0%, #2d8a4e 100%);
    padding: 20px 24px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
}
.dash-card-header-icon {
    font-size: 2rem;
    line-height: 1;
}
.dash-card-header-text h3 {
    margin: 0;
    color: #ffffff;
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.3px;
}
.dash-card-header-text p {
    margin: 2px 0 0;
    color: #a8d5b5;
    font-size: 0.82rem;
}

/* ── Metric grid inside the white body ───────────────────────────── */
.dash-card-body {
    padding: 18px 20px;
}
.metric-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}
.metric-box {
    flex: 1 1 130px;
    background: #f7f9f7;
    border: 1px solid #e4ece6;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    min-width: 110px;
}
.metric-box .metric-value {
    font-size: 1.8rem;
    font-weight: 800;
    color: #1a5c2e;
    line-height: 1.1;
}
.metric-box .metric-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #6b8f72;
    margin-top: 4px;
}
.metric-box .metric-label-icon {
    margin-right: 4px;
}
/* alert tint for low-stock / pending */
.metric-box.alert .metric-value { color: #b85c00; }
.metric-box.alert { background: #fff8f0; border-color: #f5d5b0; }
</style>
"""


def _metric_box(value: str, label: str, icon: str = "", alert: bool = False) -> str:
    cls = "metric-box alert" if alert else "metric-box"
    icon_html = f'<span class="metric-label-icon">{icon}</span>' if icon else ""
    return (
        f'<div class="{cls}">'
        f'  <div class="metric-value">{value}</div>'
        f'  <div class="metric-label">{icon_html}{label}</div>'
        f'</div>'
    )


def _card(icon: str, title: str, subtitle: str, metrics_html: str) -> None:
    st.markdown(
        f"""
        <div class="dash-card">
          <div class="dash-card-header">
            <div class="dash-card-header-icon">{icon}</div>
            <div class="dash-card-header-text">
              <h3>{title}</h3>
              <p>{subtitle}</p>
            </div>
          </div>
          <div class="dash-card-body">
            <div class="metric-grid">
              {metrics_html}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────

def render_producer_dashboard():
    st.title("🌾 Producer Dashboard")
    st.caption("Monitor your inventory, orders, and AI-powered insights")

    # Inject CSS once
    st.markdown(CARD_CSS, unsafe_allow_html=True)

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
    total_products   = len(products)
    low_stock        = sum(1 for p in products if p["stock"] <= p["reorder_point"])
    active_products  = sum(1 for p in products if p.get("status") == "active")
    total_revenue    = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_orders   = sum(1 for o in orders if o["status"] == "pending")
    shipped_orders   = sum(1 for o in orders if o["status"] == "shipped")
    delivered_orders = sum(1 for o in orders if o["status"] == "delivered")
    unread_notifs    = len(notifications)
    avg_order_value  = total_revenue / max(delivered_orders, 1)

    # ── Card 1 — Core Metrics ─────────────────────────────────────────────────
    _card(
        icon="📊",
        title="Core Metrics",
        subtitle="Your products, listings, and revenue at a glance",
        metrics_html=(
            _metric_box(str(total_products),             "Total Products",    "📦")
            + _metric_box(str(active_products),          "Active Listings",   "✅")
            + _metric_box(str(low_stock),                "Low Stock",         "⚠️",  alert=low_stock > 0)
            + _metric_box(format_currency(total_revenue),"Revenue (Paid)",    "💰")
            + _metric_box(str(unread_notifs),            "Notifications",     "🔔",  alert=unread_notifs > 0)
        ),
    )

    # ── Card 2 — Order Status ─────────────────────────────────────────────────
    _card(
        icon="🛒",
        title="Orders",
        subtitle="View and manage orders from your buyers",
        metrics_html=(
            _metric_box(str(pending_orders),             "Pending",           "⏳",  alert=pending_orders > 0)
            + _metric_box(str(len(orders)),              "Active",            "🔄")
            + _metric_box(str(shipped_orders),           "Shipped",           "🚚")
            + _metric_box(str(delivered_orders),         "Delivered",         "📦")
        ),
    )

    # ── Inventory Snapshot ────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("📋 Inventory Snapshot")
        if products:
            inventory_data = [
                {
                    "SKU":       p["sku"],
                    "Name":      p["name"],
                    "Category":  p.get("category", "—"),
                    "Stock":     p["stock"],
                    "Unit":      p.get("unit", ""),
                    "Reorder Pt":p["reorder_point"],
                    "Price":     format_currency(p.get("price", 0)),
                    "Status":    "⚠️ Low" if p["stock"] <= p["reorder_point"] else "✅ OK",
                }
                for p in products
            ]
            st.dataframe(inventory_data, use_container_width=True, hide_index=True)
        else:
            st.info("No products yet — add them from the Inventory page.")

    # ── Recent Orders ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("🧾 Recent Orders")
        if orders:
            orders_data = [
                {
                    "Order #":  o["order_number"],
                    "Status":   o["status"].title(),
                    "Total":    format_currency(o["total"]),
                    "Payment":  o["payment_status"].title(),
                    "Placed":   format_datetime(o.get("placed_at"), "%Y-%m-%d"),
                }
                for o in orders[:10]
            ]
            st.dataframe(orders_data, use_container_width=True, hide_index=True)
        else:
            st.info("No orders yet.")

    # ── AI Predictions ────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("🤖 AI Predictions")
        if predictions:
            pred_data = [
                {
                    "Type":       p["prediction_type"].replace("_", " ").title(),
                    "Value":      p.get("predicted_value", "—"),
                    "Confidence": f"{float(p.get('confidence', 0) or 0) * 100:.1f}%",
                    "Model":      p.get("model_version", "—"),
                    "Created":    format_datetime(p.get("created_at"), "%Y-%m-%d"),
                }
                for p in predictions[:10]
            ]
            st.dataframe(pred_data, use_container_width=True, hide_index=True)
        else:
            st.info("No AI predictions available yet. Visit AI Insights to generate them.")

    # ── Quick Actions ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("⚡ Quick Actions")
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
