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
}
.dash-card-header {
    background: linear-gradient(135deg, #1a5c2e 0%, #2d8a4e 100%);
    padding: 20px 24px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
}
.dash-card-header-icon { font-size: 2rem; line-height: 1; }
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
.dash-card-body { padding: 18px 20px; }
.metric-grid { display: flex; flex-wrap: wrap; gap: 12px; }
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
.metric-box .metric-label-icon { margin-right: 4px; }
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
            <div class="metric-grid">{metrics_html}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────

def render_merchant_dashboard():
    st.title("🏪 Merchant Dashboard")
    st.caption("Track your procurement, supplier agreements, and spending")

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
