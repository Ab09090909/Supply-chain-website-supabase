"""Producer orders view — with Accept/Confirm, Ship, and Deliver buttons."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency, format_datetime


NEXT_STATUS = {
    "pending": "confirmed",
    "confirmed": "processing",
    "processing": "shipped",
    "shipped": "delivered",
}

STATUS_LABELS = {
    "pending":    "⏳ Pending",
    "confirmed":  "✅ Confirmed",
    "processing": "🔄 Processing",
    "shipped":    "🚚 Shipped",
    "delivered":  "📦 Delivered",
    "cancelled":  "❌ Cancelled",
}

STATUS_COLORS = {
    "pending":    "#f59e0b",
    "confirmed":  "#10b981",
    "processing": "#3b82f6",
    "shipped":    "#8b5cf6",
    "delivered":  "#059669",
    "cancelled":  "#ef4444",
}

ACTION_LABELS = {
    "pending":    "✅ Accept Order",
    "confirmed":  "🔄 Start Processing",
    "processing": "🚚 Mark as Shipped",
    "shipped":    "📦 Mark as Delivered",
}

_CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background: #f0f4f1;
    font-family: 'Inter', system-ui, sans-serif;
}
[data-testid="stHeader"] { background: transparent; }

/* Page header */
.po-page-header {
    background: linear-gradient(135deg, #1a3a2e 0%, #14532d 60%, #0f3d23 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.po-page-header h1 { color: #f0fdf4; font-size: 1.75rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
.po-page-header p  { color: #86efac; font-size: 0.875rem; margin: 4px 0 0; }
.po-header-icon    { font-size: 2.4rem; line-height: 1; }

/* KPI strip */
.po-kpi-strip {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}
.po-kpi-pill {
    flex: 1;
    min-width: 100px;
    background: #fff;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    border: 1px solid rgba(0,0,0,.05);
    box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.po-kpi-pill .kv { font-size: 1.6rem; font-weight: 800; color: #111827; line-height: 1; }
.po-kpi-pill .kl { font-size: 0.67rem; font-weight: 600; letter-spacing: 0.09em; text-transform: uppercase; color: #9ca3af; margin-top: 4px; }

/* Filter row */
.po-filter-wrap { margin-bottom: 18px; }

/* Section label */
.po-section-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #6b7280; margin: 0 0 12px;
}

/* Order card */
.po-card {
    background: #fff;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 14px;
    border: 1px solid rgba(0,0,0,.05);
    box-shadow: 0 1px 4px rgba(0,0,0,.05), 0 2px 8px rgba(0,0,0,.03);
}

/* Order header bar */
.po-card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 12px;
}
.po-order-num   { font-size: 0.95rem; font-weight: 700; color: #111827; }
.po-order-meta  { font-size: 0.76rem; color: #9ca3af; margin-top: 2px; }
.po-order-buyer { font-size: 0.78rem; color: #374151; margin-top: 4px; }

/* Status badge */
.po-status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    white-space: nowrap;
}

/* Inline stats row */
.po-stats-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 12px;
}
.po-stat-chip {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 0.78rem;
    color: #374151;
}
.po-stat-chip b { color: #111827; }

/* Shipping block */
.po-shipping {
    background: #f8fafc;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.78rem;
    color: #374151;
    margin-bottom: 10px;
    border: 1px solid #e2e8f0;
}
.po-shipping b { color: #111827; }

/* Notes */
.po-notes {
    font-size: 0.78rem;
    color: #6b7280;
    background: #fffbeb;
    border-left: 3px solid #fbbf24;
    padding: 6px 12px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 10px;
}

/* Action strip */
.po-divider { border: none; border-top: 1px solid #e5e7eb; margin: 12px 0; }

/* Empty */
.po-empty {
    text-align: center; padding: 48px 16px;
    background: #fff; border-radius: 14px;
    border: 1px solid rgba(0,0,0,.05); color: #9ca3af; font-size: 0.85rem;
}
.po-empty-icon { font-size: 2.5rem; display: block; margin-bottom: 10px; }
</style>
"""


def render_producer_orders():
    st.html(_CSS)

    st.html("""
    <div class="po-page-header">
      <div class="po-header-icon">🛒</div>
      <div>
        <h1>Orders</h1>
        <p>View and manage orders from your buyers</p>
      </div>
    </div>
    """)

    user = get_current_user()
    if not user:
        return

    try:
        client = get_supabase_client()
        orders = (
            client.table("orders")
            .select("*, order_items(*), buyer:profiles!orders_buyer_id_fkey(full_name, email, phone, location)")
            .eq("seller_id", user["id"])
            .order("created_at", desc=True)
            .execute()
        ).data or []
    except Exception as e:
        st.error(f"Failed to load orders: {e}")
        return

    if not orders:
        st.html('<div class="po-empty"><span class="po-empty-icon">🛒</span>No orders yet. Once buyers place orders on your products, they\'ll appear here.</div>')
        return

    # ── KPI strip ────────────────────────────────────────────────────────────
    counts = {
        "⏳ Pending":   sum(1 for o in orders if o["status"] == "pending"),
        "🔄 Active":    sum(1 for o in orders if o["status"] in ("confirmed", "processing")),
        "🚚 Shipped":   sum(1 for o in orders if o["status"] == "shipped"),
        "📦 Delivered": sum(1 for o in orders if o["status"] == "delivered"),
    }
    pills = "".join(
        f'<div class="po-kpi-pill"><div class="kv">{v}</div><div class="kl">{k}</div></div>'
        for k, v in counts.items()
    )
    st.html(f'<div class="po-kpi-strip">{pills}</div>')

    # ── Filter ───────────────────────────────────────────────────────────────
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "pending", "confirmed", "processing", "shipped", "delivered", "cancelled"],
        label_visibility="collapsed",
    )
    filtered = [o for o in orders if status_filter == "All" or o["status"] == status_filter]

    st.html(f'<p class="po-section-label">{len(filtered)} order{"s" if len(filtered) != 1 else ""}</p>')

    for o in filtered:
        _render_order_card(o, user)


def _render_order_card(order: dict, producer: dict):
    status  = order["status"]
    color   = STATUS_COLORS.get(status, "#64748b")
    buyer   = order.get("buyer") or {}
    items   = order.get("order_items") or []
    ship    = order.get("shipping_address") or {}

    # Build buyer line
    buyer_parts = []
    if buyer.get("full_name"): buyer_parts.append(f"👤 {buyer['full_name']}")
    if buyer.get("email"):     buyer_parts.append(f"📧 {buyer['email']}")
    if buyer.get("phone"):     buyer_parts.append(f"📞 {buyer['phone']}")
    buyer_line = " &nbsp;·&nbsp; ".join(buyer_parts) if buyer_parts else "Buyer info unavailable"

    # Build shipping line
    ship_line = ""
    if ship:
        parts = [ship.get("name", ""), ship.get("phone", ""), ship.get("street", ""),
                 ship.get("city", ""), ship.get("region", ""), ship.get("country", "")]
        ship_line = ", ".join(p for p in parts if p)

    st.html(f"""
    <div class="po-card">
      <div class="po-card-header">
        <div>
          <div class="po-order-num">{order['order_number']}</div>
          <div class="po-order-meta">Placed {format_datetime(order.get('placed_at'))}</div>
          <div class="po-order-buyer">{buyer_line}</div>
        </div>
        <span class="po-status-badge"
          style="background:{color}18; color:{color}; border:1px solid {color}55;">
          {STATUS_LABELS.get(status, status)}
        </span>
      </div>

      <div class="po-stats-row">
        <div class="po-stat-chip">💰 Total &nbsp;<b>{format_currency(order['total'])}</b></div>
        <div class="po-stat-chip">💳 Payment &nbsp;<b>{order['payment_status'].title()}</b></div>
        <div class="po-stat-chip">📦 Items &nbsp;<b>{len(items)}</b></div>
      </div>

      {'<div class="po-shipping">📍 <b>Ship to:</b> ' + ship_line + '</div>' if ship_line else ''}
      {'<div class="po-notes">📝 ' + order['notes'] + '</div>' if order.get('notes') else ''}
    </div>
    """)

    # Items table (outside HTML block so st.dataframe renders)
    if items:
        with st.expander(f"View {len(items)} item(s)", expanded=False):
            st.dataframe(
                [{"SKU": it["sku"], "Name": it["name"], "Qty": it["quantity"],
                  "Unit Price": format_currency(it["unit_price"]),
                  "Subtotal": format_currency(it["unit_price"] * it["quantity"])} for it in items],
                use_container_width=True, hide_index=True,
            )

    # Action buttons
    if status in NEXT_STATUS:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(ACTION_LABELS[status], key=f"adv_{order['id']}", type="primary", use_container_width=True):
                _advance_order_status(order, producer)
        with col_b:
            if st.button("❌ Cancel Order", key=f"can_{order['id']}", use_container_width=True):
                _cancel_order(order, producer)
    elif status == "delivered":
        st.success("This order has been delivered.")
    elif status == "cancelled":
        st.error("This order was cancelled.")

    # Tracking number + carrier (set when shipping, visible to buyer)
    with st.expander(f"🚚 Update tracking — {order['order_number']}", expanded=False):
        try:
            from utils.tracking_ui import render_seller_tracking_form
            render_seller_tracking_form(order["id"])
        except Exception as e:
            st.caption(f"Tracking unavailable: {e}")


def _advance_order_status(order: dict, producer: dict):
    current     = order["status"]
    next_status = NEXT_STATUS.get(current)
    if not next_status:
        return
    try:
        client         = get_supabase_client()
        update_payload = {"status": next_status}
        if next_status == "confirmed":  update_payload["confirmed_at"] = "now()"
        if next_status == "shipped":    update_payload["shipped_at"]   = "now()"
        if next_status == "delivered":  update_payload["delivered_at"] = "now()"
        client.table("orders").update(update_payload).eq("id", order["id"]).execute()

        try:
            buyer_id = order.get("buyer_id")
            if buyer_id:
                msg = {
                    "pending":    f"Your order {order['order_number']} has been accepted by {producer['full_name']}.",
                    "confirmed":  f"Your order {order['order_number']} is now being processed.",
                    "processing": f"Your order {order['order_number']} has been shipped!",
                    "shipped":    f"Your order {order['order_number']} has been delivered. Enjoy!",
                }.get(current, f"Your order {order['order_number']} status updated to {next_status}.")
                client.table("notifications").insert({
                    "user_id": buyer_id, "sender_id": producer["id"],
                    "title": f"Order Update: {order['order_number']}", "message": msg,
                    "type": "success" if next_status in ("confirmed", "delivered") else "info",
                }).execute()
        except Exception:
            pass

        st.success(f"Order {order['order_number']} → {STATUS_LABELS.get(next_status, next_status)}")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to update order: {e}")


def _cancel_order(order: dict, producer: dict):
    try:
        client = get_supabase_client()
        client.table("orders").update({"status": "cancelled"}).eq("id", order["id"]).execute()
        try:
            buyer_id = order.get("buyer_id")
            if buyer_id:
                client.table("notifications").insert({
                    "user_id": buyer_id, "sender_id": producer["id"],
                    "title": f"Order Cancelled: {order['order_number']}",
                    "message": f"Your order {order['order_number']} has been cancelled by {producer['full_name']}.",
                    "type": "warning",
                }).execute()
        except Exception:
            pass
        st.warning(f"Order {order['order_number']} cancelled.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to cancel order: {e}")
