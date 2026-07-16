"""Admin dashboard - platform-wide stats, user breakdown, system health.

The admin dashboard now also hosts the AI / ML Engine status panel that
used to be shown to every user on the AI Insights page. Operational
diagnostics (training counts, prediction log size, self-learning loop
state, per-product accuracy across the platform) are admin-only — they
are not user-facing features.

Non-admins still see their own per-product forecasts in AI Insights, but
the platform-wide internal metrics are no longer shown there.
"""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_admin_client, get_supabase_client
from utils.helpers import format_currency, format_datetime
from utils.db_health import render_db_health_warning
from pages.common.ai_insights import render_model_status_panel
from ai.engine import get_training_summary

# ── Shared card CSS (same as producer dashboard) ──────────────────────────────
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

def render_admin_dashboard():
    st.title("🛡️ Admin Dashboard")
    st.caption("Platform-wide overview and system health")

    st.markdown(CARD_CSS, unsafe_allow_html=True)

    user = get_current_user()
    if not user:
        st.warning("Please log in to view this page.")
        return

    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    try:
        users         = client.table("profiles").select("*").execute().data or []
        products      = client.table("products").select("*").execute().data or []
        orders        = client.table("orders").select("*").execute().data or []
        fraud         = client.table("fraud_logs").select("*").execute().data or []
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
        role = u.get("role", "customer")
        role_counts[role] = role_counts.get(role, 0) + 1

    total_revenue    = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_fraud    = sum(1 for f in fraud if f["status"] == "pending")
    resolved_fraud   = sum(1 for f in fraud if f["status"] == "resolved")
    pending_orders   = sum(1 for o in orders if o["status"] == "pending")
    delivered_orders = sum(1 for o in orders if o["status"] == "delivered")
    active_products  = sum(1 for p in products if p.get("status") == "active")
    verified_users   = sum(1 for u in users if u.get("is_verified"))
    unread_notifs    = len(notifications)

    # ── Card 1 — Platform Overview ────────────────────────────────────────────
    _card(
        icon="🛡️",
        title="Platform Overview",
        subtitle="All users, products, revenue, and alerts across the platform",
        metrics_html=(
            _metric_box(str(len(users)),                 "Total Users",     "👥")
            + _metric_box(str(len(products)),            "Total Products",  "📦")
            + _metric_box(format_currency(total_revenue),"Revenue (Paid)",  "💰")
            + _metric_box(str(len(orders)),              "Total Orders",    "🛒")
            + _metric_box(str(pending_fraud),            "Fraud Alerts",    "🚨", alert=pending_fraud > 0)
        ),
    )

    # ── Card 2 — Users by Role ────────────────────────────────────────────────
    _card(
        icon="👥",
        title="Users by Role",
        subtitle="Breakdown of registered users across all roles",
        metrics_html=(
            _metric_box(str(role_counts["producer"]),  "Producers",  "🌾")
            + _metric_box(str(role_counts["merchant"]), "Merchants",  "🏪")
            + _metric_box(str(role_counts["customer"]), "Customers",  "🧑")
            + _metric_box(str(role_counts["admin"]),    "Admins",     "🛡️")
            + _metric_box(str(verified_users),          "Verified",   "✅")
        ),
    )

    # ── Card 3 — Orders & Products ────────────────────────────────────────────
    _card(
        icon="📊",
        title="Orders & Products",
        subtitle="Order pipeline status and marketplace activity",
        metrics_html=(
            _metric_box(str(pending_orders),   "Pending Orders",  "⏳", alert=pending_orders > 0)
            + _metric_box(str(delivered_orders), "Delivered",     "📦")
            + _metric_box(str(active_products),  "Active Products","✅")
            + _metric_box(str(resolved_fraud),   "Resolved Fraud","🔒")
            + _metric_box(str(unread_notifs),    "Notifications", "🔔", alert=unread_notifs > 0)
        ),
    )

    # ── AI / ML Engine Status (admin-only diagnostics) ───────────────────────
    # This is the panel that used to live on the public AI Insights page.
    # It shows training counts, prediction log size, and self-learning
    # loop state. It is intentionally admin-only because it's operational
    # info, not a user-facing feature.
    with st.container(border=True):
        st.subheader("🧠 AI / ML Engine Status")
        st.caption(
            "Operational diagnostics for the self-learning ML engine. "
            "Use this to verify that predictions are being logged and "
            "scored against actuals, and to spot training data gaps."
        )
        try:
            ai_summary = get_training_summary()
            if not ai_summary.get("ml_available", True):
                st.warning(
                    "⚠️ ML libraries (pandas, numpy, scikit-learn) are not installed. "
                    "Add them to `requirements.txt` and reboot the app to enable AI features."
                )
            else:
                # render_model_status_panel handles its own 5+4 metric grid
                # + the self-learning loop caption + a divider.
                render_model_status_panel(ai_summary)
        except Exception as e:
            st.error(f"Failed to load AI engine status: {e}")
            st.caption(
                "Most common cause: the `ai_prediction_log` and `ai_model_metrics` "
                "tables don't exist yet. Run `supabase_sql/migration_v6.sql` in the "
                "Supabase SQL Editor to create them."
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
            st.info("No orders yet.")

    # ── Recent Fraud Alerts ───────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("🚨 Recent Fraud Alerts")
        if fraud:
            fraud_data = [
                {
                    "ID":       f["id"][:8],
                    "Type":     f.get("fraud_type", "—").replace("_", " ").title(),
                    "Status":   f["status"].title(),
                    "Severity": f.get("severity", "—").title(),
                    "Created":  format_datetime(f.get("created_at"), "%Y-%m-%d"),
                }
                for f in fraud[:10]
            ]
            st.dataframe(fraud_data, use_container_width=True, hide_index=True)
        else:
            st.info("No fraud alerts.")

    # ── Quick Actions ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("⚡ Quick Actions")
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
