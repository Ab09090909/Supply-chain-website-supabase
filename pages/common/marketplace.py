"""
Shared Marketplace — visible to ALL roles.

Each product card shows:
  - Product image
  - Name, SKU, category, price (ETB)
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
            .select("*, profiles!products_producer_id_fkey(full_name, email, role, avatar_url)")
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

    # Filters with helpful labels
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        search = st.text_input(
            "🔍 Search products",
            placeholder="Try 'milk', 'avocado', 'organic'...",
            help="Search across product name and description. Case-insensitive.",
        )
    with col2:
        categories = ["All"] + PRODUCT_CATEGORIES
        category = st.selectbox(
            "Filter by Category",
            categories,
            help="Show only products in a specific category, or all.",
        )
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Newest", "Price: Low → High", "Price: High → Low", "Stock: High → Low", "Most Saved"],
            help="Choose how to order products in the grid.",
        )

    filtered = [
        p for p in products
        if (not search or search.lower() in p["name"].lower() or search.lower() in p.get("description", "").lower())
        and (category == "All" or p.get("category") == category)
    ]

    if sort_by == "Price: Low → High":
        filtered.sort(key=lambda x: float(x.get("price", 0)))
    elif sort_by == "Price: High → Low":
        filtered.sort(key=lambda x: float(x.get("price", 0)), reverse=True)
    elif sort_by == "Stock: High → Low":
        filtered.sort(key=lambda x: int(x.get("stock", 0)), reverse=True)
    elif sort_by == "Most Saved":
        filtered.sort(key=lambda x: save_counts.get(x["id"], 0), reverse=True)

    st.markdown(f"###### {len(filtered)} product(s) found")

    # Grid of product cards — LARGER images for better product visibility
    cols = st.columns(3)
    for i, p in enumerate(filtered):
        with cols[i % 3]:
            with st.container(border=True):
                # Product image — LARGER (180px height) for better visibility
                image_url = p.get("image_url")
                if image_url:
                    try:
                        st.markdown(
                            f"<div style='height:180px; overflow:hidden; border-radius:8px; margin-bottom:0.5rem;'>"
                            f"<img src='{image_url}' style='width:100%; height:100%; object-fit:cover; transition: transform 0.3s ease;' /></div>",
                            unsafe_allow_html=True,
                        )
                    except Exception:
                        st.markdown("🖼️")
                else:
                    st.markdown(
                        "<div style='height:180px; background:linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%); border-radius:8px; "
                        "display:flex; align-items:center; justify-content:center; "
                        "font-size:3rem; color:#94a3b8; margin-bottom:0.5rem;'>📦</div>",
                        unsafe_allow_html=True,
                    )

                producer = p.get("profiles") or {}
                # Compact name (smaller font)
                st.markdown(
                    f"<div style='font-size:0.9rem; font-weight:600; color:#0f172a; line-height:1.3; margin-bottom:0.15rem;'>{p['name']}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(f"by {producer.get('full_name', 'Unknown')} · {p.get('category', 'Other')}")

                # Quality + brand badges — compact inline
                if p.get("quality_grade") or p.get("brand"):
                    badges = []
                    if p.get("quality_grade"):
                        badges.append(f"⭐ {p['quality_grade']}")
                    if p.get("brand"):
                        badges.append(f"🏷️ {p['brand']}")
                    st.markdown(
                        f"<div style='font-size:0.7rem; color:#64748b; margin:0.2rem 0; font-weight:500;'>"
                        f"{' · '.join(badges)}</div>",
                        unsafe_allow_html=True,
                    )

                # Price (prominent) + stock/saves (compact below)
                st.markdown(
                    f"<div style='font-size:1.1rem; font-weight:700; color:#047857; margin:0.3rem 0 0.15rem 0;'>{format_currency(p['price'])}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(f"📦 {p['stock']} {format_unit(p.get('unit'))} · 💖 {save_counts.get(p['id'], 0)} saved")

                # Action buttons
                col_a, col_b = st.columns(2)
                with col_a:
                    # Save / unsave button
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
                    # Order button → opens product detail page (for everyone)
                    if st.button("🛒 Order", key=f"order_{p['id']}", use_container_width=True,
                                 type="primary"):
                        st.session_state["view_product_id"] = p["id"]
                        st.rerun()

                # Contact producer button (full width below)
                # Pre-fills the message form with producer's phone number
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
