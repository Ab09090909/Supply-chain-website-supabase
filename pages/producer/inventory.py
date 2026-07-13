"""Producer inventory management."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency


def render_producer_inventory():
    page_header("Inventory Management", "Add, edit, and track your products")

    user = get_current_user()
    if not user:
        return

    client = get_supabase_client()

    # ---- Add product form ----
    with st.expander("➕ Add new product", expanded=False):
        with st.form("add_product_form"):
            col1, col2 = st.columns(2)
            with col1:
                sku = st.text_input("SKU *", placeholder="AGR-007")
                name = st.text_input("Product name *", placeholder="Organic Carrots")
                category = st.selectbox("Category", ["Grains", "Dairy", "Fruits", "Vegetables", "Pantry", "Other"])
                price = st.number_input("Unit price (USD) *", min_value=0.0, value=1.0, step=0.10)
            with col2:
                stock = st.number_input("Stock quantity *", min_value=0, value=100, step=1)
                unit = st.selectbox("Unit", ["unit", "kg", "ton", "gallon", "dozen", "liter", "box"])
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
                        }).execute()
                        st.success(f"Product '{name}' added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add product: {e}")

    # ---- Products table ----
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
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
            with col1:
                st.markdown(f"**{p['name']}**  `{p['sku']}`")
                st.caption(p.get("description") or "No description")
            with col2:
                st.metric("Price", format_currency(p["price"]))
            with col3:
                st.metric("Stock", f"{p['stock']} {p.get('unit', '')}")
            with col4:
                status = "⚠️ Low" if p["stock"] <= p["reorder_point"] else "✅ OK"
                st.metric("Status", status)
            with col5:
                if st.button("Edit", key=f"edit_{p['id']}"):
                    st.session_state["editing_product"] = p["id"]
                    st.rerun()
