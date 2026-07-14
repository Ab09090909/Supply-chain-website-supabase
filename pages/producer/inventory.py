"""Producer inventory management — now with product image upload + image display."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency
from utils.storage import render_image_uploader


def render_producer_inventory():
    page_header("Inventory Management", "Add, edit, and track your products")

    user = get_current_user()
    if not user:
        return

    client = get_supabase_client()

    # ---- Add product form (with image upload) ----
    with st.expander("➕ Add new product", expanded=False):
        # Image upload section (NEW)
        st.markdown("##### Product Image")
        new_image_url, _ = render_image_uploader(
            label="Upload product image",
            folder="products",
            current_url=None,
            key="new_product_image",
        )
        st.markdown("---")

        with st.form("add_product_form"):
            col1, col2 = st.columns(2)
            with col1:
                sku = st.text_input("SKU *", placeholder="AGR-007")
                name = st.text_input("Product name *", placeholder="Organic Carrots")
                category = st.selectbox("Category", ["Grains", "Dairy", "Fruits", "Vegetables", "Pantry", "Beverages", "Herbs", "Other"])
                price = st.number_input("Unit price (USD) *", min_value=0.0, value=1.0, step=0.10)
            with col2:
                stock = st.number_input("Stock quantity *", min_value=0, value=100, step=1)
                unit = st.selectbox("Unit", ["unit", "kg", "ton", "gallon", "dozen", "liter", "box", "bottle", "bunch"])
                reorder_point = st.number_input("Reorder point", min_value=0, value=20)
                reorder_qty = st.number_input("Reorder quantity", min_value=0, value=50)

            description = st.text_area("Description", placeholder="Brief product description...")

            submitted = st.form_submit_button("Add product", type="primary")
            if submitted:
                if not sku or not name:
                    st.error("SKU and product name are required.")
                else:
                    try:
                        client.table("products").insert({
                            "sku": sku,
                            "name": name,
                            "description": description,
                            "category": category,
                            "price": price,
                            "stock": stock,
                            "unit": unit,
                            "reorder_point": reorder_point,
                            "reorder_quantity": reorder_qty,
                            "producer_id": user["id"],
                            "status": "active",
                            "image_url": new_image_url,
                        }).execute()
                        st.success(f"Product '{name}' added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add product: {e}")

    # ---- Products table (with images) ----
    st.markdown("##### Your Products")
    try:
        products = (
            client.table("products")
            .select("*")
            .eq("producer_id", user["id"])
            .order("created_at", desc=True)
            .execute()
        ).data or []
    except Exception as e:
        st.error(f"Failed to load products: {e}")
        return

    if not products:
        st.info("No products yet. Add your first product above.")
        return

    for p in products:
        with st.container(border=True):
            # Layout: image | info | metrics | status | actions
            col_img, col_info, col_price, col_stock, col_status = st.columns([1, 3, 1, 1, 1])

            with col_img:
                # Product image (NEW)
                if p.get("image_url"):
                    try:
                        st.image(p["image_url"], width=80)
                    except Exception:
                        st.markdown("📦")
                else:
                    st.markdown(
                        "<div style='width:80px; height:80px; background:#f1f5f9; "
                        "border-radius:8px; display:flex; align-items:center; "
                        "justify-content:center; font-size:2rem;'>📦</div>",
                        unsafe_allow_html=True,
                    )

            with col_info:
                st.markdown(f"**{p['name']}**  `{p['sku']}`")
                st.caption(p.get("description") or "No description")
                st.caption(f"Category: {p.get('category', '—')} · Unit: {p.get('unit', '')}")

            with col_price:
                st.metric("Price", format_currency(p["price"]))

            with col_stock:
                st.metric("Stock", f"{p['stock']}")

            with col_status:
                status = "⚠️ Low" if p["stock"] <= p["reorder_point"] else "✅ OK"
                st.metric("Status", status)
                if st.button("Edit", key=f"edit_{p['id']}"):
                    st.session_state["editing_product"] = p["id"]
                    st.rerun()
