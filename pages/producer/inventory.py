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


# ── Design tokens (shared with producer_dashboard) ─────────────────────────────
_CSS = """
<style>
/* ── Global ── */
[data-testid="stAppViewContainer"] {
    background: #f0f4f1;
    font-family: 'Inter', system-ui, sans-serif;
}
[data-testid="stHeader"] { background: transparent; }

/* ── Page header ── */
.pi-page-header {
    background: linear-gradient(135deg, #1a3a2e 0%, #14532d 60%, #0f3d23 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.pi-page-header h1 {
    color: #f0fdf4;
    font-size: 1.75rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.5px;
}
.pi-page-header p {
    color: #86efac;
    font-size: 0.875rem;
    margin: 4px 0 0;
}
.pi-header-icon { font-size: 2.4rem; line-height: 1; }

/* ── Section label ── */
.pi-section-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6b7280;
    margin: 0 0 12px;
}

/* ── Add-product expander button ── */
.pi-add-btn-wrap {
    margin-bottom: 20px;
}

/* ── Form card ── */
.pi-form-section-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #0d9488;
    padding: 10px 0 4px;
    border-bottom: 1px solid #e5e7eb;
    margin-bottom: 4px;
}

/* ── Product card ── */
.pi-product-card {
    background: #ffffff;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06), 0 2px 8px rgba(0,0,0,.03);
    border: 1px solid rgba(0,0,0,.05);
    transition: box-shadow .15s ease;
}
.pi-product-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,.09);
}

/* Product name / SKU row */
.pi-product-name {
    font-size: 1rem;
    font-weight: 700;
    color: #111827;
    margin: 0;
}
.pi-product-sku {
    display: inline-block;
    background: #f0fdf4;
    color: #15803d;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 20px;
    border: 1px solid #bbf7d0;
    margin-left: 8px;
    vertical-align: middle;
}
.pi-product-desc {
    font-size: 0.82rem;
    color: #6b7280;
    margin: 4px 0 6px;
}
.pi-product-meta {
    font-size: 0.78rem;
    color: #9ca3af;
}
.pi-product-meta b { color: #374151; }

/* Stat pills inside card */
.pi-stat-pill {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 8px 16px;
    min-width: 72px;
    text-align: center;
}
.pi-stat-pill .val {
    font-size: 1.1rem;
    font-weight: 800;
    color: #111827;
    line-height: 1.1;
}
.pi-stat-pill .lbl {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #9ca3af;
    margin-top: 2px;
}

/* Status badge */
.pi-badge-ok {
    display: inline-block;
    background: #f0fdf4;
    color: #15803d;
    border: 1px solid #bbf7d0;
    font-size: 0.72rem;
    font-weight: 600;
    border-radius: 20px;
    padding: 3px 10px;
}
.pi-badge-low {
    display: inline-block;
    background: #fff7ed;
    color: #c2410c;
    border: 1px solid #fed7aa;
    font-size: 0.72rem;
    font-weight: 600;
    border-radius: 20px;
    padding: 3px 10px;
}

/* Product image placeholder */
.pi-img-placeholder {
    width: 76px; height: 76px;
    background: #f1f5f9;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    flex-shrink: 0;
}

/* Divider */
.pi-divider {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 24px 0 20px;
}

/* Empty state */
.pi-empty {
    text-align: center;
    padding: 48px 16px;
    background: #fff;
    border-radius: 14px;
    border: 1px solid rgba(0,0,0,.05);
    color: #9ca3af;
    font-size: 0.85rem;
}
.pi-empty-icon { font-size: 2.5rem; display: block; margin-bottom: 10px; }
</style>
"""

def _section(label: str) -> None:
    st.html(f'<div class="pi-form-section-label">{label}</div>')


def render_producer_inventory():
    st.html(_CSS)

    # ── Page header ──────────────────────────────────────────────────────────
    st.html("""
    <div class="pi-page-header">
      <div class="pi-header-icon">📦</div>
      <div>
        <h1>Inventory Management</h1>
        <p>Add, edit, and track your products</p>
      </div>
    </div>
    """)

    user = get_current_user()
    if not user:
        return

    client = get_supabase_client()

    # ── Add product form ─────────────────────────────────────────────────────
    with st.expander("➕  Add new product", expanded=False):
        _section("Product Image")
        new_image_url, _ = render_image_uploader(
            label="Upload product image",
            folder="products",
            current_url=None,
            key="new_product_image",
        )

        with st.form("add_product_form"):
            _section("Basic Information")
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
                    help="Pick the category that best fits your product.",
                )
            with col2:
                price = st.number_input(
                    f"Unit price ({CURRENCY_SYMBOL}) *",
                    min_value=0.0,
                    value=100.0,
                    step=10.0,
                    help="Price per unit in Ethiopian Birr.",
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
                    help="Unit of measurement (quintal, sack, kg, litre, dozen …).",
                )

            _section("Quality & Branding")
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                quality_grade = st.selectbox(
                    "Quality Grade",
                    ["(none)"] + QUALITY_GRADES,
                    help="Quality grading helps buyers understand the product's tier.",
                )
                brand = st.text_input(
                    "Brand",
                    placeholder="e.g. Green Valley",
                    help="Your brand or product line name.",
                )
            with col_q2:
                model = st.text_input(
                    "Model / Variant",
                    placeholder="e.g. Premium 2024, Size M",
                    help="Specific model or variant of the product.",
                )
                origin = st.text_input(
                    "Origin",
                    placeholder="e.g. Ethiopia, Oromia region",
                    help="Where the product was grown / manufactured.",
                )

            _section("Certifications & Dates")
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
                        help="When this batch was produced / harvested.",
                    )
                with col_d2:
                    expiry_date = st.date_input(
                        "Expiry date",
                        value=None,
                        help="Best-before or expiry date for perishable items.",
                    )

            _section("Inventory Management")
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
                help="A clear, honest description helps buyers decide.",
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
                        st.success(f"✅ '{name}' added to inventory.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add product: {e}")

    st.html('<hr class="pi-divider"/>')

    # ── Products list ────────────────────────────────────────────────────────
    st.html('<p class="pi-section-label">Your Products</p>')

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
        st.html("""
        <div class="pi-empty">
          <span class="pi-empty-icon">📦</span>
          No products yet — add your first one above.
        </div>
        """)
        return

    for p in products:
        is_low = p["stock"] <= p["reorder_point"]
        badge = '<span class="pi-badge-low">⚠️ Low stock</span>' if is_low else '<span class="pi-badge-ok">✅ In stock</span>'

        # Build meta tags
        meta_parts = [f"<b>Category:</b> {p.get('category', '—')}",
                      f"<b>Unit:</b> {format_unit(p.get('unit'))}"]
        if p.get("quality_grade"):
            meta_parts.append(f"⭐ {p['quality_grade']}")
        if p.get("brand"):
            meta_parts.append(f"🏷️ {p['brand']}")
        if p.get("origin"):
            meta_parts.append(f"📍 {p['origin']}")
        if p.get("certifications"):
            certs = p["certifications"]
            meta_parts.append("🏅 " + ", ".join(certs if isinstance(certs, list) else [str(certs)]))
        meta_html = " &nbsp;·&nbsp; ".join(meta_parts)

        col_img, col_info, col_stats, col_actions = st.columns([1, 4, 3, 1], gap="medium")

        with col_img:
            if p.get("image_url"):
                try:
                    st.image(p["image_url"], width=76)
                except Exception:
                    st.html('<div class="pi-img-placeholder">📦</div>')
            else:
                st.html('<div class="pi-img-placeholder">📦</div>')

        with col_info:
            desc = p.get("description") or "No description provided."
            st.html(f"""
            <div style="padding-top:4px;">
              <span class="pi-product-name">{p['name']}</span>
              <span class="pi-product-sku">{p['sku']}</span>
              <div class="pi-product-desc">{desc[:120]}{'…' if len(desc) > 120 else ''}</div>
              <div class="pi-product-meta">{meta_html}</div>
            </div>
            """)

        with col_stats:
            st.html(f"""
            <div style="display:flex;gap:10px;padding-top:6px;flex-wrap:wrap;align-items:center;">
              <div class="pi-stat-pill">
                <span class="val">{format_currency(p['price'])}</span>
                <span class="lbl">Price</span>
              </div>
              <div class="pi-stat-pill">
                <span class="val">{p['stock']}</span>
                <span class="lbl">Stock</span>
              </div>
              <div class="pi-stat-pill">
                <span class="val">{p['reorder_point']}</span>
                <span class="lbl">Reorder at</span>
              </div>
              {badge}
            </div>
            """)

        with col_actions:
            st.markdown("<div style='padding-top:18px;'>", unsafe_allow_html=True)
            if st.button("Edit", key=f"edit_{p['id']}", use_container_width=True):
                st.session_state["editing_product"] = p["id"]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.html('<hr class="pi-divider" style="margin:10px 0 14px;"/>')
