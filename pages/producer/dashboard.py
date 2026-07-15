"""Producer dashboard - overview of stock, orders, AI predictions."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header, metric_card, stat_card
from utils.helpers import format_currency


# ── Design tokens ──────────────────────────────────────────────────────────────
_CSS = """
<style>
/* ── Global ── */
[data-testid="stAppViewContainer"] {
    background: #f0f4f1;
    font-family: 'Inter', system-ui, sans-serif;
}
[data-testid="stHeader"] { background: transparent; }

/* ── Page header ── */
.pd-page-header {
    background: linear-gradient(135deg, #1a3a2e 0%, #14532d 60%, #0f3d23 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.pd-page-header h1 {
    color: #f0fdf4;
    font-size: 1.75rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.5px;
}
.pd-page-header p {
    color: #86efac;
    font-size: 0.875rem;
    margin: 4px 0 0;
}
.pd-header-icon {
    font-size: 2.4rem;
    line-height: 1;
}

/* ── Section label ── */
.pd-section-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6b7280;
    margin: 0 0 12px;
}

/* ── Donut KPI card ── */
.pd-kpi-wrap {
    background: #ffffff;
    border-radius: 16px;
    padding: 24px 16px 20px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,.06), 0 4px 12px rgba(0,0,0,.04);
    transition: transform .15s ease, box-shadow .15s ease;
    border: 1px solid rgba(0,0,0,.04);
    position: relative;
    overflow: hidden;
}
.pd-kpi-wrap:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,.10);
}
.pd-kpi-accent-bar {
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
}
.pd-kpi-svg-wrap { position: relative; display: inline-block; }
.pd-kpi-center {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    line-height: 1.1;
}
.pd-kpi-value {
    font-size: 1.45rem;
    font-weight: 800;
    color: #111827;
    display: block;
    letter-spacing: -1px;
}
.pd-kpi-icon { font-size: 1.4rem; display: block; }
.pd-kpi-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6b7280;
    margin-top: 10px;
}

/* ── Divider ── */
.pd-divider {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 28px 0 20px;
}

/* ── Table card ── */
.pd-table-card {
    background: #ffffff;
    border-radius: 14px;
    padding: 20px 20px 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
    border: 1px solid rgba(0,0,0,.04);
    margin-bottom: 20px;
}
.pd-table-title {
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #374151;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.pd-table-title span { font-size: 1rem; }

/* ── Empty state ── */
.pd-empty {
    text-align: center;
    padding: 32px 16px;
    color: #9ca3af;
    font-size: 0.85rem;
}
.pd-empty-icon { font-size: 2rem; display: block; margin-bottom: 8px; }

/* ── Streamlit dataframe tweaks ── */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
}
</style>
"""


def _donut_card(label: str, value: str, icon: str, color: str, pct: float = 0.65) -> str:
    """Render an SVG donut ring KPI card (pure HTML, Streamlit-compatible)."""
    r = 44
    circ = 2 * 3.14159 * r
    filled = circ * min(max(pct, 0.0), 1.0)
    gap = circ - filled
    # bg track color
    track = "#f3f4f6"

    return f"""
<div class="pd-kpi-wrap">
  <div class="pd-kpi-accent-bar" style="background:{color};"></div>
  <div class="pd-kpi-svg-wrap">
    <svg width="108" height="108" viewBox="0 0 108 108">
      <!-- track -->
      <circle cx="54" cy="54" r="{r}"
        fill="none" stroke="{track}" stroke-width="9"/>
      <!-- progress -->
      <circle cx="54" cy="54" r="{r}"
        fill="none" stroke="{color}" stroke-width="9"
        stroke-linecap="round"
        stroke-dasharray="{filled:.2f} {gap:.2f}"
        transform="rotate(-90 54 54)"/>
    </svg>
    <div class="pd-kpi-center">
      <span class="pd-kpi-icon">{icon}</span>
    </div>
  </div>
  <div class="pd-kpi-value">{value}</div>
  <div class="pd-kpi-label">{label}</div>
</div>
"""


def _table_card(title: str, icon: str, body_html: str) -> str:
    return f"""
<div class="pd-table-card">
  <div class="pd-table-title"><span>{icon}</span>{title}</div>
  {body_html}
</div>
"""


def _empty(msg: str, icon: str = "📭") -> str:
    return f'<div class="pd-empty"><span class="pd-empty-icon">{icon}</span>{msg}</div>'


# ── Main render ────────────────────────────────────────────────────────────────

def render_producer_dashboard():
    st.html(_CSS)

    # ── Page header ──────────────────────────────────────────────────────────
    st.html("""
    <div class="pd-page-header">
      <div class="pd-header-icon">🌾</div>
      <div>
        <h1>Producer Dashboard</h1>
        <p>Monitor your inventory, orders, and AI-powered insights</p>
      </div>
    </div>
    """)

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

    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    # ── KPIs ─────────────────────────────────────────────────────────────────
    total_products  = len(products)
    low_stock       = sum(1 for p in products if p["stock"] <= p["reorder_point"])
    total_revenue   = sum(float(o["total"]) for o in orders if o["payment_status"] == "paid")
    pending_orders  = sum(1 for o in orders if o["status"] == "pending")

    # Compute normalised percentages (soft caps for visual interest)
    _safe_pct = lambda n, cap: min(n / cap, 1.0) if cap else 0.0

    kpis = [
        ("Total Products",  str(total_products),          "📦", "#0d9488",
         _safe_pct(total_products, 50)),
        ("Low Stock Alerts", str(low_stock),              "⚠️",
         "#ef4444" if low_stock > 0 else "#10b981",
         _safe_pct(low_stock, total_products or 1)),
        ("Revenue",         format_currency(total_revenue), "💰", "#d97706",
         _safe_pct(total_revenue, 100_000)),
        ("Pending Orders",  str(pending_orders),          "⏳", "#6366f1",
         _safe_pct(pending_orders, 20)),
    ]

    cols = st.columns(4, gap="medium")
    for col, (label, value, icon, color, pct) in zip(cols, kpis):
        with col:
            st.html(_donut_card(label, value, icon, color, pct))

    st.html('<hr class="pd-divider"/>')

    # ── Inventory snapshot ───────────────────────────────────────────────────
    st.html('<p class="pd-section-label">Inventory Snapshot</p>')
    if products:
        inventory_data = [
            {
                "SKU":          p["sku"],
                "Name":         p["name"],
                "Category":     p.get("category", "—"),
                "Stock":        p["stock"],
                "Unit":         p.get("unit", ""),
                "Reorder Point": p["reorder_point"],
                "Status":       "⚠️ Low" if p["stock"] <= p["reorder_point"] else "✅ OK",
            }
            for p in products
        ]
        st.dataframe(inventory_data, use_container_width=True, hide_index=True)
    else:
        st.html(_empty("No products yet — add them from the Inventory page.", "📦"))

    st.html('<hr class="pd-divider"/>')

    # ── Recent orders ────────────────────────────────────────────────────────
    st.html('<p class="pd-section-label">Recent Orders</p>')
    if orders:
        recent = orders[:5]
        orders_data = [
            {
                "Order #":  o["order_number"],
                "Status":   o["status"].title(),
                "Total":    format_currency(o["total"]),
                "Payment":  o["payment_status"].title(),
                "Placed":   (o.get("placed_at", "—") or "—")[:10],
            }
            for o in recent
        ]
        st.dataframe(orders_data, use_container_width=True, hide_index=True)
    else:
        st.html(_empty("No orders yet.", "🛒"))

    st.html('<hr class="pd-divider"/>')

    # ── AI predictions ───────────────────────────────────────────────────────
    st.html('<p class="pd-section-label">AI Predictions</p>')
    if predictions:
        pred_data = [
            {
                "Type":       p["prediction_type"].replace("_", " ").title(),
                "Value":      p.get("predicted_value", "—"),
                "Confidence": f"{float(p.get('confidence', 0) or 0) * 100:.1f}%",
                "Model":      p.get("model_version", "—"),
            }
            for p in predictions[:5]
        ]
        st.dataframe(pred_data, use_container_width=True, hide_index=True)
    else:
        st.html(_empty("No AI predictions available yet.", "🤖"))
