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
    transition: box-shadow 0.25s ease, transform 0.25s ease;
    animation: fadeInUp 0.4s ease-out backwards;
}
.dash-card:hover {
    box-shadow: 0 12px 28px rgba(16, 185, 129, 0.15);
    transform: translateY(-2px);
}
.dash-card-header {
    background: linear-gradient(135deg, #0f3d23 0%, #1a5c2e 35%, #2d8a4e 70%, #34d399 100%);
    background-size: 200% 200%;
    animation: gradientShift 8s ease infinite;
    padding: 20px 24px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
    position: relative;
    overflow: hidden;
}
.dash-card-header::after {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
    border-radius: 50%;
    animation: float 6s ease-in-out infinite;
}
.dash-card-header-icon {
    font-size: 2rem;
    line-height: 1;
    animation: bounceIn 0.6s ease-out;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
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
    color: #d1fae5;
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
    background: linear-gradient(135deg, #f7f9f7 0%, #ecfdf5 100%);
    border: 1px solid #e4ece6;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    min-width: 110px;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    position: relative;
    overflow: hidden;
    animation: scaleIn 0.4s ease-out backwards;
}
.metric-box:hover {
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 8px 18px rgba(16, 185, 129, 0.15);
    border-color: #6ee7b7;
}
.metric-box::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    background: linear-gradient(90deg, #10b981 0%, #34d399 100%);
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.3s ease;
}
.metric-box:hover::before {
    transform: scaleX(1);
}
.metric-box .metric-value {
    font-size: 1.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #1a5c2e 0%, #10b981 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
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
.metric-box.alert {
    background: linear-gradient(135deg, #fff8f0 0%, #fef3c7 100%);
    border-color: #f5d5b0;
}
.metric-box.alert .metric-value {
    background: linear-gradient(135deg, #b85c00 0%, #f59e0b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.metric-box.alert::before {
    background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%);
}
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
    # Use the project's _html() helper so the multi-line HTML is rendered
    # as raw HTML and never as a Markdown code block (which would show
    # the raw <div> tags on the page).
    from utils.ui import _html
    _html(
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
        """
    )


# ─────────────────────────────────────────────────────────────────────────────

def render_producer_dashboard():
    # Animated welcome banner — replaces the plain st.title() with a
    # gradient header card and a quick stat strip.
    user = get_current_user()
    name = user.get("full_name", "Producer") if user else "Producer"

    from datetime import datetime
    hour = datetime.now().hour
    if hour < 12:
        greeting, emoji = "Good morning", "☀️"
    elif hour < 18:
        greeting, emoji = "Good afternoon", "🌤️"
    else:
        greeting, emoji = "Good evening", "🌙"

    from utils.ui import _html
    _html(f"""
    <div style='
        background: linear-gradient(135deg, #0f3d23 0%, #1a5c2e 35%, #2d8a4e 70%, #34d399 100%);
        background-size: 200% 200%;
        animation: gradientShift 8s ease infinite;
        border-radius: 18px;
        padding: 28px 32px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 24px rgba(16, 185, 129, 0.2);
    '>
      <div style='
        position: absolute; top: -40px; right: -20px;
        width: 220px; height: 220px; border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
        animation: float 5s ease-in-out infinite;
      '></div>
      <div style='
        position: absolute; bottom: -30px; left: 30%;
        width: 140px; height: 140px; border-radius: 50%;
        background: radial-gradient(circle, rgba(110, 231, 183, 0.18) 0%, transparent 70%);
        animation: float 7s ease-in-out infinite reverse;
      '></div>
      <div style='position: relative; z-index: 1;'>
        <div style='
            display: inline-block;
            background: rgba(255, 255, 255, 0.18);
            backdrop-filter: blur(8px);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            color: #d1fae5;
            font-weight: 600;
            margin-bottom: 8px;
            border: 1px solid rgba(255, 255, 255, 0.25);
        '>{emoji} {greeting}</div>
        <h1 style='
            color: #ffffff;
            font-size: 1.85rem;
            font-weight: 800;
            margin: 0 0 4px 0;
            letter-spacing: -0.02em;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        '>🌾 Welcome back, {name}!</h1>
        <p style='
            color: #d1fae5;
            font-size: 0.9rem;
            margin: 0;
            font-weight: 500;
        '>Monitor your inventory, orders, and AI-powered insights</p>
      </div>
    </div>
    """)

    # Inject CSS once
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    user = get_current_user()
    if not user:
        st.warning("Please log in to view this page.")
        return

    # ---- Verification banner for unverified users ----
    vstatus = user.get("verification_status")
    if vstatus != "verified":
        st.markdown("---")
        st.markdown("### 🔐 Account Verification Required")
        st.warning(
            "Your account is not verified yet. To unlock merchant matching and AI features, "
            "please upload a verification document below."
        )
        if st.button("📤 Verify My Account Now", type="primary", use_container_width=True):
            st.session_state["force_nav"] = "profile"
            st.rerun()
        try:
            from auth.verification import render_verification_page
            render_verification_page()
        except Exception as e:
            st.error(f"Verification module failed to load: {e}")
        st.markdown("---")

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

    # ── Sales Analytics ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("📈 Sales Analytics (last 30 days)")
        try:
            from utils.analytics import get_producer_sales_summary, get_low_stock_products
            sales = get_producer_sales_summary(user["id"], days=30)
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            with sc1:
                st.metric("Revenue (30d)", format_currency(sales.get("total_revenue_etb", 0)))
            with sc2:
                st.metric("Orders", sales.get("order_count", 0))
            with sc3:
                st.metric("Items sold", sales.get("items_sold", 0))
            with sc4:
                st.metric("Avg order", format_currency(sales.get("avg_order_value_etb", 0)))
            with sc5:
                st.metric("Unique customers", sales.get("unique_customers", 0))

            # Revenue by day chart
            rev_by_day = sales.get("revenue_by_day") or []
            if rev_by_day:
                import pandas as pd
                df = pd.DataFrame(rev_by_day).set_index("date")
                st.line_chart(df, use_container_width=True, height=200)

            # Top products
            top = sales.get("top_products") or []
            if top:
                st.markdown("##### 🏆 Top selling products (30d)")
                tp_data = [
                    {
                        "Product": t.get("name"),
                        "SKU": t.get("sku"),
                        "Units sold": t.get("units_sold", 0),
                        "Revenue": format_currency(t.get("revenue_etb", 0)),
                        "Rating": f"{t.get('avg_rating', 0):.1f}★ ({t.get('review_count', 0)})",
                    }
                    for t in top
                ]
                st.dataframe(tp_data, use_container_width=True, hide_index=True)
        except Exception as e:
            st.caption(f"Analytics unavailable: {e}")

        # Low-stock alerts
        try:
            low = get_low_stock_products(user["id"])
            if low:
                st.markdown("##### ⚠️ Low stock alerts")
                ls_data = [
                    {
                        "SKU": p.get("sku"),
                        "Product": p.get("name"),
                        "Stock": p.get("stock"),
                        "Reorder at": p.get("reorder_point"),
                        "Shortfall": p.get("shortfall", 0),
                    }
                    for p in low
                ]
                st.dataframe(ls_data, use_container_width=True, hide_index=True)
        except Exception:
            pass
