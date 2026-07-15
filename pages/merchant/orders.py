"""Merchant orders page."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency, format_datetime


def render_merchant_orders():
    page_header("My Orders", "Orders you've placed with producers")

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

    for o in orders:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**{o['order_number']}**")
                st.caption(f"Placed {format_datetime(o.get('placed_at'))}")
            with col2:
                st.metric("Total", format_currency(o["total"]))
            with col3:
                st.metric("Status", o["status"].title())

            items = o.get("order_items") or []
            if items:
                st.dataframe([
                    {
                        "SKU": it["sku"],
                        "Name": it["name"],
                        "Qty": it["quantity"],
                        "Unit Price": format_currency(it["unit_price"]),
                        "Subtotal": format_currency(it["unit_price"] * it["quantity"]),
                    }
                    for it in items
                ], use_container_width=True, hide_index=True)
