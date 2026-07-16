"""Customer dashboard - overview of orders, spending, and AI recommendations."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.helpers import format_currency, format_datetime


# ── Shared card CSS (matches producer/merchant dashboard style) ───────────────
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
/* alert tint for pending / unread */
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

def render_customer_dashboard():
    # Animated welcome banner
    user = get_current_user()
    name = user.get("full_name", "Customer") if user else "Customer"

    from datetime import datetime
    hour = datetime.now().hour
    if hour < 12:
        greeting, emoji = "Good morning", "☀️"
    elif hour < 18:
        greeting, emoji = "Good afternoon", "🌤️"
    else:
        greeting, emoji = "Good evening", "🌙"

    st.html(f"""
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
        '>🛍️ Welcome back, {name}!</h1>
        <p style='
            color: #d1fae5;
            font-size: 0.9rem;
            margin: 0;
            font-weight: 500;
        '>Track your orders, spending, and AI-powered recommendations</p>
      </div>
    </div>
    """)

    # Inject CSS once
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    if not user:
        st.warning("Please log in to view this page.")
        return

    # ---- Verification banner for unverified users ----
    # Show this prominently at the top of the dashboard for brand-new
    # signups and any unverified user. This is the bulletproof way to
    # ensure the user sees the verification prompt.
    vstatus = user.get("verification_status")
    if vstatus != "verified":
        st.markdown("---")
        st.markdown("### 🔐 Account Verification Required")
        st.warning(
            "Your account is not verified yet. To unlock ordering, messaging, and AI features, "
            "please upload a verification document below."
        )
        if st.button("📤 Verify My Account Now", type="primary", use_container_width=True):
            st.session_state["force_nav"] = "profile"
            st.rerun()
        # Also show the verification form inline (always renders)
        try:
            from auth.verification import render_verification_page
            render_verification_page()
        except Exception as e:
            st.error(f"Verification module failed to load: {e}")
        st.markdown("---")

    try:
        client = get_supabase_client()

        # ---- Orders (as buyer) ----
        orders = (
            client.table("orders")
            .select("id, order_number, status, payment_status, total, placed_at, created_at")
            .eq("buyer_id", user["id"])
            .execute()
        ).data or []

        # ---- Cart items count ----
        try:
            cart_items = (
                client.table("cart_items")
                .select("id, quantity")
                .eq("user_id", user["id"])
                .execute()
            ).data or []
        except Exception:
            cart_items = []
        cart_count = sum(int(it.get("quantity") or 0) for it in cart_items)

        # ---- Favorites count ----
        try:
            favorites = (
                client.table("favorites")
                .select("id")
                .eq("user_id", user["id"])
                .execute()
            ).data or []
        except Exception:
            favorites = []

        # ---- Notifications ----
        try:
            notifications = (
                client.table("notifications")
                .select("id, is_read")
                .eq("user_id", user["id"])
                .execute()
            ).data or []
        except Exception:
            notifications = []

    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    # ── Compute KPIs ──────────────────────────────────────────────────────────
    total_orders     = len(orders)
    pending_orders   = sum(1 for o in orders if o.get("status") == "pending")
    confirmed_orders = sum(1 for o in orders if o.get("status") in ("confirmed", "processing"))
    shipped_orders   = sum(1 for o in orders if o.get("status") == "shipped")
    delivered_orders = sum(1 for o in orders if o.get("status") == "delivered")
    cancelled_orders = sum(1 for o in orders if o.get("status") == "cancelled")

    total_spent = sum(float(o.get("total") or 0) for o in orders if o.get("payment_status") == "paid")
    pending_pay = sum(float(o.get("total") or 0) for o in orders if o.get("payment_status") == "pending")
    avg_order_value = total_spent / max(delivered_orders, 1)

    unread_notifs = sum(1 for n in notifications if not n.get("is_read"))

    # ── Card 1 — Core Metrics ─────────────────────────────────────────────────
    _card(
        icon="📊",
        title="Your Activity",
        subtitle="Orders, spending, and saved items at a glance",
        metrics_html=(
            _metric_box(str(total_orders),     "Total Orders",   "🛒")
            + _metric_box(format_currency(total_spent), "Total Spent", "💰")
            + _metric_box(str(cart_count),     "In Cart",        "🛍️",  alert=cart_count > 0)
            + _metric_box(str(len(favorites)), "Favorites",      "❤️")
            + _metric_box(str(unread_notifs),  "Unread",         "🔔",  alert=unread_notifs > 0)
        ),
    )

    # ── Card 2 — Order Status ─────────────────────────────────────────────────
    _card(
        icon="🚚",
        title="Order Status",
        subtitle="Live breakdown of your purchases",
        metrics_html=(
            _metric_box(str(pending_orders),     "Pending",    "⏳",  alert=pending_orders > 0)
            + _metric_box(str(confirmed_orders), "Processing", "🔄")
            + _metric_box(str(shipped_orders),   "Shipped",    "🚚")
            + _metric_box(str(delivered_orders), "Delivered",  "📦")
            + _metric_box(str(cancelled_orders), "Cancelled",  "❌")
        ),
    )

    # ── Recent Orders ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("🧾 Recent Orders")
        if orders:
            sorted_orders = sorted(
                orders,
                key=lambda o: o.get("placed_at") or o.get("created_at") or "",
                reverse=True,
            )
            orders_data = [
                {
                    "Order #":  o.get("order_number", "—"),
                    "Status":   (o.get("status") or "—").title(),
                    "Total":    format_currency(o.get("total") or 0),
                    "Payment":  (o.get("payment_status") or "—").title(),
                    "Placed":   format_datetime(o.get("placed_at") or o.get("created_at"), "%Y-%m-%d"),
                }
                for o in sorted_orders[:10]
            ]
            st.dataframe(orders_data, use_container_width=True, hide_index=True)
        else:
            st.info("You haven't placed any orders yet. Browse the marketplace to get started!")

    # ── Spending Snapshot ─────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("💰 Spending Snapshot")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Spent", format_currency(total_spent))
        with c2:
            st.metric("Pending Payment", format_currency(pending_pay))
        with c3:
            st.metric("Avg Order Value", format_currency(avg_order_value))

    # ── Quick Actions ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("⚡ Quick Actions")
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            if st.button("🛒 Browse Marketplace", use_container_width=True):
                st.session_state["force_nav"] = "marketplace"
                st.rerun()
        with a2:
            if st.button("🛍️ View Cart", use_container_width=True):
                st.session_state["force_nav"] = "cart"
                st.rerun()
        with a3:
            if st.button("📦 My Orders", use_container_width=True):
                st.session_state["force_nav"] = "orders"
                st.rerun()
        with a4:
            if st.button("🔔 Notifications", use_container_width=True):
                st.session_state["force_nav"] = "notifications"
                st.rerun()

    # ── Recommended for You ───────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("✨ Recommended for You")
        st.caption("Based on your browsing and purchase history")
        try:
            from utils.recommendations import get_recommendations_for_user
            recs = get_recommendations_for_user(user["id"], limit=6) or []
        except Exception:
            recs = []
        if recs:
            cols = st.columns(min(3, len(recs)))
            for i, prod in enumerate(recs[:6]):
                with cols[i % len(cols)]:
                    name = prod.get("name", "Product")
                    price = format_currency(prod.get("price", 0))
                    st.markdown(f"**{name}**")
                    st.caption(price)
                    if st.button("View", key=f"rec_{prod.get('id', i)}", use_container_width=True):
                        st.session_state["view_product_id"] = prod.get("id")
                        st.session_state["force_nav"] = "marketplace"
                        st.rerun()
        else:
            st.info("No recommendations yet. Browse the marketplace to get personalized suggestions!")
