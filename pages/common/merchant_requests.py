"""
Merchant Requests page — merchants view incoming match requests from producers.

Merchant can:
  • Preview the proposed agreement
  • Confirm the agreement (sets status to 'confirmed')
  • Cancel the request (sets status to 'cancelled')
"""
from __future__ import annotations

import streamlit as st

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
    """Confirm a merchant request."""
    try:
        client = get_supabase_client()
        # Update the request status
        client.table("merchant_requests").update({
            "status": "confirmed",
            "merchant_response": "Agreement confirmed by merchant.",
            "responded_at": "now()",
        }).eq("id", req["id"]).execute()

        # Update the agreement status if it exists
        if req.get("agreement_code"):
            try:
                client.table("agreements").update({
                    "status": "active",
                }).eq("agreement_code", req["agreement_code"]).execute()
            except Exception:
                pass

        # Notify the producer
        try:
            client.table("notifications").insert({
                "user_id": req["producer_id"],
                "sender_id": merchant["id"],
                "title": "✅ Agreement Confirmed!",
                "message": (
                    f"{merchant['full_name']} has confirmed your supply agreement "
                    f"({req.get('agreement_code', '—')}). You can now start processing orders!"
                ),
                "type": "success",
            }).execute()
        except Exception:
            pass

        st.success("✅ Agreement confirmed! The producer has been notified.")
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

            st.markdown("---")
            st.markdown("**📊 Portfolio Summary**")
            sm1, sm2, sm3, sm4 = st.columns(4)
            with sm1:
                st.metric("🛒 Active products", len(products))
            with sm2:
                st.metric("📦 Total stock", f"{total_stock:,}")
            with sm3:
                st.metric("💰 Inventory value", format_currency(total_value))
            with sm4:
                st.metric(f"{'⭐ Avg rating' if avg_rating else '⭐ No ratings yet'}",
                          f"{avg_rating:.2f}" if avg_rating else "—")

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
