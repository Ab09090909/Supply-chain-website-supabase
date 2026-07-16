"""Merchant orders page."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency, format_datetime
from utils.tracking import get_tracking, get_timeline
from utils.reviews_ui import render_order_rating_widget


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

    # Pre-fetch the product info once so each order's rating widget can
    # show the product name + image without N extra queries per order.
    product_ids = list({
        it.get("product_id")
        for o in orders
        for it in (o.get("order_items") or [])
        if it.get("product_id")
    })
    product_map: dict = {}
    if product_ids:
        try:
            prods = (
                client.table("products")
                .select("id, name, sku, image_url, avg_rating, review_count")
                .in_("id", product_ids)
                .execute()
            ).data or []
            for p in prods:
                product_map[p["id"]] = p
        except Exception:
            pass

    for o in orders:
        # Status colors
        status_colors = {
            "pending":    "#f59e0b",
            "confirmed":  "#10b981",
            "processing": "#3b82f6",
            "shipped":    "#8b5cf6",
            "delivered":  "#059669",
            "cancelled":  "#ef4444",
        }
        status = o["status"]
        color  = status_colors.get(status, "#64748b")

        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(
                    f"<div style='font-size:0.95rem; font-weight:700;'>"
                    f"🛒 {o['order_number']}"
                    f"<span style='background:{color}22; color:{color}; "
                    f"padding:2px 10px; border-radius:20px; font-size:0.72rem; "
                    f"font-weight:700; margin-left:8px;'>{status.upper()}</span>"
                    f"</div>"
                    f"<div style='font-size:0.76rem; color:#94a3b8; margin-top:4px;'>"
                    f"Placed {format_datetime(o.get('placed_at'))}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col2:
                st.metric("Total", format_currency(o["total"]))
            with col3:
                st.metric("Items", len(o.get("order_items") or []))

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

            # Inline tracking widget — shows the merchant the current
            # shipment status without making them navigate away.
            with st.expander("📦 Track this order", expanded=(status in ("shipped", "delivered"))):
                tracking = get_tracking(o["id"])
                timeline = get_timeline(o["id"])

                if not tracking and not timeline:
                    st.caption("Tracking isn't available yet. The producer will update it soon.")
                else:
                    if tracking:
                        tn   = tracking.get("tracking_number") or "—"
                        cr   = tracking.get("carrier") or "—"
                        eta  = tracking.get("estimated_delivery") or "—"
                        st.markdown(
                            f"<div style='background:#f0fdf4; border:1px solid #bbf7d0; "
                            f"border-radius:10px; padding:12px 14px; margin:6px 0;'>"
                            f"<div style='font-size:0.85rem; color:#166534; font-weight:600;'>"
                            f"🚚 Tracking #{tn} &nbsp;·&nbsp; 📦 {cr} &nbsp;·&nbsp; 🗓️ ETA {eta}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    if timeline:
                        st.markdown("##### 📜 Timeline")
                        for ev in timeline:
                            actor = (ev.get("profiles") or {}).get("full_name", "System")
                            ts = (ev.get("created_at") or "")[:19]
                            desc = ev.get("description") or ""
                            st.markdown(
                                f"- **{ev.get('event', '')}** — {desc}  \n"
                                f"  <small style='color:#64748b;'>{ts} · by {actor}</small>",
                                unsafe_allow_html=True,
                            )

            # Once the order is delivered, merchants can also rate the
            # products they bought (verified-buyer review, same as customers).
            if status == "delivered":
                with st.expander(
                    f"⭐ Rate products in this order ({len(items)})",
                    expanded=False,
                ):
                    st.caption(
                        "Your rating is linked to this order so the producer "
                        "knows it's from a verified merchant customer."
                    )
                    for it in items:
                        product = product_map.get(it.get("product_id")) if it.get("product_id") else None
                        render_order_rating_widget(o, it, product, user)
