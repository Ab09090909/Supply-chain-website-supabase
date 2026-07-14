"""Customer marketplace - browse and favorite products."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency


def render_customer_marketplace():
    page_header("Marketplace", "Browse fresh products from our producers")

    user = get_current_user()
    if not user:
        return

    try:
        client = get_supabase_client()
        products = (
            client.table("products")
            .select("*, profiles!products_producer_id_fkey(full_name, company)")
            .eq("status", "active")
            .gt("stock", 0)
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
        st.info("No products available right now. Check back soon!")
        return

    # Search / filter
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search products", placeholder="Try 'milk', 'avocado', 'wheat'...")
    with col2:
        categories = ["All"] + sorted({p.get("category", "Other") for p in products})
        category = st.selectbox("Category", categories)

    filtered = [
        p for p in products
        if (not search or search.lower() in p["name"].lower() or search.lower() in p.get("description", "").lower())
        and (category == "All" or p.get("category") == category)
    ]

    st.markdown(f"###### {len(filtered)} product(s) found")

    # Grid layout
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
                        st.markdown("📦")
                else:
                    st.markdown(
                        "<div style='height:120px; background:#f1f5f9; border-radius:8px; "
                        "display:flex; align-items:center; justify-content:center; "
                        "font-size:2.5rem; color:#94a3b8;'>📦</div>",
                        unsafe_allow_html=True,
                    )

                producer = p.get("profiles") or {}
                st.markdown(f"**{p['name']}**")
                st.caption(f"by {producer.get('full_name', 'Unknown')}")
                st.markdown(f"📦 `{p['sku']}` · 🏷️ {p.get('category', 'Other')}")
                st.markdown(f"### {format_currency(p['price'])}")
                st.caption(f"Stock: {p['stock']} {p.get('unit', '')}")

                col_a, col_b = st.columns(2)
                with col_a:
                    if p["id"] in fav_ids:
                        if st.button("♥", key=f"unfav_{p['id']}", help="Remove from favorites"):
                            client.table("favorites").delete().eq(
                                "user_id", user["id"]
                            ).eq("product_id", p["id"]).execute()
                            st.rerun()
                    else:
                        if st.button("♡", key=f"fav_{p['id']}", help="Add to favorites"):
                            client.table("favorites").insert({
                                "user_id": user["id"],
                                "product_id": p["id"],
                            }).execute()
                            st.rerun()
                with col_b:
                    qty = st.number_input("Qty", min_value=1, max_value=p["stock"], value=1, key=f"qty_{p['id']}")
                    if st.button("Add to cart", key=f"cart_{p['id']}"):
                        try:
                            existing = client.table("cart_items").select("*").eq(
                                "user_id", user["id"]
                            ).eq("product_id", p["id"]).execute().data
                            if existing:
                                client.table("cart_items").update({
                                    "quantity": existing[0]["quantity"] + qty
                                }).eq("id", existing[0]["id"]).execute()
                            else:
                                client.table("cart_items").insert({
                                    "user_id": user["id"],
                                    "product_id": p["id"],
                                    "quantity": qty,
                                }).execute()
                            st.success(f"Added {qty} × {p['name']} to cart!")
                        except Exception as e:
                            st.error(f"Failed: {e}")
