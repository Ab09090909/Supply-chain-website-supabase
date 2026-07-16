"""
Merchant Requests page — merchants view incoming match requests from producers.

Merchant can:
  • Preview the proposed agreement
  • Confirm the agreement (sets status to 'confirmed')
  • Cancel the request (sets status to 'cancelled')
"""
from __future__ import annotations

import streamlit as st
from uuid import uuid4
import re as _re

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header, role_badge
from utils.helpers import format_currency, format_datetime
from utils.db_health import is_table_available, render_db_health_warning


def render_merchant_requests():
    page_header("📨 Merchant Requests", "Review supply agreement requests from producers")

    user = get_current_user()
    if not user:
        return

    # Check if the merchant_requests table exists
    if not is_table_available("merchant_requests"):
        st.error("❌ The `merchant_requests` table doesn't exist yet.")
        st.info(
            "**To fix this:** Run `supabase/migration_v4.sql` in your Supabase SQL Editor.\n\n"
            "Go to: **Supabase Dashboard → SQL Editor → New Query** → "
            "paste the contents of `supabase/migration_v4.sql` → click **Run**."
        )
        render_db_health_warning()
        return

    try:
        client = get_supabase_client()
        requests = (
            client.table("merchant_requests")
            .select("*, profiles!merchant_requests_producer_id_fkey(full_name, email, company, location, phone, avatar_url, is_verified)")
            .eq("merchant_id", user["id"])
            .order("created_at", desc=True)
            .execute()
        ).data or []
    except Exception as e:
        err = str(e)
        if "PGRST205" in err or "could not find" in err.lower():
            st.error("❌ The `merchant_requests` table doesn't exist yet.")
            st.info(
                "**To fix this:** Run `supabase/migration_v4.sql` in your Supabase SQL Editor.\n\n"
                "Go to: **Supabase Dashboard → SQL Editor → New Query** → "
                "paste the contents of `supabase/migration_v4.sql` → click **Run**."
            )
        else:
            st.error(f"Failed to load requests: {e}")
        return

    if not requests:
        st.info("No merchant requests yet. Producers can send you match requests from their AI Merchant Match tab.")
        return

    # Summary
    pending = [r for r in requests if r["status"] == "pending"]
    confirmed = [r for r in requests if r["status"] == "confirmed"]
    cancelled = [r for r in requests if r["status"] == "cancelled"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("⏳ Pending", len(pending))
    with col2:
        st.metric("✅ Confirmed", len(confirmed))
    with col3:
        st.metric("❌ Cancelled", len(cancelled))

    st.markdown("---")

    # Filter
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "pending", "confirmed", "cancelled"],
        help="Show only requests with a specific status.",
    )

    filtered = [r for r in requests if status_filter == "All" or r["status"] == status_filter]

    for req in filtered:
        _render_request_card(req, user)


def _render_request_card(req: dict, merchant: dict):
    """Render a single merchant request card."""
    producer = req.get("profiles") or {}
    pct = float(req.get("match_percentage") or 0)

    # Status colors
    status_colors = {
        "pending": "#f59e0b",
        "confirmed": "#10b981",
        "cancelled": "#ef4444",
    }
    color = status_colors.get(req["status"], "#64748b")

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 3, 2])

        with col1:
            # Match percentage
            st.markdown(
                f"""
                <div style='text-align:center; padding:0.75rem; border-radius:10px;
                            background:{color}11; border:2px solid {color};'>
                    <div style='font-size:1.5rem; font-weight:700; color:{color};'>{pct}%</div>
                    <div style='font-size:0.7rem; color:{color}; font-weight:600;'>Match</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            # Producer info
            avatar = producer.get("avatar_url")
            if avatar:
                st.markdown(
                    f"<div style='display:flex; align-items:center; gap:0.75rem;'>"
                    f"<img src='{avatar}' style='width:40px; height:40px; border-radius:50%; object-fit:cover;' />"
                    f"<div><strong>{producer.get('full_name', 'Unknown')}</strong> {role_badge('producer')}<br/>"
                    f"<span style='color:#64748b; font-size:0.85rem;'>{producer.get('company') or 'Independent Producer'}</span>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**{producer.get('full_name', 'Unknown')}**  {role_badge('producer')}", unsafe_allow_html=True)
                st.caption(producer.get("company") or "Independent Producer")

            st.caption(f"📍 {producer.get('location', 'Unknown')} · 📧 {producer.get('email', '—')}")
            st.caption(f"📨 Received: {format_datetime(req.get('created_at'))}")
            if req.get("agreement_code"):
                st.caption(f"📋 Agreement: `{req['agreement_code']}`")

        with col3:
            # Status badge
            st.markdown(
                f"<div style='text-align:center; padding:0.5rem; background:{color}11; "
                f"border-radius:8px; border:1px solid {color};'>"
                f"<strong style='color:{color};'>{req['status'].upper()}</strong></div>",
                unsafe_allow_html=True,
            )

        # --- Producer message ---
        if req.get("producer_message"):
            st.markdown("**💬 Message from producer:**")
            st.info(req["producer_message"])

        # --- Agreement preview ---
        with st.expander("📜 Preview Agreement Terms", expanded=False):
            st.markdown(f"""
            <div style='padding:1rem; border-radius:8px; background:#fffbeb;
                        border:1px dashed #f59e0b; font-size:0.9rem;'>
            <strong>📋 Agreement Preview</strong><br/>
            <hr style='border-color:#fde68a; margin:0.5rem 0;'/>
            <strong>Agreement Code:</strong> {req.get('agreement_code', '—')}<br/>
            <strong>Producer:</strong> {producer.get('full_name', '—')}<br/>
            <strong>Merchant:</strong> {merchant.get('full_name', '—')}<br/>
            <strong>Match Score:</strong> {pct}%<br/>
            <strong>Status:</strong> {req['status'].title()}<br/>
            <hr style='border-color:#fde68a; margin:0.5rem 0;'/>
            <strong>Proposed Terms:</strong><br/>
            {req.get('proposed_terms', 'No terms specified.')}
            </div>
            """, unsafe_allow_html=True)

        # --- Details button (show producer profile + their products) ---
        with st.expander("🔍 Details — Producer Profile & Products", expanded=False):
            _render_producer_details(req, producer)

        # --- Actions ---
        if req["status"] == "pending":
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Confirm Agreement", key=f"confirm_{req['id']}", type="primary", use_container_width=True):
                    _confirm_request(req, merchant)
            with col_b:
                if st.button("❌ Cancel", key=f"cancel_req_{req['id']}", use_container_width=True):
                    _cancel_request(req, merchant)
        elif req["status"] == "confirmed":
            st.success("✅ You have confirmed this agreement. The producer has been notified.")
        elif req["status"] == "cancelled":
            st.error("❌ This request was cancelled.")

        st.markdown("---")


def _confirm_request(req: dict, merchant: dict):
    """Confirm a merchant request — creates an order, agreement, and tracking record.

    Flow:
      1. Update the merchant_request status to 'confirmed'
      2. Update the agreement status to 'active'
      3. Create a real `orders` row (the producer supplies this merchant)
         so the same tracking workflow used by buyer → producer works
      4. Create the matching `order_tracking` row in 'confirmed' state
      5. Create a `order_timeline` event "Agreement confirmed"
      6. Notify the producer that the agreement is confirmed and the
         order is now ready to process
    """
    try:
        client = get_supabase_client()

        # 1. Update the request status
        client.table("merchant_requests").update({
            "status": "confirmed",
            "merchant_response": "Agreement confirmed by merchant.",
            "responded_at": "now()",
        }).eq("id", req["id"]).execute()

        # 2. Update the agreement status
        if req.get("agreement_code"):
            try:
                client.table("agreements").update({
                    "status": "active",
                }).eq("agreement_code", req["agreement_code"]).execute()
            except Exception:
                pass

        # 3. Create a real order so the same tracking workflow works
        order_id = None
        try:
            order_number = f"AGR-{req.get('agreement_code', uuid4().hex[:8].upper())}"
            # Try to extract the proposed price from the terms
            price = 0
            try:
                # Look for a number followed by "per unit" in the terms
                m = _re.search(r"Br\s*([\d,]+(?:\.\d+)?)\s*per\s*unit", req.get("proposed_terms", "") or "", _re.IGNORECASE)
                if m:
                    price = float(m.group(1).replace(",", ""))
            except Exception:
                pass
            if not price:
                # Fallback: try the product's listed price
                try:
                    product_id = req.get("product_id")
                    if product_id:
                        p = client.table("products").select("price").eq("id", product_id).maybe_single().execute()
                        if p and p.data:
                            price = float(p.data.get("price") or 0)
                except Exception:
                    pass

            order_payload = {
                "order_number":    order_number,
                "buyer_id":        req["producer_id"],   # producer supplies the merchant → merchant is the "buyer" in this order
                "buyer_role":      "merchant",
                "seller_id":       req["producer_id"],
                "seller_role":     "producer",
                "subtotal":        price,
                "tax":             0,
                "shipping_cost":   0,
                "total":           price,
                "status":          "confirmed",
                "payment_status":  "pending",
                "shipping_address": {"name": merchant.get("full_name", "—"),
                                      "street": "—",
                                      "city": merchant.get("location", "—"),
                                      "country": "Ethiopia",
                                      "phone": merchant.get("phone", "—")},
                "notes":           f"Order from agreement {req.get('agreement_code', '—')}",
            }
            # The producer supplies, the merchant receives. So the producer
            # is the SELLER and the merchant is the BUYER. We swap them.
            order_payload["buyer_id"]  = req["merchant_id"]
            order_payload["seller_id"] = req["producer_id"]
            order_payload["buyer_role"]  = "merchant"
            order_payload["seller_role"] = "producer"

            order_resp = client.table("orders").insert(order_payload).execute()
            if order_resp.data:
                order_id = order_resp.data[0].get("id")
                # If the agreement mentions a specific product, create an
                # order_items row for it so tracking links to the product
                product_id = req.get("product_id")
                if product_id:
                    try:
                        prod = client.table("products").select("sku, name, price, unit").eq("id", product_id).maybe_single().execute()
                        if prod and prod.data:
                            pd = prod.data
                            client.table("order_items").insert({
                                "order_id":   order_id,
                                "product_id": product_id,
                                "sku":        pd.get("sku", "—"),
                                "name":       pd.get("name", "—"),
                                "unit_price": float(pd.get("price") or 0),
                                "quantity":   1,
                            }).execute()
                    except Exception:
                        pass
        except Exception as e:
            # If order creation fails (table missing, RLS, etc.), still
            # the agreement is confirmed — tracking just won't apply.
            print(f"Order creation skipped: {e}")

        # 4. Create the order_tracking row in 'confirmed' state
        if order_id:
            try:
                client.table("order_tracking").insert({
                    "order_id": order_id,
                    "status":   "confirmed",
                    "notes":    f"Order created from agreement {req.get('agreement_code', '—')}",
                }).execute()
            except Exception:
                pass

            # 5. Add a timeline event
            try:
                client.table("order_timeline").insert({
                    "order_id": order_id,
                    "event":     "Agreement confirmed",
                    "description": f"Merchant {merchant.get('full_name', '—')} confirmed agreement {req.get('agreement_code', '—')}.",
                    "actor_id":  merchant["id"],
                }).execute()
            except Exception:
                pass

        # 6. Notify the producer
        try:
            client.table("notifications").insert({
                "user_id": req["producer_id"],
                "sender_id": merchant["id"],
                "title": "✅ Agreement Confirmed!",
                "message": (
                    f"{merchant['full_name']} has confirmed your supply agreement "
                    f"({req.get('agreement_code', '—')}). "
                    + (f"An order has been created — you can now start processing and shipping it."
                       if order_id else
                       "You can now start preparing the delivery.")
                ),
                "type": "success",
            }).execute()
        except Exception:
            pass

        st.success("✅ Agreement confirmed! The producer has been notified.")
        if order_id:
            st.info(
                "📦 An order has been created automatically. Both you and the "
                "producer can now track the shipment from **My Orders** / **Orders**."
            )
        st.rerun()
    except Exception as e:
        st.error(f"Failed to confirm: {e}")


def _cancel_request(req: dict, merchant: dict):
    """Cancel/decline a merchant request."""
    try:
        client = get_supabase_client()
        client.table("merchant_requests").update({
            "status": "cancelled",
            "merchant_response": "Declined by merchant.",
            "responded_at": "now()",
        }).eq("id", req["id"]).execute()

        # Update the agreement status
        if req.get("agreement_code"):
            try:
                client.table("agreements").update({
                    "status": "cancelled",
                }).eq("agreement_code", req["agreement_code"]).execute()
            except Exception:
                pass

        # Notify the producer
        try:
            client.table("notifications").insert({
                "user_id": req["producer_id"],
                "sender_id": merchant["id"],
                "title": "❌ Agreement Declined",
                "message": (
                    f"{merchant['full_name']} has declined your supply agreement "
                    f"({req.get('agreement_code', '—')})."
                ),
                "type": "warning",
            }).execute()
        except Exception:
            pass

        st.info("Request declined. The producer has been notified.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to decline: {e}")


def _render_producer_details(req: dict, producer: dict):
    """Show the producer's full profile + their products.

    This gives the merchant all the context they need to decide whether
    to confirm the agreement: who the producer is, what they sell,
    how much stock they have, and how they've been rated.
    """
    producer_id = req.get("producer_id")
    if not producer_id:
        st.info("Producer info unavailable.")
        return

    # ---- Producer business card ----
    st.markdown("#### 👤 Producer Business Card")

    avatar = producer.get("avatar_url")
    if avatar:
        avatar_html = (
            f"<img src='{avatar}' style='width:64px; height:64px; border-radius:50%; "
            f"object-fit:cover; border:3px solid #10b981;' />"
        )
    else:
        initials = "".join(
            p[0].upper() for p in (producer.get("full_name") or "??").split()[:2]
        )
        avatar_html = (
            f"<div style='width:64px; height:64px; border-radius:50%; "
            f"background:linear-gradient(135deg,#10b981 0%,#059669 100%); "
            f"display:flex; align-items:center; justify-content:center; "
            f"color:#fff; font-weight:700; font-size:1.4rem;'>{initials}</div>"
        )

    is_verified = "✅ Verified" if producer.get("is_verified") else "❌ Not verified"

    st.markdown(
        f"""
        <div style='padding:1.25rem; border-radius:12px; background:#f8fafc;
                    border-left:4px solid #10b981; border:1px solid #e2e8f0;
                    margin-bottom:1rem;'>
            <div style='display:flex; align-items:center; gap:1rem;'>
                {avatar_html}
                <div style='flex:1;'>
                    <div style='font-size:1.2rem; font-weight:700; color:#0f172a;'>
                        {producer.get('full_name', 'Unknown Producer')}
                    </div>
                    <div style='color:#64748b; font-size:0.9rem; margin-top:0.15rem;'>
                        {producer.get('company') or 'Independent Producer'}
                    </div>
                    <div style='margin-top:0.4rem; color:#10b981; font-weight:600; font-size:0.85rem;'>
                        {is_verified}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Contact + business details grid
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📧 Contact Information**")
        st.markdown(f"• Email: `{producer.get('email', '—')}`")
        st.markdown(f"• Phone: {producer.get('phone', '—') or '—'}")
        st.markdown(f"• Location: {producer.get('location', '—') or '—'}")
    with c2:
        st.markdown("**📊 Business Information**")
        joined = producer.get("created_at", "")
        joined_str = format_datetime(joined, "%Y-%m-%d") if joined else "—"
        st.markdown(f"• Member since: {joined_str}")
        is_active = "✅ Active" if producer.get("is_active", True) else "❌ Inactive"
        st.markdown(f"• Status: {is_active}")

    # ---- Producer's products ----
    st.markdown("---")
    st.markdown("#### 🛒 Producer's Products")
    try:
        client = get_supabase_client()
        products = (
            client.table("products")
            .select("id, name, sku, category, price, stock, unit, status, image_url, "
                    "quality_grade, brand, origin, avg_rating, review_count")
            .eq("producer_id", producer_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        ).data or []

        if not products:
            st.info("This producer has no active products yet.")
        else:
            st.caption(f"Showing {len(products)} active product(s)")

            # Build product cards
            for p in products:
                _render_product_card_in_details(p)

            # Aggregate stats
            total_stock = sum(int(p.get("stock", 0) or 0) for p in products)
            total_value = sum(
                float(p.get("price", 0) or 0) * int(p.get("stock", 0) or 0)
                for p in products
            )
            avg_rating = (
                sum(float(p.get("avg_rating", 0) or 0) for p in products if p.get("avg_rating"))
                / max(sum(1 for p in products if p.get("avg_rating")), 1)
            )
            rating_label = "⭐ Avg rating" if avg_rating else "⭐ No ratings yet"
            rating_value = f"{avg_rating:.2f}" if avg_rating else "—"

            st.markdown("---")
            st.markdown("#### 📊 Portfolio Summary")

            # Build the same beautiful KPI card style used at the top of the page
            # (green icon + label + big number, white card with subtle border).
            # Use double-quoted attributes to avoid any escaping issues with
            # nested f-strings, and concatenate pre-rendered HTML strings
            # (no nested f-string braces).
            card_style = (
                "background:#fff; border:1px solid #e2e8f0; border-radius:12px; "
                "padding:14px 16px; text-align:center; "
                "box-shadow:0 1px 3px rgba(0,0,0,0.04);"
            )
            label_style = (
                "font-size:0.7rem; font-weight:700; letter-spacing:0.09em; "
                "text-transform:uppercase; color:#6b7280; margin-bottom:6px;"
            )
            value_style = (
                "font-size:1.6rem; font-weight:800; color:#047857; line-height:1;"
            )

            active_products_value = str(len(products))
            total_stock_value = f"{total_stock:,}"
            inventory_value_text = format_currency(total_value)

            cards = [
                f'<div style="{card_style}"><div style="{label_style}">🛒 Active products</div>'
                f'<div style="{value_style}">{active_products_value}</div></div>',
                f'<div style="{card_style}"><div style="{label_style}">📦 Total stock</div>'
                f'<div style="{value_style}">{total_stock_value}</div></div>',
                f'<div style="{card_style}"><div style="{label_style}">💰 Inventory value</div>'
                f'<div style="{value_style}">{inventory_value_text}</div></div>',
                f'<div style="{card_style}"><div style="{label_style}">{rating_label}</div>'
                f'<div style="{value_style}">{rating_value}</div></div>',
            ]
            kpi_cards = "".join(cards)
            st.markdown(
                f'<div style="display:flex; gap:12px; flex-wrap:wrap;">{kpi_cards}</div>',
                unsafe_allow_html=True,
            )

    except Exception as e:
        st.warning(f"Could not load producer's products: {e}")


def _render_product_card_in_details(p: dict):
    """Render a small product card inside the Details expander."""
    name    = p.get("name", "—")
    sku     = p.get("sku", "—")
    price   = p.get("price", 0)
    stock   = p.get("stock", 0)
    unit    = p.get("unit", "unit")
    cat     = p.get("category", "Other")
    qg      = p.get("quality_grade")
    brand   = p.get("brand")
    origin  = p.get("origin")
    rating  = p.get("avg_rating")
    reviews = p.get("review_count", 0)
    img     = p.get("image_url")

    # Stock status
    if stock == 0:
        stock_badge = "<span style='background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:600;'>Out of stock</span>"
    elif stock < 20:
        stock_badge = f"<span style='background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:600;'>Low: {stock}</span>"
    else:
        stock_badge = f"<span style='background:#dcfce7; color:#166534; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:600;'>In stock: {stock}</span>"

    img_html = (
        f"<img src='{img}' style='width:60px; height:60px; border-radius:8px; object-fit:cover;' />"
        if img
        else "<div style='width:60px; height:60px; border-radius:8px; background:#f1f5f9; display:flex; align-items:center; justify-content:center; font-size:1.5rem;'>📦</div>"
    )

    # Meta line
    meta_parts = [f"🏷️ {cat}"]
    if qg:    meta_parts.append(f"⭐ {qg}")
    if brand: meta_parts.append(f"🏢 {brand}")
    if origin: meta_parts.append(f"📍 {origin}")
    meta_html = " &nbsp;·&nbsp; ".join(meta_parts)

    # Rating
    rating_html = ""
    if rating and reviews:
        rating_html = f"&nbsp;&nbsp;⭐ <b>{rating:.1f}</b> ({reviews})"
    elif reviews:
        rating_html = f"&nbsp;&nbsp;⭐ — ({reviews} reviews)"

    st.markdown(
        f"""
        <div style='display:flex; gap:14px; padding:12px; margin-bottom:8px;
                    background:#fff; border:1px solid #e2e8f0; border-radius:10px;
                    align-items:center;'>
            <div>{img_html}</div>
            <div style='flex:1; min-width:0;'>
                <div style='font-size:0.95rem; font-weight:700; color:#0f172a;
                            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>
                    {name}
                </div>
                <div style='font-size:0.75rem; color:#64748b; margin-top:2px;'>
                    SKU: <code>{sku}</code>{rating_html}
                </div>
                <div style='font-size:0.72rem; color:#94a3b8; margin-top:2px;'>
                    {meta_html}
                </div>
            </div>
            <div style='text-align:right; min-width:120px;'>
                <div style='font-size:1rem; font-weight:800; color:#047857;'>
                    {format_currency(price)}
                </div>
                <div style='font-size:0.7rem; color:#64748b;'>/ {unit}</div>
                <div style='margin-top:4px;'>{stock_badge}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
