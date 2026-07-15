"""Admin dashboard - platform-wide stats."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_admin_client, get_supabase_client
from utils.helpers import format_currency
from utils.db_health import render_db_health_warning


# ─── Inject CSS once ────────────────────────────────────────────────────────
def _inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ── Base ── */
    [data-testid="stAppViewContainer"] {
        background: #0F172A;
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stMain"] { background: #0F172A; }
    [data-testid="stHeader"] { background: transparent !important; }
    section[data-testid="stSidebar"] { background: #0F172A !important; border-right: 1px solid #1E293B; }

    /* ── Typography overrides ── */
    h1, h2, h3, h4, h5, h6, p, span, label, div {
        font-family: 'Inter', sans-serif !important;
    }

    /* ── Dashboard header ── */
    .adm-hero {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 60%, #14532d18 100%);
        border: 1px solid #1E293B;
        border-radius: 16px;
        padding: 32px 36px 28px;
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
    }
    .adm-hero::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #22C55E, #16A34A, transparent);
        border-radius: 16px 16px 0 0;
    }
    .adm-hero-eyebrow {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #22C55E;
        margin-bottom: 8px;
    }
    .adm-hero-title {
        font-size: 28px;
        font-weight: 800;
        color: #F8FAFC;
        line-height: 1.2;
        margin: 0 0 6px 0;
    }
    .adm-hero-sub {
        font-size: 14px;
        color: #64748B;
        margin: 0;
        font-weight: 400;
    }
    .adm-hero-badge {
        display: inline-block;
        background: #14532d;
        color: #22C55E;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 20px;
        margin-top: 12px;
        border: 1px solid #16A34A40;
        letter-spacing: 0.04em;
    }

    /* ── Primary metric card ── */
    .adm-metric {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 22px 20px 18px;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s, transform 0.2s;
        cursor: default;
        height: 130px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .adm-metric:hover {
        border-color: #475569;
        transform: translateY(-2px);
    }
    .adm-metric-accent {
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 14px 14px 0 0;
    }
    .adm-metric-icon {
        font-size: 20px;
        line-height: 1;
        margin-bottom: 2px;
    }
    .adm-metric-value {
        font-size: 30px;
        font-weight: 800;
        color: #F8FAFC;
        line-height: 1;
        letter-spacing: -0.03em;
    }
    .adm-metric-label {
        font-size: 12px;
        font-weight: 500;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 4px;
    }

    /* ── Role card ── */
    .adm-role-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px 16px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .adm-role-icon { font-size: 22px; margin-bottom: 8px; display: block; }
    .adm-role-count {
        font-size: 26px;
        font-weight: 800;
        color: #F8FAFC;
        line-height: 1;
        letter-spacing: -0.02em;
    }
    .adm-role-label {
        font-size: 11px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 4px;
    }
    .adm-role-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
        vertical-align: middle;
    }

    /* ── Section heading ── */
    .adm-section-title {
        font-size: 13px;
        font-weight: 700;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 28px 0 14px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .adm-section-title::after {
        content: '';
        flex: 1;
        height: 1px;
        background: #1E293B;
    }

    /* ── Orders table ── */
    [data-testid="stDataFrame"] {
        background: #1E293B !important;
        border-radius: 12px !important;
        border: 1px solid #334155 !important;
        overflow: hidden;
    }
    [data-testid="stDataFrame"] table { background: transparent !important; }
    [data-testid="stDataFrame"] th {
        background: #0F172A !important;
        color: #64748B !important;
        font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        border-bottom: 1px solid #334155 !important;
        padding: 10px 14px !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stDataFrame"] td {
        color: #CBD5E1 !important;
        font-size: 13px !important;
        padding: 10px 14px !important;
        border-color: #1E293B !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stDataFrame"] tr:hover td { background: #263548 !important; }

    /* ── Error / info boxes ── */
    [data-testid="stAlert"] {
        background: #1E293B !important;
        border-radius: 12px !important;
        border-left-color: #22C55E !important;
        color: #CBD5E1 !important;
    }

    /* ── Hide default HR ── */
    hr { border-color: #1E293B !important; margin: 8px 0 !important; }

    /* ── Streamlit metric override (role section) ── */
    [data-testid="stMetric"] {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
    }
    [data-testid="stMetricValue"] { color: #F8FAFC !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #64748B !important; font-size: 11px !important; }
    </style>
    """, unsafe_allow_html=True)


# ─── Component helpers ───────────────────────────────────────────────────────
def _hero():
    st.markdown("""
    <div class="adm-hero">
        <div class="adm-hero-eyebrow">🌍 Ethiopian AI Supply Chain</div>
        <div class="adm-hero-title">Admin Dashboard</div>
        <div class="adm-hero-sub">Platform-wide analytics, user management &amp; system health</div>
        <div class="adm-hero-badge">● Live</div>
    </div>
    """, unsafe_allow_html=True)


def _metric_card(label: str, value: str, icon: str, accent: str = "#22C55E", sub: str = ""):
    sub_html = f'<div style="font-size:11px;color:#475569;margin-top:2px">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="adm-metric">
        <div class="adm-metric-accent" style="background:{accent}"></div>
        <div class="adm-metric-icon">{icon}</div>
        <div>
            <div class="adm-metric-value">{value}</div>
            <div class="adm-metric-label">{label}</div>
            {sub_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _role_card(role: str, count: int, icon: str, color: str):
    st.markdown(f"""
    <div class="adm-role-card">
        <span class="adm-role-icon">{icon}</span>
        <div class="adm-role-count">{count}</div>
        <div class="adm-role-label">
            <span class="adm-role-dot" style="background:{color}"></span>{role}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _section(title: str):
    st.markdown(f'<div class="adm-section-title">{title}</div>', unsafe_allow_html=True)


# ─── Main render ────────────────────────────────────────────────────────────
def render_admin_dashboard():
    _inject_styles()
    _hero()

    user = get_current_user()
    if not user:
        return

    # ── Data fetch ──────────────────────────────────────────────────────────
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
        if "401" in err or "invalid api key" in err.lower():
            st.error("❌ Admin access failed: Invalid Supabase API key.")
            st.info(
                "**To fix this:** Check your Supabase credentials in Streamlit secrets:\n\n"
                "1. `SUPABASE_URL` — your project URL\n"
                "2. `SUPABASE_ANON_KEY` — the anon public key\n"
                "3. `SUPABASE_SERVICE_ROLE_KEY` — the service_role key (required for admin)\n\n"
                "Get these from: **Supabase Dashboard → Project Settings → API**"
            )
        elif "PGRST205" in err or "could not find" in err.lower():
            st.error("❌ Database tables are missing.")
            st.info("Run `supabase/schema.sql` and `supabase/policies.sql` in your Supabase SQL Editor.")
            render_db_health_warning()
        else:
            st.error(f"Failed to load stats: {e}")
        return

    # ── Derived stats ────────────────────────────────────────────────────────
    role_counts  = {"producer": 0, "merchant": 0, "customer": 0, "admin": 0}
    for u in users:
        r = u.get("role", "customer")
        role_counts[r] = role_counts.get(r, 0) + 1

    total_revenue = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_fraud = sum(1 for f in fraud if f["status"] == "pending")
    total_orders  = len(orders)
    active_products = sum(1 for p in products if p.get("is_active", True))

    # ── KPI strip ────────────────────────────────────────────────────────────
    _section("Key Metrics")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _metric_card("Total Users",    str(len(users)),             "👥", "#22C55E")
    with c2:
        _metric_card("Products",       str(active_products),        "📦", "#3B82F6",
                     sub=f"{len(products)} total")
    with c3:
        _metric_card("Total Orders",   str(total_orders),           "🛒", "#8B5CF6")
    with c4:
        _metric_card("Revenue",        format_currency(total_revenue), "💰", "#F59E0B")
    with c5:
        fraud_color = "#EF4444" if pending_fraud > 0 else "#22C55E"
        _metric_card("Fraud Alerts",   str(pending_fraud),          "🚨", fraud_color,
                     sub="Pending review" if pending_fraud > 0 else "All clear")

    # ── Users by role ─────────────────────────────────────────────────────────
    _section("Platform Users by Role")
    role_meta = {
        "producer": ("🌾", "#22C55E"),
        "merchant": ("🏪", "#3B82F6"),
        "customer": ("👤", "#8B5CF6"),
        "admin":    ("🛡️",  "#F59E0B"),
    }
    rc1, rc2, rc3, rc4 = st.columns(4)
    for col, (role, count) in zip([rc1, rc2, rc3, rc4], role_counts.items()):
        icon, color = role_meta.get(role, ("👤", "#64748B"))
        with col:
            _role_card(role.capitalize(), count, icon, color)

    # ── Recent orders ─────────────────────────────────────────────────────────
    _section("Recent Orders")
    if orders:
        rows = [
            {
                "Order #":  o.get("order_number", "—"),
                "Total":    format_currency(o["total"]),
                "Status":   o["status"].title(),
                "Payment":  o["payment_status"].title(),
                "Date":     (o.get("placed_at") or "")[:10],
            }
            for o in orders[:10]
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No orders yet.")
