"""Admin dashboard - platform-wide stats."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_admin_client, get_supabase_client
from utils.helpers import format_currency
from utils.db_health import render_db_health_warning


# ── Theme-aware palette ───────────────────────────────────────────────────────
def _palette():
    """Return color tokens based on current theme in session_state."""
    is_dark = st.session_state.get("dark_mode", True)

    if is_dark:
        return dict(
            BG       = "#0F172A",
            SURFACE  = "#1E293B",
            BORDER   = "#2D3F55",
            TEXT_PRI = "#F1F5F9",
            TEXT_SEC = "#64748B",
            HERO_TOP = "linear-gradient(135deg,#1E293B 0%,#0F172A 70%)",
            TABLE_HD = "#0D1B2E",
        )
    else:
        return dict(
            BG       = "#F8FAFC",
            SURFACE  = "#FFFFFF",
            BORDER   = "#E2E8F0",
            TEXT_PRI = "#0F172A",
            TEXT_SEC = "#64748B",
            HERO_TOP = "linear-gradient(135deg,#EFF6FF 0%,#F8FAFC 70%)",
            TABLE_HD = "#F1F5F9",
        )

# Accent colors stay the same in both themes
GREEN  = "#16A34A"
BLUE   = "#2563EB"
PURPLE = "#7C3AED"
AMBER  = "#D97706"
RED    = "#DC2626"

# Lighter tints for light-mode accent bars / borders
GREEN_L  = "#22C55E"
BLUE_L   = "#3B82F6"
PURPLE_L = "#8B5CF6"
AMBER_L  = "#F59E0B"
RED_L    = "#EF4444"


def _css(p: dict):
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main .block-container {{
    background: {p['BG']} !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stHeader"] {{ background: transparent !important; }}
section[data-testid="stSidebar"] {{
    background: {p['BG']} !important;
    border-right: 1px solid {p['BORDER']};
}}
.block-container {{ padding-top: 1.5rem !important; }}

/* st.metric card */
[data-testid="stMetric"] {{
    background: {p['SURFACE']};
    border: 1px solid {p['BORDER']};
    border-radius: 14px;
    padding: 20px 18px 16px !important;
    min-height: 110px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
}}
[data-testid="stMetricValue"] {{
    color: {p['TEXT_PRI']} !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stMetricLabel"] {{
    color: {p['TEXT_SEC']} !important;
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
    border: 1px solid {p['BORDER']} !important;
    overflow: hidden;
}}
[data-testid="stDataFrame"] th {{
    background: {p['TABLE_HD']} !important;
    color: {p['TEXT_SEC']} !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stDataFrame"] td {{
    color: {p['TEXT_PRI']} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}}

[data-testid="stAlert"] {{
    background: {p['SURFACE']} !important;
    border-radius: 12px !important;
    color: {p['TEXT_PRI']} !important;
}}
hr {{ border-color: {p['BORDER']} !important; margin: 4px 0 !important; }}
</style>
""", unsafe_allow_html=True)


def _hero(p: dict):
    st.markdown(f"""
<div style="
    background:{p['HERO_TOP']};
    border:1px solid {p['BORDER']};
    border-top:3px solid {GREEN_L};
    border-radius:16px;
    padding:28px 32px 24px;
    margin-bottom:8px;
    font-family:Inter,sans-serif;
">
    <div style="font-size:11px;font-weight:700;letter-spacing:.12em;
                text-transform:uppercase;color:{GREEN};margin-bottom:6px;">
        🌍 Ethiopian AI Supply Chain
    </div>
    <div style="font-size:26px;font-weight:800;color:{p['TEXT_PRI']};
                line-height:1.2;margin-bottom:6px;">
        Admin Dashboard
    </div>
    <div style="font-size:13px;color:{p['TEXT_SEC']};margin-bottom:14px;">
        Platform-wide analytics, user management &amp; system health
    </div>
    <span style="background:#dcfce7;color:{GREEN};font-size:11px;font-weight:700;
                 padding:3px 12px;border-radius:20px;border:1px solid #bbf7d0;">
        ● Live
    </span>
</div>
""", unsafe_allow_html=True)


def _section_label(text: str, p: dict):
    st.markdown(f"""
<div style="font-size:11px;font-weight:700;color:{p['TEXT_SEC']};
            text-transform:uppercase;letter-spacing:.12em;
            margin:24px 0 10px;font-family:Inter,sans-serif;
            display:flex;align-items:center;gap:8px;">
    {text}
    <div style="flex:1;height:1px;background:{p['BORDER']};margin-left:6px;"></div>
</div>
""", unsafe_allow_html=True)


def _accent_bar(color: str):
    st.markdown(
        f'<div style="height:3px;background:{color};border-radius:6px;margin-bottom:2px;"></div>',
        unsafe_allow_html=True,
    )


def _role_block(role: str, count: int, icon: str, color: str, p: dict):
    st.markdown(f"""
<div style="
    background:{p['SURFACE']};
    border:1px solid {p['BORDER']};
    border-top:3px solid {color};
    border-radius:12px;
    padding:18px 12px;
    text-align:center;
    font-family:Inter,sans-serif;
    box-shadow:0 1px 3px rgba(0,0,0,.05);
">
    <div style="font-size:24px;margin-bottom:6px;">{icon}</div>
    <div style="font-size:28px;font-weight:800;color:{p['TEXT_PRI']};
                line-height:1;letter-spacing:-0.02em;">{count}</div>
    <div style="font-size:10px;font-weight:700;color:{p['TEXT_SEC']};
                text-transform:uppercase;letter-spacing:.1em;margin-top:5px;">
        <span style="display:inline-block;width:6px;height:6px;border-radius:50%;
                     background:{color};margin-right:5px;vertical-align:middle;"></span>
        {role}
    </div>
</div>
""", unsafe_allow_html=True)


# ── Main ─────────────────────────────────────────────────────────────────────
def render_admin_dashboard():
    p = _palette()          # read theme once; pass to every component
    _css(p)
    _hero(p)

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

    # ── Derived stats ─────────────────────────────────────────────────────────
    role_counts = {"producer": 0, "merchant": 0, "customer": 0, "admin": 0}
    for u in users:
        r = u.get("role", "customer")
        role_counts[r] = role_counts.get(r, 0) + 1

    total_revenue   = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_fraud   = sum(1 for f in fraud if f["status"] == "pending")
    total_orders    = len(orders)
    active_products = sum(1 for p_item in products if p_item.get("is_active", True))
    fraud_accent    = RED_L if pending_fraud > 0 else GREEN_L

    # ── KPI strip ─────────────────────────────────────────────────────────────
    _section_label("Key Metrics", p)
    kpis = [
        ("👥 Total Users",  str(len(users)),                GREEN_L),
        ("📦 Products",     str(active_products),           BLUE_L),
        ("🛒 Orders",       str(total_orders),              PURPLE_L),
        ("💰 Revenue",      format_currency(total_revenue), AMBER_L),
        ("🚨 Fraud Alerts", str(pending_fraud),             fraud_accent),
    ]
    for col, (label, value, color) in zip(st.columns(5), kpis):
        with col:
            _accent_bar(color)
            st.metric(label=label, value=value)

    # ── Role cards ────────────────────────────────────────────────────────────
    _section_label("Users by Role", p)
    role_meta = {
        "producer": ("🌾", GREEN_L),
        "merchant": ("🏪", BLUE_L),
        "customer": ("👤", PURPLE_L),
        "admin":    ("🛡️",  AMBER_L),
    }
    for col, (role, count) in zip(st.columns(4), role_counts.items()):
        icon, color = role_meta.get(role, ("👤", "#64748B"))
        with col:
            _role_block(role.capitalize(), count, icon, color, p)

    # ── Recent orders ──────────────────────────────────────────────────────────
    _section_label("Recent Orders", p)
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
