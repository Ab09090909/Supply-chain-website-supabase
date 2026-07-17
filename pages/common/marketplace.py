"""
Shared Marketplace — visible to ALL roles.

Each product card shows:
  - Product image
  - Name, SKU, category, price (ETB)
  - Star rating + review count
  - "Saved by N users" indicator
  - "Order" / "View Details" button → opens full product detail page
  - "Save" / "♥ Saved" button (favorites)
  - "Contact" button → opens a direct-message form to the producer
"""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user, get_current_role
from database.connection import get_supabase_client
from utils.ui import page_header, role_badge
from utils.helpers import format_currency, format_unit
from utils.constants import PRODUCT_CATEGORIES
from utils.search import filter_products
from utils.search_ui import render_search_filter_bar
from utils.reviews_ui import render_product_card_stars


def render_shared_marketplace():
    page_header("Marketplace", "Browse all products from every producer on the platform")

    user = get_current_user()
    role = get_current_role()
    if not user:
        return

    # If user clicked "Order" / "View Details" on a product, render the detail page instead
    if st.session_state.get("view_product_id"):
        from .product_detail import render_product_detail
        render_product_detail(st.session_state["view_product_id"])
        return

    try:
        client = get_supabase_client()
        products = (
            client.table("products")
            .select("*, profiles!products_producer_id_fkey(id, full_name, email, role, avatar_url, phone, company)")
            .eq("status", "active")
            .order("created_at", desc=True)
            .execute()
        ).data or []

        favorites = (
            client.table("favorites")
            .select("product_id")
            .eq("user_id", user["id"])
            .execute()
        ).data or []
        fav_ids = {f["product_id"] for f in favorites}

        # Fetch save counts per product (how many users saved each)
        all_favs = (
            client.table("favorites")
            .select("product_id")
            .execute()
        ).data or []
        save_counts: dict = {}
        for f in all_favs:
            pid = f.get("product_id")
            if pid:
                save_counts[pid] = save_counts.get(pid, 0) + 1
    except Exception as e:
        st.error(f"Failed to load marketplace: {e}")
        return

    if not products:
        st.info("No products available yet. Be the first to add one!")
        return

    # Filters (search bar + price range + category + sort + rating + stock)
    filters = render_search_filter_bar(
        categories=PRODUCT_CATEGORIES,
        show_rating_filter=True,
        show_in_stock=True,
        key_prefix="mp",
    )

    # Apply filters
    filtered = filter_products(
        products,
        query=filters["query"],
        category=filters["category"],
        min_price=filters["min_price"],
        max_price=filters["max_price"],
        min_rating=filters["min_rating"],
        in_stock_only=filters["in_stock_only"],
        sort_by=filters["sort_by"],
    )

    st.markdown(f"###### {len(filtered)} product(s) found")

    # Grid of product cards — clean card design without Streamlit border
    cols = st.columns(3)
    for i, p in enumerate(filtered):
        with cols[i % 3]:
            # Build card HTML (image, meta, price)
            image_url = p.get("image_url")
            if image_url:
                img_html = (
                    f"<div style='height:280px; overflow:hidden; border-radius:10px 10px 0 0; margin:-1rem -1rem 0.75rem -1rem; "
                    f"position:relative;'>"
                    f"<img src='{image_url}' style='width:100%; height:100%; object-fit:contain; background:#f8fafc; transition:transform 0.4s ease;' "
                    f"onmouseover=\"this.style.transform='scale(1.06)'\" onmouseout=\"this.style.transform='scale(1)'\" />"
                    f"<div style='position:absolute; inset:0; "
                    f"background:linear-gradient(180deg, transparent 60%, rgba(0,0,0,0.35) 100%); pointer-events:none;'></div>"
                    f"</div>"
                )
            else:
                img_html = (
                    "<div style='height:280px; background:linear-gradient(135deg,#a7f3d0 0%, #6ee7b7 50%, #34d399 100%); "
                    "background-size:200% 200%; animation:gradientShift 8s ease infinite; "
                    "border-radius:10px 10px 0 0; margin:-1rem -1rem 0.75rem -1rem; "
                    "display:flex; align-items:center; justify-content:center; font-size:4.5rem; "
                    "box-shadow: inset 0 0 30px rgba(255,255,255,0.3);'>📦</div>"
                )

            producer = p.get("profiles") or {}
            badges = ""
            if p.get("quality_grade") or p.get("brand"):
                parts = []
                if p.get("quality_grade"):
                    parts.append(f"<span style='background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:10px; font-weight:600;'>⭐ {p['quality_grade']}</span>")
                if p.get("brand"):
                    parts.append(f"<span style='background:#ede9fe; color:#5b21b6; padding:2px 8px; border-radius:10px; font-weight:600;'>🏷️ {p['brand']}</span>")
                badges = f"<div style='font-size:0.68rem; margin:0.3rem 0; display:flex; gap:4px; flex-wrap:wrap;'>{' '.join(parts)}</div>"

            st.markdown(
                f"""
                <div style='
                    background:#fff; border:1px solid #e8edf2; border-radius:14px;
                    padding:1rem; box-shadow:0 2px 10px rgba(0,0,0,0.05);
                    transition:transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
                    margin-bottom:0.25rem; position:relative; overflow:hidden;
                    animation: fadeInUp 0.4s ease-out backwards;
                '
                onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 12px 28px rgba(16,185,129,0.15)';this.style.borderColor='#a7f3d0';"
                onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 2px 10px rgba(0,0,0,0.05)';this.style.borderColor='#e8edf2';">
                    {img_html}
                    <div style='font-size:0.92rem; font-weight:700; color:#0f172a; line-height:1.35; margin-bottom:0.15rem;'>{p['name']}</div>
                    <div style='font-size:0.72rem; color:#94a3b8; margin-bottom:0.2rem;'>
                        by <span style='color:#10b981; font-weight:600;'>{producer.get('full_name','Unknown')}</span>
                        &nbsp;·&nbsp; {p.get('category','Other')}
                    </div>
                    {badges}
                    <div style='display:flex; align-items:baseline; gap:6px; margin:0.4rem 0 0.1rem 0;'>
                        <div style='font-size:1.25rem; font-weight:800;
                                    background:linear-gradient(135deg, #047857 0%, #10b981 100%);
                                    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                                    background-clip:text;'>{format_currency(p['price'])}</div>
                    </div>
                    <div style='font-size:0.7rem; color:#94a3b8; display:flex; gap:10px; align-items:center;'>
                        <span>📦 {p['stock']} {format_unit(p.get('unit'))}</span>
                        <span>💖 {save_counts.get(p['id'],0)} saved</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Star rating (shown even if no reviews — "No ratings yet" hint)
            render_product_card_stars(p)

            # Action buttons below the card
            col_a, col_b = st.columns(2)
            with col_a:
                if p["id"] in fav_ids:
                    if st.button("♥ Saved", key=f"unfav_{p['id']}", use_container_width=True):
                        try:
                            client.table("favorites").delete().eq(
                                "user_id", user["id"]
                            ).eq("product_id", p["id"]).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
                else:
                    if st.button("♡ Save", key=f"fav_{p['id']}", use_container_width=True):
                        try:
                            client.table("favorites").insert({
                                "user_id": user["id"],
                                "product_id": p["id"],
                            }).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
            with col_b:
                if st.button("🛒 Order", key=f"order_{p['id']}", use_container_width=True, type="primary"):
                    st.session_state["view_product_id"] = p["id"]
                    st.rerun()

            if st.button("💬 Contact Producer", key=f"contact_{p['id']}", use_container_width=True):
                st.session_state["pending_message_to"] = producer.get("id")
                st.session_state["pending_message_to_name"] = producer.get("full_name")
                st.session_state["pending_message_subject"] = f"Inquiry: {p['name']}"

                # Pre-fill the message body with producer's phone and product info
                producer_phone = producer.get("phone") or "Not provided"
                producer_email = producer.get("email") or "Not provided"
                producer_company = producer.get("company") or "Independent Producer"
                pre_filled_body = (
                    f"Hello {producer.get('full_name', 'there')},\n\n"
                    f"I'm interested in your product: {p['name']} (SKU: {p['sku']}).\n\n"
                    f"Producer contact information:\n"
                    f"- Phone: {producer_phone}\n"
                    f"- Email: {producer_email}\n"
                    f"- Company: {producer_company}\n\n"
                    f"Could you please provide more details about availability and delivery?\n\n"
                    f"Thank you."
                )
                st.session_state["pending_message_body"] = pre_filled_body
                st.session_state["force_nav"] = "notifications"
                st.rerun()
