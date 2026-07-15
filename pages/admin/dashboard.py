"""Admin dashboard - platform-wide stats."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_admin_client, get_supabase_client
from utils.ui import page_header, metric_card
from utils.helpers import format_currency
from utils.db_health import render_db_health_warning


def _inject_styles():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Global font */
html, body, [class*="css"], [data-testid] {
    font-family: 'Inter', sans-serif !important;
}

/* Tighten page top padding */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
}

/* st.metric — cleaner card feel */
[data-testid="stMetric"] {
    border-radius: 12px;
    padding: 16px 18px !important;
    border: 1px solid rgba(128,128,128,0.15);
}
[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    opacity: 0.6;
}
[data-testid="stMetricDelta"] { display: none; }

/* Dataframe — rounder, cleaner */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    border: 1px solid rgba(128,128,128,0.15) !important;
    overflow: hidden;
}
[data-testid="stDataFrame"] th {
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    opacity: 0.6;
}
[data-testid="stDataFrame"] td {
    font-size: 13px !important;
    font-weight: 500 !important;
}

/* Section labels */
.adm-section {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    opacity: 0.5;
    margin: 20px 0 10px;
    font-family: Inter, sans-serif;
}

/* Divider */
hr { opacity: 0.12 !important; margin: 8px 0 !important; }
</style>
""", unsafe_allow_html=True)


def _section(label: str):
    st.markdown(f'<div class="adm-section">{label}</div>', unsafe_allow_html=True)


def render_admin_dashboard():
    _inject_styles()
    page_header("Admin Dashboard", "Platform-wide overview and system health")

    user = get_current_user()
    if not user:
        return

    # Try admin client first; fall back to anon client (RLS-limited)
    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    try:
        users    = client.table("profiles").select("*").execute().data or []
        products = client.table("products").select("*").execute().data or []
        orders   = client.table("orders").select("*").execute().data or []
        fraud    = client.table("fraud_logs").select("*").execute().data or []
    except Exception as e:
        err = str(e)
        if "401" in err or "Invalid API key" in err or "invalid api key" in err.lower():
            st.error("❌ Admin access failed: Invalid Supabase API key.")
            st.info(
                "**To fix this:** Check your Supabase credentials in Streamlit secrets:\n\n"
                "1. `SUPABASE_URL` — your project URL\n"
                "2. `SUPABASE_ANON_KEY` — the anon public key (NOT the service_role key)\n"
                "3. `SUPABASE_SERVICE_ROLE_KEY` — the service_role key (for admin features)\n\n"
                "Get these from: **Supabase Dashboard → Project Settings → API**\n\n"
                "The admin dashboard needs the **service_role key** to see all users. "
                "If you only have the anon key, admin features will be limited by RLS."
            )
        elif "PGRST205" in err or "could not find" in err.lower():
            st.error("❌ Database tables are missing.")
            st.info("Run `supabase/schema.sql` and `supabase/policies.sql` in your Supabase SQL Editor first.")
            render_db_health_warning()
        else:
            st.error(f"Failed to load stats: {e}")
        return

    # Counts by role
    role_counts = {"producer": 0, "merchant": 0, "customer": 0, "admin": 0}
    for u in users:
        role_counts[u.get("role", "customer")] = role_counts.get(u.get("role", "customer"), 0) + 1

    total_revenue = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_fraud = sum(1 for f in fraud if f["status"] == "pending")

    # ── KPI cards ─────────────────────────────────────────────────────────────
    _section("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Users", str(len(users)), icon="👥")
    with col2:
        metric_card("Products", str(len(products)), icon="📦")
    with col3:
        metric_card("Revenue", format_currency(total_revenue), icon="💰")
    with col4:
        metric_card(
            "Fraud Alerts", str(pending_fraud), icon="🚨",
            color="#ef4444" if pending_fraud > 0 else "#10b981",
        )

    st.markdown("---")

    # ── Users by role ──────────────────────────────────────────────────────────
    _section("Users by Role")
    role_icons = {"producer": "🌾", "merchant": "🏪", "customer": "👤", "admin": "🛡️"}
    role_cols = st.columns(4)
    for i, (role, count) in enumerate(role_counts.items()):
        with role_cols[i]:
            st.metric(
                label=f"{role_icons.get(role, '')} {role.capitalize()}",
                value=count,
            )

    st.markdown("---")

    # ── Recent orders ──────────────────────────────────────────────────────────
    _section("Recent Orders")
    if orders:
        st.dataframe(
            [
                {
                    "Order #": o["order_number"],
                    "Total":   format_currency(o["total"]),
                    "Status":  o["status"].title(),
                    "Payment": o["payment_status"].title(),
                    "Date":    (o.get("placed_at") or "")[:10],
                }
                for o in orders[:10]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No orders yet.")
