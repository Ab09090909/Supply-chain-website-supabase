"""
Shared Marketplace — visible to ALL roles (producer, merchant, customer, admin).

Any logged-in user can browse all active products from all producers.
Customers can favorite + add to cart. Other roles can view + message the producer.
"""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user, get_current_role
from database.connection import get_supabase_client
from utils.ui import page_header, role_badge
from utils.helpers import format_currency


def render_shared_marketplace():
    page_header("Marketplace", "Browse all products from every producer on the platform")

    user = get_current_user()
    role = get_current_role()
    if not user:
        return

    try:
        client = get_supabase_client()
        products = (
            client.table("products")
            .select("*, profiles!products_producer_id_fkey(full_name, email, role)")
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
    except Exception as e:
        st.error(f"Failed to load marketplace: {e}")
        return

    if not products:
        st.info("No products available yet. Be the first to add one!")
        return

    # Filters
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        search = st.text_input("🔍 Search", placeholder="Try 'milk', 'avocado', 'organic'...")
    with col2:
        categories = ["All"] + sorted({p.get("category", "Other") for p in products})
        category = st.selectbox("Category", categories)
    with col3:
        sort_by = st.selectbox("Sort", ["Newest", "Price: Low→High", "Price: High→Low", "Stock: High→Low"])

    filtered = [
        p for p in products
        if (not search or search.lower() in p["name"].lower() or search.lower() in p.get("description", "").lower())
        and (category == "All" or p.get("category") == category)
    ]

    if sort_by == "Price: Low→High":
        filtered.sort(key=lambda x: float(x.get("price", 0)))
    elif sort_by == "Price: High→Low":
        filtered.sort(key=lambda x: float(x.get("price", 0)), reverse=True)
    elif sort_by == "Stock: High→Low":
        filtered.sort(key=lambda x: int(x.get("stock", 0)), reverse=True)

    st.markdown(f"###### {len(filtered)} product(s) found")

    # Grid of product cards with images
    cols = st.columns(3)
    for i, p in enumerate(filtered):
        with cols[i % 3]:
            with st.container(border=True):
                # Product image (NEW)
                image_url = p.get("image_url")
                if image_url:
                    try:
                        st.image(image_url, use_container_width=True)
                    except Exception:
                        st.markdown("🖼️ _Image unavailable_")
                else:
                    st.markdown(
                        "<div style='height:180px; background:#f1f5f9; border-radius:8px; "
                        "display:flex; align-items:center; justify-content:center; "
                        "font-size:3rem; color:#94a3b8;'>📦</div>",
                        unsafe_allow_html=True,
                    )

                producer = p.get("profiles") or {}
                st.markdown(f"**{p['name']}**")
                st.caption(f"by {producer.get('full_name', 'Unknown')} {role_badge(producer.get('role', ''))}", unsafe_allow_html=True)
                st.markdown(f"📦 `{p['sku']}` · 🏷️ {p.get('category', 'Other')}")
                st.markdown(f"### {format_currency(p['price'])}")
                st.caption(f"Stock: {p['stock']} {p.get('unit', '')}")

                col_a, col_b = st.columns(2)
                with col_a:
                    # Favorite button (all roles can favorite)
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
                    # Customers can add to cart; others can message producer
                    if role == "customer":
                        if st.button("🛒 Add", key=f"cart_{p['id']}", use_container_width=True):
                            try:
                                existing = client.table("cart_items").select("*").eq(
                                    "user_id", user["id"]
                                ).eq("product_id", p["id"]).execute().data
                                if existing:
                                    client.table("cart_items").update({
                                        "quantity": existing[0]["quantity"] + 1
                                    }).eq("id", existing[0]["id"]).execute()
                                else:
                                    client.table("cart_items").insert({
                                        "user_id": user["id"],
                                        "product_id": p["id"],
                                        "quantity": 1,
                                    }).execute()
                                st.success("Added to cart!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        # Non-customer: contact producer
                        if st.button("💬 Contact", key=f"msg_{p['id']}", use_container_width=True):
                            st.session_state["pending_message_to"] = producer.get("id")
                            st.session_state["pending_message_subject"] = f"Inquiry: {p['name']}"
                            st.info("Use the Notifications tab → Send Message to reach this producer.")
