"""Merchant dashboard - procurement, agreements, spending, and supplier insights."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.helpers import format_currency, format_datetime

CARD_CSS = """
<style>
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
.dash-card-body { padding: 18px 20px; }
.metric-grid { display: flex; flex-wrap: wrap; gap: 12px; }
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
.metric-box .metric-label-icon { margin-right: 4px; }
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
            <div class="metric-grid">{metrics_html}</div>
          </div>
        </div>
        """
    )


# ─────────────────────────────────────────────────────────────────────────────

def render_merchant_dashboard():
    # Animated welcome banner
    user = get_current_user()
    name = user.get("full_name", "Merchant") if user else "Merchant"

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
        '>🏪 Welcome back, {name}!</h1>
        <p style='
            color: #d1fae5;
            font-size: 0.9rem;
            margin: 0;
            font-weight: 500;
        '>Track your procurement, supplier agreements, and spending</p>
      </div>
    </div>
    """)

    st.markdown(CARD_CSS, unsafe_allow_html=True)

    if not user:
        st.warning("Please log in to view this page.")
        return

    # ---- Verification banner for unverified users ----
    vstatus = user.get("verification_status")
    if vstatus != "verified":
        st.markdown("---")
        st.markdown("### 🔐 Account Verification Required")
        st.warning(
            "Your account is not verified yet. To unlock producer matching and AI features, "
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

        favorites = (
            client.table("favorites")
            .select("product_id")
            .eq("user_id", user["id"])
            .execute()
        ).data or []

        requests = (
            client.table("merchant_requests")
            .select("id, status")
            .eq("merchant_id", user["id"])
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
    total_spent        = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_orders     = sum(1 for o in orders if o["status"] in ("pending", "processing"))
    delivered_orders   = sum(1 for o in orders if o["status"] == "delivered")
    active_agreements  = sum(1 for a in agreements if a["status"] == "active")
    pending_agreements = sum(1 for a in agreements if a["status"] == "pending")
    saved_products     = len(favorites)
    incoming_requests  = sum(1 for r in requests if r["status"] == "pending")
    unread_notifs      = len(notifications)

    # ── Card 1 — Core Metrics ─────────────────────────────────────────────────
    _card(
        icon="🏪",
        title="Core Metrics",
        subtitle="Your spending, orders, and saved products at a glance",
        metrics_html=(
            _metric_box(format_currency(total_spent), "Total Spent",    "💰")
            + _metric_box(str(pending_orders),        "Open Orders",    "⏳", alert=pending_orders > 0)
            + _metric_box(str(delivered_orders),      "Delivered",      "📦")
            + _metric_box(str(saved_products),        "Saved Products", "❤️")
            + _metric_box(str(unread_notifs),         "Notifications",  "🔔", alert=unread_notifs > 0)
        ),
    )

    # ── Card 2 — Agreements & Requests ───────────────────────────────────────
    _card(
        icon="🤝",
        title="Agreements & Match Requests",
        subtitle="Supplier agreements and incoming producer match requests",
        metrics_html=(
            _metric_box(str(active_agreements),  "Active Agreements",  "✅")
            + _metric_box(str(pending_agreements),"Pending Agreements", "⏳", alert=pending_agreements > 0)
            + _metric_box(str(len(agreements)),   "Total Agreements",   "📄")
            + _metric_box(str(incoming_requests), "Match Requests",     "📨", alert=incoming_requests > 0)
            + _metric_box(str(len(orders)),       "Total Orders",       "🛒")
        ),
    )

    # ── Recent Orders ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("🧾 Recent Orders")
        if orders:
            orders_data = [
                {
                    "Order #": o["order_number"],
                    "Total":   format_currency(o["total"]),
                    "Status":  o["status"].title(),
                    "Payment": o["payment_status"].title(),
                    "Date":    format_datetime(o.get("placed_at"), "%Y-%m-%d"),
                }
                for o in orders[:10]
            ]
            st.dataframe(orders_data, use_container_width=True, hide_index=True)
        else:
            st.info("No orders placed yet. Browse the Marketplace to find products.")

    # ── Agreements ────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("📄 Agreements")
        if agreements:
            agreements_data = [
                {
                    "Code":   a["agreement_code"],
                    "Title":  a.get("title", "—"),
                    "Status": a["status"].title(),
                    "Start":  str(a.get("start_date", "—"))[:10],
                    "End":    str(a.get("end_date", "—"))[:10],
                }
                for a in agreements
            ]
            st.dataframe(agreements_data, use_container_width=True, hide_index=True)
        else:
            st.info("No agreements yet. Use Merchant Match to find suppliers.")

    # ── Quick Actions ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("⚡ Quick Actions")
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
