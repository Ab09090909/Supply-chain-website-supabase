"""
Product Detail page — full product view with producer business card,
order form, agreement preview, and confirm-agreement button.

This is opened from the marketplace when a user clicks "Order" or "View Details".
"""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user, get_current_role
from database.connection import get_supabase_client
from utils.ui import page_header, role_badge
from utils.helpers import format_currency, format_unit, format_datetime, generate_order_number
from utils.constants import (
    UNIT_OPTIONS, PAYMENT_TERMS, ROLE_COLORS,
)


def render_product_detail(product_id: str):
    """Render the full product detail view for a given product_id."""
    page_header("📦 Product Details", "Full information, producer profile, and order form")

    user = get_current_user()
    role = get_current_role()
    if not user:
        st.warning("Please log in to view this page.")
        return

    try:
        client = get_supabase_client()
        # Fetch product + producer info in one call using the FK relationship
        result = (
            client.table("products")
            .select("*, profiles!products_producer_id_fkey(*)")
            .eq("id", product_id)
            .single()
            .execute()
        )
        product = result.data
        if not product:
            st.error("Product not found.")
            return
    except Exception as e:
        st.error(f"Failed to load product: {e}")
        return

    producer = product.get("profiles") or {}

    # ---- Back button ----
    if st.button("← Back to Marketplace", key="back_to_marketplace"):
        st.session_state.pop("view_product_id", None)
        st.session_state["force_nav"] = "marketplace"
        st.rerun()

    # ---- Top: Product image + key info ----
    col_img, col_info = st.columns([1, 2])

    with col_img:
        image_url = product.get("image_url")
        if image_url:
            try:
                st.image(image_url, use_container_width=True)
            except Exception:
                st.markdown("📦 _Image unavailable_")
        else:
            st.markdown(
                "<div style='height:240px; background:#f1f5f9; border-radius:12px; "
                "display:flex; align-items:center; justify-content:center; "
                "font-size:4rem; color:#94a3b8;'>📦</div>",
                unsafe_allow_html=True,
            )

    with col_info:
        st.markdown(f"## {product['name']}")
        st.caption(f"SKU: `{product['sku']}` · Category: {product.get('category', '—')}")
        st.markdown(f"### {format_currency(product['price'])} / {format_unit(product.get('unit'))}")
        st.markdown(f"**Stock available:** {product['stock']} {format_unit(product.get('unit'))}")

        # Quality / Brand / Model row
        col_q, col_b, col_m = st.columns(3)
        with col_q:
            st.metric("Quality Grade", product.get("quality_grade") or "—")
        with col_b:
            st.metric("Brand", product.get("brand") or "—")
        with col_m:
            st.metric("Model", product.get("model") or "—")

        col_o, col_c = st.columns(2)
        with col_o:
            st.metric("Origin", product.get("origin") or "—")
        with col_c:
            certs = product.get("certifications") or []
            st.metric("Certifications", ", ".join(certs) if certs else "—")

        if product.get("description"):
            st.markdown(f"_{product['description']}_")

    st.markdown("---")

    # ---- Producer Business Card ----
    st.markdown("### 👤 Producer Profile")
    _render_producer_business_card(producer)

    # ---- Order Form + Agreement Preview (side by side) ----
    st.markdown("---")
    col_order, col_agreement = st.columns([3, 2])

    with col_order:
        st.markdown("### 🛒 Place an Order")
        _render_order_form(product, producer, user, role)

    with col_agreement:
        st.markdown("### 📜 Producer Agreement Preview")
        _render_agreement_preview(product, producer, user)
        st.markdown("---")
        _render_save_button(product, user)


def _render_producer_business_card(producer: dict):
    """Render the producer as a business card with all their info."""
    if not producer:
        st.info("Producer information unavailable.")
        return

    avatar_url = producer.get("avatar_url")
    role = producer.get("role", "producer")
    color = ROLE_COLORS.get(role, "#10b981")

    # Card header with avatar + name
    if avatar_url:
        avatar_html = (
            f"<img src='{avatar_url}' style='width:64px; height:64px; border-radius:50%;"
            f"object-fit:cover; border:3px solid {color};' />"
        )
    else:
        avatar_html = (
            f"<div style='width:64px; height:64px; border-radius:50%;"
            f"background:{color}; color:white; display:flex; align-items:center;"
            f"justify-content:center; font-weight:700; font-size:1.5rem;'>"
            f"{(producer.get('full_name') or 'P')[0].upper()}</div>"
        )

    st.markdown(
        f"""
        <div style='padding:1.25rem; border-radius:12px; background:#f8fafc;
                    border-left:4px solid {color}; border-top:1px solid #e2e8f0;
                    border-right:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0;
                    margin-bottom:1rem;'>
            <div style='display:flex; align-items:center; gap:1rem;'>
                {avatar_html}
                <div style='flex:1;'>
                    <div style='font-size:1.25rem; font-weight:700; color:#0f172a;'>
                        {producer.get('full_name', 'Unknown Producer')}
                    </div>
                    <div style='color:#64748b; font-size:0.9rem; margin-top:0.15rem;'>
                        {producer.get('company') or 'Independent Producer'}
                    </div>
                    <div style='margin-top:0.4rem;'>{role_badge(role)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Contact + business details grid
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📧 Contact Information**")
        st.markdown(f"• Email: `{producer.get('email', '—')}`")
        st.markdown(f"• Phone: {producer.get('phone', '—') or '—'}")
        st.markdown(f"• Location: {producer.get('location', '—') or '—'}")
        st.markdown(f"• Verified: {'✅ Yes' if producer.get('is_verified') else '❌ No'}")

    with col2:
        st.markdown("**📊 Business Information**")
        st.markdown(f"• Member since: {format_datetime(producer.get('created_at'), '%Y-%m-%d')}")
        st.markdown(f"• Status: {'✅ Active' if producer.get('is_active') else '❌ Inactive'}")
        last_login = producer.get("last_login")
        st.markdown(f"• Last login: {format_datetime(last_login) if last_login else '—'}")


def _render_agreement_preview(product: dict, producer: dict, user: dict):
    """Render a preview of the producer agreement / supply terms."""
    st.markdown(
        f"""
        <div style='padding:1rem; border-radius:8px; background:#fffbeb;
                    border:1px dashed #f59e0b; font-size:0.9rem;'>
        <strong>📋 Supply Agreement Terms</strong><br/>
        <hr style='border-color:#fde68a; margin:0.5rem 0;'/>
        <strong>Producer:</strong> {producer.get('full_name', '—')}<br/>
        <strong>Buyer:</strong> {user.get('full_name', '—')}<br/>
        <strong>Product:</strong> {product.get('name', '—')} ({product.get('sku', '—')})<br/>
        <strong>Unit Price:</strong> {format_currency(product.get('price'))} / {format_unit(product.get('unit'))}<br/>
        <strong>Available Stock:</strong> {product.get('stock', 0)} {format_unit(product.get('unit'))}<br/>
        <strong>Quality Grade:</strong> {product.get('quality_grade') or 'Standard'}<br/>
        <strong>Payment Terms:</strong> Per negotiation (default: Cash on Delivery)<br/>
        <strong>Delivery:</strong> Per negotiation, FOB producer location<br/>
        <hr style='border-color:#fde68a; margin:0.5rem 0;'/>
        <em>By clicking "Confirm Agreement & Place Order" you agree to purchase the
        specified quantity at the listed unit price, subject to producer confirmation.</em>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_save_button(product: dict, user: dict):
    """Render a 'Save / Unsave' button (favorites)."""
    try:
        client = get_supabase_client()
        existing = client.table("favorites").select("id").eq(
            "user_id", user["id"]
        ).eq("product_id", product["id"]).execute().data
        is_saved = len(existing) > 0

        # Also show how many users have saved this product
        all_saves = client.table("favorites").select("user_id").eq(
            "product_id", product["id"]
        ).execute().data or []
        save_count = len(all_saves)

        if is_saved:
            if st.button(f"♥ Saved (by {save_count} users)", use_container_width=True, type="primary"):
                client.table("favorites").delete().eq("user_id", user["id"]).eq(
                    "product_id", product["id"]
                ).execute()
                st.rerun()
        else:
            if st.button(f"♡ Save (saved by {save_count} users)", use_container_width=True):
                client.table("favorites").insert({
                    "user_id": user["id"],
                    "product_id": product["id"],
                }).execute()
                st.rerun()
    except Exception as e:
        st.error(f"Failed to load save state: {e}")


def _render_order_form(product: dict, producer: dict, user: dict, role: str):
    """Render the order placement form with quantity, address, payment terms, notes."""
    with st.form("place_order_form"):
        st.markdown(f"**Unit price:** {format_currency(product['price'])} / {format_unit(product.get('unit'))}")
        st.markdown(f"**Available stock:** {product['stock']}")

        col1, col2 = st.columns(2)
        with col1:
            quantity = st.number_input(
                "Order Quantity *",
                min_value=1,
                max_value=int(product["stock"]) if product["stock"] > 0 else 1,
                value=1,
                step=1,
                help=f"How many {format_unit(product.get('unit'))} do you want to order?",
            )
        with col2:
            payment_terms = st.selectbox(
                "Payment Terms *",
                PAYMENT_TERMS,
                help="When and how you will pay the producer.",
            )

        # Shipping address
        st.markdown("##### Shipping Address")
        col_a, col_b = st.columns(2)
        with col_a:
            ship_name = st.text_input(
                "Recipient Name *",
                value=user.get("full_name", ""),
                help="Who will receive the delivery?",
            )
            ship_street = st.text_input(
                "Street Address *",
                placeholder="e.g. Bole Road, Friendship Building, Apt 4",
                help="Full street address including building/apartment if any.",
            )
        with col_b:
            ship_city = st.text_input(
                "City *",
                placeholder="e.g. Addis Ababa",
                help="City or town for delivery.",
            )
            ship_region = st.text_input(
                "Region / State",
                placeholder="e.g. Oromia, Amhara, Tigray",
                help="Region or state. Optional but recommended for rural areas.",
            )
        col_c, col_d = st.columns(2)
        with col_c:
            ship_country = st.text_input(
                "Country *",
                value="Ethiopia",
                help="Country for delivery.",
            )
        with col_d:
            ship_phone = st.text_input(
                "Delivery Phone *",
                value=user.get("phone", "") or "",
                placeholder="+251 9XX XXX XXX",
                help="Phone number for delivery coordination.",
            )

        notes = st.text_area(
            "Order Notes (optional)",
            placeholder="Any special instructions for the producer...",
            help="Add delivery time preferences, packaging requests, etc.",
        )

        # Live total preview
        subtotal = float(product["price"]) * quantity
        tax = subtotal * 0.15  # 15% VAT in Ethiopia
        shipping = 200.0  # flat ETB for demo
        total = subtotal + tax + shipping

        st.markdown(f"""
        **Order Summary:**
        - Subtotal: {format_currency(subtotal)}
        - VAT (15%): {format_currency(tax)}
        - Shipping: {format_currency(shipping)}
        ### Total: {format_currency(total)}
        """)

        # Confirm checkbox
        confirm = st.checkbox(
            "I have read the producer agreement preview and confirm this order.",
            help="Tick this box to acknowledge the supply terms shown on the right.",
        )

        submitted = st.form_submit_button(
            "✅ Confirm Agreement & Place Order",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not confirm:
                st.error("Please tick the confirmation box to place the order.")
            elif not ship_name or not ship_street or not ship_city or not ship_country:
                st.error("Please fill in all required shipping fields.")
            elif quantity > int(product["stock"]):
                st.error(f"Quantity exceeds available stock ({product['stock']}).")
            else:
                _place_order(
                    product, producer, user, role, quantity, payment_terms,
                    ship_name, ship_street, ship_city, ship_region, ship_country, ship_phone,
                    notes, subtotal, tax, shipping, total
                )


def _place_order(
    product, producer, user, role, quantity, payment_terms,
    ship_name, ship_street, ship_city, ship_region, ship_country, ship_phone,
    notes, subtotal, tax, shipping, total
):
    """Insert the order + order_items + send notification to producer."""
    try:
        client = get_supabase_client()
        order_number = generate_order_number(role.upper()[:4])

        # Create the agreement (status pending)
        agreement_code = f"AGR-{order_number[-12:]}"
        try:
            client.table("agreements").insert({
                "producer_id": producer["id"],
                "merchant_id": user["id"],
                "agreement_code": agreement_code,
                "title": f"Supply Agreement — {product['name']}",
                "terms": (
                    f"Buyer {user['full_name']} agrees to purchase {quantity} "
                    f"{format_unit(product.get('unit'))} of {product['name']} "
                    f"at {format_currency(product['price'])} per unit. "
                    f"Payment: {payment_terms}. Shipping to {ship_city}, {ship_country}."
                ),
                "status": "pending",
            }).execute()
        except Exception:
            pass  # Agreement creation is best-effort

        # Create the order
        new_order = client.table("orders").insert({
            "order_number": order_number,
            "buyer_id": user["id"],
            "buyer_role": role,
            "seller_id": producer["id"],
            "seller_role": "producer",
            "subtotal": subtotal,
            "tax": tax,
            "shipping_cost": shipping,
            "total": total,
            "status": "pending",
            "payment_status": "pending",
            "shipping_address": {
                "name": ship_name,
                "street": ship_street,
                "city": ship_city,
                "region": ship_region,
                "country": ship_country,
                "phone": ship_phone,
            },
            "notes": notes,
        }).execute().data[0]

        # Insert order item
        client.table("order_items").insert({
            "order_id": new_order["id"],
            "product_id": product["id"],
            "sku": product["sku"],
            "name": product["name"],
            "unit_price": float(product["price"]),
            "quantity": quantity,
        }).execute()

        # Notify the producer
        try:
            client.table("notifications").insert({
                "user_id": producer["id"],
                "sender_id": user["id"],
                "title": "New Order Received 🎉",
                "message": (
                    f"You received order {order_number} from {user['full_name']} "
                    f"for {quantity} {format_unit(product.get('unit'))} of {product['name']}. "
                    f"Total: {format_currency(total)}."
                ),
                "type": "success",
                "link": None,
            }).execute()
        except Exception:
            pass

        st.success(f"✅ Order {order_number} placed successfully!")
        st.balloons()
        st.markdown(f"""
        **Order Confirmation:**
        - Order #: `{order_number}`
        - Total: {format_currency(total)}
        - Agreement #: `{agreement_code}` (pending producer confirmation)
        - Delivery to: {ship_name}, {ship_city}, {ship_country}

        The producer has been notified. You'll see updates in your Notifications tab.
        """)

        if st.button("← Back to Marketplace", key="back_after_order"):
            st.session_state.pop("view_product_id", None)
            st.session_state["force_nav"] = "marketplace"
            st.rerun()

    except Exception as e:
        st.error(f"Failed to place order: {e}")
