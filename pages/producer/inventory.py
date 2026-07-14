"""Producer inventory management — with new product fields (quality grade, model, brand, origin, certifications)."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency, format_unit
from utils.storage import render_image_uploader
from utils.constants import (
    PRODUCT_CATEGORIES, UNIT_OPTIONS, QUALITY_GRADES,
    CERTIFICATION_OPTIONS, CURRENCY_SYMBOL,
)


def render_producer_inventory():
    page_header("Inventory Management", "Add, edit, and track your products")

    user = get_current_user()
    if not user:
        return

    client = get_supabase_client()

    # ---- Add product form (with image upload + new fields) ----
    with st.expander("➕ Add new product", expanded=False):
        # Image upload section
        st.markdown("##### Product Image")
        new_image_url, _ = render_image_uploader(
            label="Upload product image",
            folder="products",
            current_url=None,
            key="new_product_image",
        )
        st.markdown("---")

        with st.form("add_product_form"):
            # Section 1: Basic info
            st.markdown("**Basic Information**")
            col1, col2 = st.columns(2)
            with col1:
                sku = st.text_input(
                    "SKU *",
                    placeholder="AGR-007",
                    help="A unique stock-keeping unit code for this product. Used in orders and inventory tracking.",
                )
                name = st.text_input(
                    "Product name *",
                    placeholder="Organic Carrots",
                    help="The display name customers see in the marketplace.",
                )
                category = st.selectbox(
                    "Category *",
                    PRODUCT_CATEGORIES,
                    help="Pick the category that best fits your product. Used for filtering in the marketplace.",
                )
            with col2:
                price = st.number_input(
                    f"Unit price ({CURRENCY_SYMBOL}) *",
                    min_value=0.0,
                    value=100.0,
                    step=10.0,
                    help="Price per unit in Ethiopian Birr. Customers see this in the marketplace.",
                )
                stock = st.number_input(
                    "Stock quantity *",
                    min_value=0,
                    value=100,
                    step=1,
                    help="How many units you currently have available to sell.",
                )
                unit = st.selectbox(
                    "Unit *",
                    UNIT_OPTIONS,
                    help="The unit of measurement. Includes Ethiopian standards (quintal, sack, bag) and international (kg, litre, dozen, etc.).",
                )

            # Section 2: Quality & branding (NEW)
            st.markdown("**Quality & Branding**")
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                quality_grade = st.selectbox(
                    "Quality Grade",
                    ["(none)"] + QUALITY_GRADES,
                    help="Quality grading helps buyers understand the product's tier. Common in agricultural supply chains.",
                )
                brand = st.text_input(
                    "Brand",
                    placeholder="e.g. Green Valley",
                    help="Your brand or product line name. Optional but recommended for marketing.",
                )
            with col_q2:
                model = st.text_input(
                    "Model / Variant",
                    placeholder="e.g. Premium 2024, Size M",
                    help="Specific model or variant of the product (e.g. for equipment, packaged goods).",
                )
                origin = st.text_input(
                    "Origin",
                    placeholder="e.g. Ethiopia, Oromia region",
                    help="Where the product was grown / manufactured. Buyers often prefer local origin.",
                )

            # Section 3: Certifications & dates (NEW)
            st.markdown("**Certifications & Dates**")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.caption("Certifications (tick all that apply)")
                certs_selected = []
                certs_cols = st.columns(3)
                for i, cert in enumerate(CERTIFICATION_OPTIONS):
                    with certs_cols[i % 3]:
                        if st.checkbox(cert, key=f"cert_{cert}"):
                            certs_selected.append(cert)
            with col_c2:
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    production_date = st.date_input(
                        "Production date",
                        value=None,
                        help="When this batch was produced / harvested. Optional.",
                    )
                with col_d2:
                    expiry_date = st.date_input(
                        "Expiry date",
                        value=None,
                        help="Best-before or expiry date for perishable items. Optional.",
                    )

            # Section 4: Inventory management
            st.markdown("**Inventory Management**")
            col_i1, col_i2 = st.columns(2)
            with col_i1:
                reorder_point = st.number_input(
                    "Reorder point",
                    min_value=0,
                    value=20,
                    help="When stock drops to this number, you'll get a low-stock alert.",
                )
            with col_i2:
                reorder_qty = st.number_input(
                    "Reorder quantity",
                    min_value=0,
                    value=50,
                    help="How many units to reorder when restocking.",
                )

            description = st.text_area(
                "Description",
                placeholder="Brief product description — what makes it special?",
                help="A clear, honest description helps buyers decide. Mention flavor, texture, growing method, etc.",
            )

            submitted = st.form_submit_button("Add product", type="primary")
            if submitted:
                if not sku or not name:
                    st.error("SKU and product name are required.")
                else:
                    try:
                        insert_payload = {
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
                            "quality_grade": quality_grade if quality_grade != "(none)" else None,
                            "brand": brand or None,
                            "model": model or None,
                            "origin": origin or None,
                            "certifications": certs_selected if certs_selected else None,
                            "production_date": str(production_date) if production_date else None,
                            "expiry_date": str(expiry_date) if expiry_date else None,
                        }
                        client.table("products").insert(insert_payload).execute()
                        st.success(f"Product '{name}' added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add product: {e}")

    # ---- Products table (with images + new fields) ----
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
            col_img, col_info, col_price, col_stock, col_status = st.columns([1, 3, 1, 1, 1])

            with col_img:
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
                meta_parts = []
                meta_parts.append(f"Category: {p.get('category', '—')}")
                meta_parts.append(f"Unit: {format_unit(p.get('unit'))}")
                if p.get("quality_grade"):
                    meta_parts.append(f"⭐ {p['quality_grade']}")
                if p.get("brand"):
                    meta_parts.append(f"🏷️ {p['brand']}")
                if p.get("origin"):
                    meta_parts.append(f"📍 {p['origin']}")
                st.caption(" · ".join(meta_parts))

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
