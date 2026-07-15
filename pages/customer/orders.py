"""Customer order history."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency, format_datetime
from utils.tracking_ui import render_buyer_tracking
from utils.invoice_ui import render_invoice_button


def render_customer_orders():
    page_header("My Orders", "Your purchase history")

    user = get_current_user()
    if not user:
        return

    try:
        client = get_supabase_client()
        orders = (
            client.table("orders")
            .select("*, order_items(*)")
            .eq("buyer_id", user["id"])
            .order("created_at", desc=True)
            .execute()
        ).data or []
    except Exception as e:
        st.error(f"Failed to load orders: {e}")
        return

    if not orders:
        st.info("You haven't placed any orders yet.")
        return

    # Pre-fetch the seller info (one query) for the invoice button
    seller_ids = list({o.get("seller_id") for o in orders if o.get("seller_id")})
    seller_map: dict = {}
    if seller_ids:
        try:
            sellers = (
                client.table("profiles")
                .select("id, full_name, company, email, phone, location")
                .in_("id", seller_ids)
                .execute()
            ).data or []
            for s in sellers:
                seller_map[s["id"]] = s
        except Exception:
            pass

    for o in orders:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.markdown(f"**{o['order_number']}**")
                st.caption(f"Placed {format_datetime(o.get('placed_at'))}")
            with col2:
                st.metric("Total", format_currency(o["total"]))
            with col3:
                st.metric("Status", o["status"].title())
            with col4:
                st.metric("Payment", o["payment_status"].title())

            items = o.get("order_items") or []
            if items:
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

            # Tracking + invoice row
            seller = seller_map.get(o.get("seller_id"), {})
            with st.expander(f"📦 Tracking & invoice — {o['order_number']}", expanded=False):
                render_buyer_tracking(o["id"])
                st.markdown("---")
                render_invoice_button(o, user, seller)
