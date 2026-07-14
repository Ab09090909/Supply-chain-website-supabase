"""Customer shopping cart."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency, generate_order_number


def render_customer_cart():
    page_header("Shopping Cart", "Review items and place your order")

    user = get_current_user()
    if not user:
        return

    client = get_supabase_client()

    try:
        cart_items = (
            client.table("cart_items")
            .select("*, products(*)")
            .eq("user_id", user["id"])
            .execute()
        ).data or []
    except Exception as e:
        st.error(f"Failed to load cart: {e}")
        return

    if not cart_items:
        st.info("🛒 Your cart is empty. Browse the marketplace to add products!")
        return

    subtotal = 0.0
    for item in cart_items:
        product = item.get("products") or {}
        price = float(product.get("price", 0))
        line_total = price * item["quantity"]
        subtotal += line_total

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.markdown(f"**{product.get('name', '—')}**")
                st.caption(f"SKU: {product.get('sku', '—')}")
            with col2:
                st.metric("Price", format_currency(price))
            with col3:
                st.metric("Qty", item["quantity"])
            with col4:
                st.metric("Subtotal", format_currency(line_total))
                if st.button("Remove", key=f"rm_{item['id']}"):
                    client.table("cart_items").delete().eq("id", item["id"]).execute()
                    st.rerun()

    st.markdown("---")
    tax = subtotal * 0.15  # 15% VAT (Ethiopia)
    shipping = 200.0 if subtotal < 5000 else 0.0  # ETB
    total = subtotal + tax + shipping

    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown(f"**Subtotal:** {format_currency(subtotal)}")
        st.markdown(f"**Tax (8%):** {format_currency(tax)}")
        st.markdown(f"**Shipping:** {format_currency(shipping)}")
        st.markdown(f"### Total: {format_currency(total)}")

        if st.button("Place Order", type="primary", use_container_width=True):
            try:
                # Use first product's producer as the seller (simplified)
                first_product = cart_items[0]["products"]
                seller_id = first_product["producer_id"]

                order_number = generate_order_number("CUST")

                order_payload = {
                    "order_number": order_number,
                    "buyer_id": user["id"],
                    "buyer_role": "customer",
                    "seller_id": seller_id,
                    "seller_role": "producer",
                    "subtotal": subtotal,
                    "tax": tax,
                    "shipping_cost": shipping,
                    "total": total,
                    "status": "pending",
                    "payment_status": "pending",
                    "shipping_address": {"name": user["full_name"], "city": user.get("location", "")},
                }
                insert_response = client.table("orders").insert(order_payload).execute()
                inserted_data = insert_response.data or []

                # Get the order id reliably
                if inserted_data and isinstance(inserted_data, list) and len(inserted_data) > 0:
                    new_order = inserted_data[0]
                else:
                    fetched = (
                        client.table("orders")
                        .select("id")
                        .eq("order_number", order_number)
                        .maybe_single()
                        .execute()
                    )
                    new_order = fetched.data if (fetched and fetched.data) else None

                # Insert order items (only if we have the order id)
                if new_order and new_order.get("id"):
                    items_to_insert = [
                        {
                            "order_id": new_order["id"],
                            "product_id": item["product_id"],
                            "sku": item["products"]["sku"],
                            "name": item["products"]["name"],
                            "unit_price": float(item["products"]["price"]),
                            "quantity": item["quantity"],
                        }
                        for item in cart_items
                    ]
                    try:
                        client.table("order_items").insert(items_to_insert).execute()
                    except Exception:
                        pass

                # Clear cart
                client.table("cart_items").delete().eq("user_id", user["id"]).execute()

                st.success(f"Order {order_number} placed successfully!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Failed to place order: {e}")
