"""Admin dashboard - platform-wide stats."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_admin_client, get_supabase_client
from utils.helpers import format_currency
from utils.db_health import render_db_health_warning


# ── Palette ──────────────────────────────────────────────────────────────────
BG        = "#0F172A"   # page background
SURFACE   = "#1E293B"   # card background
BORDER    = "#2D3F55"   # card border
TEXT_PRI  = "#F1F5F9"   # primary text
TEXT_SEC  = "#64748B"   # muted label
GREEN     = "#22C55E"
BLUE      = "#3B82F6"
PURPLE    = "#8B5CF6"
AMBER     = "#F59E0B"
RED       = "#EF4444"


def _css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Page background */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main .block-container {{
    background: {BG} !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stHeader"] {{ background: transparent !important; }}
section[data-testid="stSidebar"] {{
    background: {BG} !important;
    border-right: 1px solid {SURFACE};
}}

/* Kill default white block padding */
.block-container {{ padding-top: 1.5rem !important; }}

/* Native st.metric → styled card */
[data-testid="stMetric"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 20px 18px 16px !important;
    min-height: 110px;
}}
[data-testid="stMetricValue"] {{
    color: {TEXT_PRI} !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_SEC} !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stMetricDelta"] {{ display: none; }}

/* Dataframe */
[data-testid="stDataFrame"] {{
    border-radius: 14px !important;
    border: 1px solid {BORDER} !important;
    overflow: hidden;
}}
[data-testid="stDataFrame"] th {{
    background: #0D1B2E !important;
    color: {TEXT_SEC} !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stDataFrame"] td {{
    color: #CBD5E1 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}}

/* Alerts */
[data-testid="stAlert"] {{
    background: {SURFACE} !important;
    border-radius: 12px !important;
    color: {TEXT_PRI} !important;
}}

/* Divider */
hr {{ border-color: {SURFACE} !important; margin: 4px 0 !important; }}
</style>
""", unsafe_allow_html=True)


def _hero():
    """Header banner — pure inline styles, no class dependencies."""
    st.markdown(f"""
<div style="
    background: linear-gradient(135deg, {SURFACE} 0%, {BG} 70%);
    border: 1px solid {BORDER};
    border-top: 3px solid {GREEN};
    border-radius: 16px;
    padding: 28px 32px 24px;
    margin-bottom: 8px;
    font-family: Inter, sans-serif;
">
    <div style="font-size:11px;font-weight:700;letter-spacing:.12em;
                text-transform:uppercase;color:{GREEN};margin-bottom:6px;">
        🌍 Ethiopian AI Supply Chain
    </div>
    <div style="font-size:26px;font-weight:800;color:{TEXT_PRI};
                line-height:1.2;margin-bottom:6px;">
        Admin Dashboard
    </div>
    <div style="font-size:13px;color:{TEXT_SEC};margin-bottom:14px;">
        Platform-wide analytics, user management &amp; system health
    </div>
    <span style="background:#14532d;color:{GREEN};font-size:11px;font-weight:700;
                 padding:3px 12px;border-radius:20px;border:1px solid #16a34a55;">
        ● Live
    </span>
</div>
""", unsafe_allow_html=True)


def _section_label(text: str):
    st.markdown(f"""
<div style="font-size:11px;font-weight:700;color:{TEXT_SEC};
            text-transform:uppercase;letter-spacing:.12em;
            margin:24px 0 10px;font-family:Inter,sans-serif;
            display:flex;align-items:center;gap:8px;">
    {text}
    <div style="flex:1;height:1px;background:{SURFACE};margin-left:6px;"></div>
</div>
""", unsafe_allow_html=True)


def _accent_bar(color: str):
    """Thin colored top-bar above a metric card via a zero-height div."""
    st.markdown(f"""
<div style="height:3px;background:{color};border-radius:6px;
            margin-bottom:2px;"></div>
""", unsafe_allow_html=True)


def _role_block(role: str, count: int, icon: str, color: str):
    """Role summary card — pure inline styles."""
    st.markdown(f"""
<div style="
    background:{SURFACE};
    border:1px solid {BORDER};
    border-top:3px solid {color};
    border-radius:12px;
    padding:18px 12px;
    text-align:center;
    font-family:Inter,sans-serif;
">
    <div style="font-size:24px;margin-bottom:6px;">{icon}</div>
    <div style="font-size:28px;font-weight:800;color:{TEXT_PRI};
                line-height:1;letter-spacing:-0.02em;">{count}</div>
    <div style="font-size:10px;font-weight:700;color:{TEXT_SEC};
                text-transform:uppercase;letter-spacing:.1em;margin-top:5px;">
        <span style="display:inline-block;width:6px;height:6px;border-radius:50%;
                     background:{color};margin-right:5px;vertical-align:middle;"></span>
        {role}
    </div>
</div>
""", unsafe_allow_html=True)


# ── Main ─────────────────────────────────────────────────────────────────────
def render_admin_dashboard():
    _css()
    _hero()

    user = get_current_user()
    if not user:
        return

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
                "**To fix:** Check Streamlit secrets:\n"
                "- `SUPABASE_URL`\n- `SUPABASE_ANON_KEY`\n- `SUPABASE_SERVICE_ROLE_KEY`\n\n"
                "Get these from **Supabase Dashboard → Project Settings → API**"
            )
        elif "PGRST205" in err or "could not find" in err.lower():
            st.error("❌ Database tables are missing.")
            st.info("Run `supabase/schema.sql` and `supabase/policies.sql` in your Supabase SQL Editor.")
            render_db_health_warning()
        else:
            st.error(f"Failed to load stats: {e}")
        return

    # ── Derived ──────────────────────────────────────────────────────────────
    role_counts = {"producer": 0, "merchant": 0, "customer": 0, "admin": 0}
    for u in users:
        r = u.get("role", "customer")
        role_counts[r] = role_counts.get(r, 0) + 1

    total_revenue   = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_fraud   = sum(1 for f in fraud if f["status"] == "pending")
    total_orders    = len(orders)
    active_products = sum(1 for p in products if p.get("is_active", True))
    fraud_color     = RED if pending_fraud > 0 else GREEN

    # ── KPI row ──────────────────────────────────────────────────────────────
    _section_label("Key Metrics")

    kpis = [
        ("👥 Total Users",   str(len(users)),                GREEN),
        ("📦 Products",      str(active_products),           BLUE),
        ("🛒 Orders",        str(total_orders),              PURPLE),
        ("💰 Revenue",       format_currency(total_revenue), AMBER),
        ("🚨 Fraud Alerts",  str(pending_fraud),             fraud_color),
    ]
    cols = st.columns(5)
    for col, (label, value, color) in zip(cols, kpis):
        with col:
            _accent_bar(color)
            st.metric(label=label, value=value)

    # ── Role cards ───────────────────────────────────────────────────────────
    _section_label("Users by Role")
    role_meta = {
        "producer": ("🌾", GREEN),
        "merchant": ("🏪", BLUE),
        "customer": ("👤", PURPLE),
        "admin":    ("🛡️",  AMBER),
    }
    rc = st.columns(4)
    for col, (role, count) in zip(rc, role_counts.items()):
        icon, color = role_meta.get(role, ("👤", TEXT_SEC))
        with col:
            _role_block(role.capitalize(), count, icon, color)

    # ── Recent orders ────────────────────────────────────────────────────────
    _section_label("Recent Orders")
    if orders:
        st.dataframe(
            [
                {
                    "Order #": o.get("order_number", "—"),
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
