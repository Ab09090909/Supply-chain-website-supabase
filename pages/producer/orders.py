"""Producer orders view — with Accept/Confirm, Ship, and Deliver buttons."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency, format_datetime


# Order status flow:
#   pending → confirmed → processing → shipped → delivered
#   (any of these can go to → cancelled)
NEXT_STATUS = {
    "pending": "confirmed",
    "confirmed": "processing",
    "processing": "shipped",
    "shipped": "delivered",
}

STATUS_LABELS = {
    "pending": "⏳ Pending",
    "confirmed": "✅ Confirmed",
    "processing": "🔄 Processing",
    "shipped": "🚚 Shipped",
    "delivered": "📦 Delivered",
    "cancelled": "❌ Cancelled",
}

STATUS_COLORS = {
    "pending": "#f59e0b",
    "confirmed": "#10b981",
    "processing": "#3b82f6",
    "shipped": "#8b5cf6",
    "delivered": "#059669",
    "cancelled": "#ef4444",
}

ACTION_LABELS = {
    "pending": "✅ Accept Order",
    "confirmed": "🔄 Start Processing",
    "processing": "🚚 Mark as Shipped",
    "shipped": "📦 Mark as Delivered",
}


def render_producer_orders():
    page_header("Orders", "View and manage orders from your buyers")

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
        st.info("No orders yet. Once buyers place orders on your products, they'll appear here.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pending = sum(1 for o in orders if o["status"] == "pending")
        st.metric("⏳ Pending", pending)
    with col2:
        active = sum(1 for o in orders if o["status"] in ("confirmed", "processing"))
        st.metric("🔄 Active", active)
    with col3:
        shipped = sum(1 for o in orders if o["status"] == "shipped")
        st.metric("🚚 Shipped", shipped)
    with col4:
        delivered = sum(1 for o in orders if o["status"] == "delivered")
        st.metric("📦 Delivered", delivered)

    st.markdown("---")

    # Filter
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "pending", "confirmed", "processing", "shipped", "delivered", "cancelled"],
        help="Show only orders with a specific status.",
    )

    filtered = [o for o in orders if status_filter == "All" or o["status"] == status_filter]

    for o in filtered:
        _render_order_card(o, user)


def _render_order_card(order: dict, producer: dict):
    """Render a single order card with action buttons."""
    status = order["status"]
    color = STATUS_COLORS.get(status, "#64748b")
    buyer = order.get("buyer") or {}

    with st.container(border=True):
        # Header row
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            st.markdown(f"**{order['order_number']}**")
            st.caption(f"Placed {format_datetime(order.get('placed_at'))}")
            if buyer:
                st.caption(f"👤 Buyer: {buyer.get('full_name', '—')} · 📧 {buyer.get('email', '—')}")
                if buyer.get("phone"):
                    st.caption(f"📞 {buyer['phone']}")
        with col2:
            st.metric("Total", format_currency(order["total"]))
        with col3:
            st.metric("Payment", order["payment_status"].title())
        with col4:
            st.markdown(
                f"<div style='text-align:center; padding:0.4rem; background:{color}11; "
                f"border-radius:6px; border:1px solid {color};'>"
                f"<strong style='color:{color};'>{STATUS_LABELS.get(status, status)}</strong></div>",
                unsafe_allow_html=True,
            )

        # Order items
        items = order.get("order_items") or []
        if items:
            st.markdown("**Items:**")
            st.dataframe([
                {
                    "SKU": it["sku"],
                    "Name": it["name"],
                    "Qty": it["quantity"],
                    "Unit Price": format_currency(it["unit_price"]),
                    "Subtotal": format_currency(it["subtotal"]),
                }
                for it in items
            ], use_container_width=True, hide_index=True)

        # Shipping address
        ship = order.get("shipping_address") or {}
        if ship:
            st.markdown(f"""
            **Shipping Address:**
            {ship.get('name', '—')} · {ship.get('phone', '—')}
            {ship.get('street', '—')}, {ship.get('city', '—')}
            {ship.get('region', '')} {ship.get('country', '')}
            """)

        # Notes
        if order.get("notes"):
            st.markdown(f"**Notes:** {order['notes']}")

        # Action buttons (outside any form, so st.button works)
        if status in NEXT_STATUS:
            col_a, col_b = st.columns([1, 1])
            with col_a:
                if st.button(
                    ACTION_LABELS[status],
                    key=f"advance_{order['id']}",
                    type="primary",
                    use_container_width=True,
                ):
                    _advance_order_status(order, producer)
            with col_b:
                if st.button(
                    "❌ Cancel Order",
                    key=f"cancel_{order['id']}",
                    use_container_width=True,
                ):
                    _cancel_order(order, producer)
        elif status == "delivered":
            st.success("✅ This order has been delivered.")
        elif status == "cancelled":
            st.error("❌ This order was cancelled.")

        st.markdown("---")


def _advance_order_status(order: dict, producer: dict):
    """Move the order to its next status in the pipeline."""
    current = order["status"]
    next_status = NEXT_STATUS.get(current)
    if not next_status:
        return

    try:
        client = get_supabase_client()
        update_payload = {"status": next_status}
        # Update timestamps based on the new status
        if next_status == "confirmed":
            update_payload["confirmed_at"] = "now()"
        elif next_status == "shipped":
            update_payload["shipped_at"] = "now()"
        elif next_status == "delivered":
            update_payload["delivered_at"] = "now()"

        client.table("orders").update(update_payload).eq("id", order["id"]).execute()

        # Notify the buyer
        try:
            buyer_id = order.get("buyer_id")
            if buyer_id:
                notif_msg = {
                    "pending": f"Your order {order['order_number']} has been accepted by {producer['full_name']}.",
                    "confirmed": f"Your order {order['order_number']} is now being processed.",
                    "processing": f"Your order {order['order_number']} has been shipped!",
                    "shipped": f"Your order {order['order_number']} has been delivered. Enjoy!",
                }.get(current, f"Your order {order['order_number']} status updated to {next_status}.")

                notif_type = "success" if next_status in ("confirmed", "delivered") else "info"
                client.table("notifications").insert({
                    "user_id": buyer_id,
                    "sender_id": producer["id"],
                    "title": f"Order Update: {order['order_number']}",
                    "message": notif_msg,
                    "type": notif_type,
                }).execute()
        except Exception:
            pass

        st.success(f"Order {order['order_number']} → {STATUS_LABELS.get(next_status, next_status)}")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to update order: {e}")


def _cancel_order(order: dict, producer: dict):
    """Cancel the order."""
    try:
        client = get_supabase_client()
        client.table("orders").update({"status": "cancelled"}).eq("id", order["id"]).execute()

        # Notify the buyer
        try:
            buyer_id = order.get("buyer_id")
            if buyer_id:
                client.table("notifications").insert({
                    "user_id": buyer_id,
                    "sender_id": producer["id"],
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
