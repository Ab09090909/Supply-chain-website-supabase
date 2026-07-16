"""Producer inventory management — with new product fields (quality grade, model, brand, origin, certifications)."""
from __future__ import annotations

import streamlit as st
from datetime import date

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

    # ── Edit product (if one is selected) ──────────────────────────────────
    # The Edit button on each product card sets st.session_state["editing_product"]
    # to the product id, then reruns. On the next render we look it up and
    # show a full edit form. This was missing before — clicking Edit just
    # set the session state and the button appeared to do nothing.
    editing_id = st.session_state.get("editing_product")
    if editing_id:
        _render_edit_product(client, user, editing_id)
        return  # Don't show the rest of the inventory while editing

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

        # Show per-product order tracking on a separate row below the card
        _render_product_tracking(client, user, p)

        st.html('<hr class="pi-divider" style="margin:10px 0 14px;"/>')


# ---------------------------------------------------------------------------
# Per-product order tracking
# ---------------------------------------------------------------------------
def _render_product_tracking(client, user: dict, product: dict) -> None:
    """Show all orders for this specific product and let the producer
    update the tracking status (Confirmed → Processing → Shipped → Delivered).

    Rendered as a compact expander under each product card.
    """
    product_id = product.get("id")
    if not product_id:
        return

    try:
        # Find order_items that reference this product, joined with the
        # order and the buyer profile.
        items = (
            client.table("order_items")
            .select("id, order_id, sku, name, unit_price, quantity, "
                    "orders!inner(id, order_number, status, payment_status, "
                    "total, placed_at, confirmed_at, shipped_at, delivered_at, "
                    "buyer:profiles!orders_buyer_id_fkey(full_name, email, phone, location))")
            .eq("product_id", product_id)
            .order("created_at", desc=True, foreign_table="orders")
            .execute()
        ).data or []
    except Exception:
        # Fallback: simpler query without the join if the FK relationship
        # isn't detected (different schema versions)
        try:
            items = (
                client.table("order_items")
                .select("id, order_id, sku, name, unit_price, quantity")
                .eq("product_id", product_id)
                .execute()
            ).data or []
            # Hydrate with order data
            for it in items:
                if it.get("order_id"):
                    try:
                        o = client.table("orders").select(
                            "id, order_number, status, payment_status, total, "
                            "placed_at, confirmed_at, shipped_at, delivered_at"
                        ).eq("id", it["order_id"]).maybe_single().execute()
                        if o and o.data:
                            it["orders"] = o.data
                    except Exception:
                        pass
        except Exception:
            items = []

    if not items:
        return  # No orders for this product yet — no UI noise

    n_orders = len(items)
    n_pending = sum(1 for it in items if (it.get("orders") or {}).get("status") in ("pending", "confirmed", "processing"))
    n_shipped = sum(1 for it in items if (it.get("orders") or {}).get("status") == "shipped")

    with st.expander(
        f"📦 Orders & Tracking for this product — {n_orders} order"
        f"{'s' if n_orders != 1 else ''} ({n_pending} active, {n_shipped} shipped)",
        expanded=False,
    ):
        st.caption(
            "Update the shipping status for orders containing this product. "
            "Buyers see the same status in real-time."
        )

        for it in items:
            order = it.get("orders") or {}
            if not order:
                continue
            _render_single_order_tracking(client, user, product, it, order)


def _render_single_order_tracking(client, user: dict, product: dict, item: dict, order: dict) -> None:
    """Render one order row with inline status update controls."""
    from utils.tracking import get_tracking, update_tracking, add_timeline_event

    order_id   = order.get("id")
    order_num  = order.get("order_number", "—")
    status     = order.get("status", "pending")
    qty        = int(item.get("quantity") or 0)
    unit_price = float(item.get("unit_price") or 0)
    buyer      = order.get("buyer") or {}
    tracking   = get_tracking(order_id)

    # Status color + emoji
    status_colors = {
        "pending":    ("#f59e0b", "⏳"),
        "confirmed":  ("#10b981", "✅"),
        "processing": ("#3b82f6", "🔄"),
        "shipped":    ("#8b5cf6", "🚚"),
        "delivered":  ("#059669", "📦"),
        "cancelled":  ("#ef4444", "❌"),
    }
    color, emoji = status_colors.get(status, ("#64748b", "❓"))

    buyer_name = buyer.get("full_name", "Unknown buyer")
    buyer_loc  = buyer.get("location", "—")
    placed     = (order.get("placed_at") or "")[:10] or "—"

    with st.container(border=True):
        # Header row
        hcol1, hcol2 = st.columns([3, 1])
        with hcol1:
            st.markdown(
                f"<div style='font-size:0.95rem; font-weight:700; color:#111827;'>"
                f"🛒 {order_num}  <span style='color:{color}; font-size:0.8rem;'>"
                f"{emoji} {status.upper()}</span></div>"
                f"<div style='font-size:0.78rem; color:#64748b; margin-top:2px;'>"
                f"👤 {buyer_name} &nbsp;·&nbsp; 📍 {buyer_loc} &nbsp;·&nbsp; 📅 {placed}"
                f"</div>",
                unsafe_allow_html=True,
            )
        with hcol2:
            st.metric("Qty", qty, label_visibility="collapsed")

        # Inline tracking info
        if tracking:
            tn   = tracking.get("tracking_number") or "—"
            cr   = tracking.get("carrier") or "—"
            eta  = tracking.get("estimated_delivery") or "—"
            st.markdown(
                f"<div style='font-size:0.78rem; color:#475569; margin:6px 0;'>"
                f"🚚 <b>Tracking:</b> <code>{tn}</code> &nbsp;·&nbsp; "
                f"📦 <b>Carrier:</b> {cr} &nbsp;·&nbsp; "
                f"🗓️ <b>ETA:</b> {eta}"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Inline status updater
        next_status_map = {
            "pending": "confirmed",
            "confirmed": "processing",
            "processing": "shipped",
            "shipped": "delivered",
        }
        next_status = next_status_map.get(status)

        scol1, scol2 = st.columns([2, 3])
        with scol1:
            if next_status:
                labels = {
                    "pending":    "✅ Accept Order",
                    "confirmed":  "🔄 Start Processing",
                    "processing": "🚚 Mark as Shipped",
                    "shipped":    "📦 Mark as Delivered",
                }
                if st.button(labels[status], key=f"track_adv_{order_id}", type="primary", use_container_width=True):
                    try:
                        update_tracking(order_id, status=next_status)
                        # Add a timeline event
                        add_timeline_event(
                            order_id,
                            labels[status].split(" ", 1)[1] if " " in labels[status] else labels[status],
                            f"Producer updated status to {next_status}",
                        )
                        st.success(f"✅ Updated to {next_status}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")
        with scol2:
            with st.expander("✏️ Edit tracking details", expanded=False):
                with st.form(f"track_form_{order_id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_tn = st.text_input("Tracking number", value=tracking.get("tracking_number") or "" if tracking else "", key=f"tn_{order_id}")
                        new_cr = st.text_input("Carrier", value=tracking.get("carrier") or "" if tracking else "", key=f"cr_{order_id}")
                    with col2:
                        from datetime import date as _date
                        try:
                            eta_val = _date.fromisoformat(tracking["estimated_delivery"]) if tracking and tracking.get("estimated_delivery") else None
                        except Exception:
                            eta_val = None
                        new_eta = st.date_input("ETA", value=eta_val, key=f"eta_{order_id}")
                    new_notes = st.text_area("Notes", value=tracking.get("notes") or "" if tracking else "", key=f"notes_{order_id}")
                    if st.form_submit_button("💾 Save tracking", type="primary"):
                        try:
                            update_tracking(
                                order_id,
                                tracking_number=new_tn,
                                carrier=new_cr,
                                estimated_delivery=new_eta.isoformat() if new_eta else None,
                                notes=new_notes,
                            )
                            st.success("Saved!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")


# ---------------------------------------------------------------------------
# Edit product form
# ---------------------------------------------------------------------------
def _render_edit_product(client, user: dict, product_id: str) -> None:
    """Render the edit form for a single product.

    Looks up the product, prefills the form with its current values, and
    saves changes to the database on submit. Also has a "Delete" action
    and a "Cancel" button to close the editor without saving.

    Visual design: same dark-green page header as the inventory list,
    followed by a clean form card with all the same fields as the
    "Add new product" form so the producer sees a consistent UI.
    """
    # Fetch the product
    try:
        product = (
            client.table("products")
            .select("*")
            .eq("id", product_id)
            .eq("producer_id", user["id"])  # security: only owner can edit
            .maybe_single()
            .execute()
        ).data
    except Exception as e:
        st.error(f"Failed to load product: {e}")
        if st.button("← Back to inventory"):
            st.session_state.pop("editing_product", None)
            st.rerun()
        return

    if not product:
        st.error(
            "❌ Product not found, or you don't have permission to edit it. "
            "It may have been deleted by another admin."
        )
        if st.button("← Back to inventory"):
            st.session_state.pop("editing_product", None)
            st.rerun()
        return

    # Page header — same style as the inventory list, but with a back button
    st.html(f"""
    <div class="pi-page-header">
      <div class="pi-header-icon">✏️</div>
      <div>
        <h1>Edit Product</h1>
        <p>Update the details of <b>{product.get('name', '—')}</b> ({product.get('sku', '—')})</p>
      </div>
    </div>
    """)

    # Action row: Back / Save / Delete
    action_cols = st.columns([1, 1, 1, 3])
    with action_cols[0]:
        if st.button("← Back", key="edit_back", use_container_width=True):
            st.session_state.pop("editing_product", None)
            st.rerun()

    # ── Image uploader (preserves the existing image as the starting point)
    _section("Product Image")
    edit_image_url, _ = render_image_uploader(
        label="Update product image (optional)",
        folder="products",
        current_url=product.get("image_url"),
        key=f"edit_product_image_{product_id}",
    )

    with st.form(f"edit_product_form_{product_id}"):
        _section("Basic Information")
        col1, col2 = st.columns(2)
        with col1:
            # SKU is usually immutable — show as read-only so producers
            # don't accidentally break orders that reference it
            st.text_input(
                "SKU",
                value=product.get("sku", ""),
                disabled=True,
                help="SKU is immutable to preserve order history references.",
            )
            edit_name = st.text_input(
                "Product name *",
                value=product.get("name", ""),
            )
            edit_category = st.selectbox(
                "Category *",
                PRODUCT_CATEGORIES,
                index=(
                    PRODUCT_CATEGORIES.index(product["category"])
                    if product.get("category") in PRODUCT_CATEGORIES
                    else 0
                ),
            )
        with col2:
            edit_price = st.number_input(
                f"Unit price ({CURRENCY_SYMBOL}) *",
                min_value=0.0,
                value=float(product.get("price") or 0),
                step=10.0,
            )
            edit_stock = st.number_input(
                "Stock quantity *",
                min_value=0,
                value=int(product.get("stock") or 0),
                step=1,
            )
            current_unit = product.get("unit", "unit")
            unit_index = UNIT_OPTIONS.index(current_unit) if current_unit in UNIT_OPTIONS else 0
            edit_unit = st.selectbox(
                "Unit *",
                UNIT_OPTIONS,
                index=unit_index,
            )

        _section("Quality & Branding")
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            current_qg = product.get("quality_grade") or "(none)"
            qg_index = (
                (["(none)"] + QUALITY_GRADES).index(current_qg)
                if current_qg in (["(none)"] + QUALITY_GRADES)
                else 0
            )
            edit_quality_grade = st.selectbox(
                "Quality Grade",
                ["(none)"] + QUALITY_GRADES,
                index=qg_index,
            )
            edit_brand = st.text_input(
                "Brand",
                value=product.get("brand", "") or "",
            )
        with col_q2:
            edit_model = st.text_input(
                "Model / Variant",
                value=product.get("model", "") or "",
            )
            edit_origin = st.text_input(
                "Origin",
                value=product.get("origin", "") or "",
            )

        _section("Certifications & Dates")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.caption("Certifications (tick all that apply)")
            existing_certs = product.get("certifications") or []
            if not isinstance(existing_certs, list):
                existing_certs = [str(existing_certs)]
            certs_selected = []
            certs_cols = st.columns(3)
            for i, cert in enumerate(CERTIFICATION_OPTIONS):
                with certs_cols[i % 3]:
                    if st.checkbox(cert, value=(cert in existing_certs), key=f"edit_cert_{cert}"):
                        certs_selected.append(cert)
        with col_c2:
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                # date_input doesn't accept None, so we use a "clear" trick
                try:
                    edit_production_date = st.date_input(
                        "Production date",
                        value=(
                            date.fromisoformat(product["production_date"])
                            if product.get("production_date")
                            else None
                        ),
                    )
                except Exception:
                    edit_production_date = st.date_input("Production date", value=None)
            with col_d2:
                try:
                    edit_expiry_date = st.date_input(
                        "Expiry date",
                        value=(
                            date.fromisoformat(product["expiry_date"])
                            if product.get("expiry_date")
                            else None
                        ),
                    )
                except Exception:
                    edit_expiry_date = st.date_input("Expiry date", value=None)

        _section("Inventory Management")
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            edit_reorder_point = st.number_input(
                "Reorder point",
                min_value=0,
                value=int(product.get("reorder_point") or 0),
            )
        with col_i2:
            edit_reorder_qty = st.number_input(
                "Reorder quantity",
                min_value=0,
                value=int(product.get("reorder_quantity") or 0),
            )

        edit_description = st.text_area(
            "Description",
            value=product.get("description", "") or "",
        )

        # Status field (not in the add form because new products are always
        # 'active', but editing lets you deactivate a product too)
        edit_status = st.selectbox(
            "Status",
            ["active", "inactive", "draft"],
            index=["active", "inactive", "draft"].index(product.get("status", "active")),
            help="Set to inactive to hide the product from the marketplace without deleting it.",
        )

        # Save button
        submitted = st.form_submit_button("💾 Save changes", type="primary")
        if submitted:
            if not edit_name:
                st.error("Product name is required.")
            else:
                try:
                    update_payload = {
                        "name": edit_name,
                        "description": edit_description or None,
                        "category": edit_category,
                        "price": edit_price,
                        "stock": edit_stock,
                        "unit": edit_unit,
                        "reorder_point": edit_reorder_point,
                        "reorder_quantity": edit_reorder_qty,
                        "status": edit_status,
                        "image_url": edit_image_url or product.get("image_url"),
                        "quality_grade": edit_quality_grade if edit_quality_grade != "(none)" else None,
                        "brand": edit_brand or None,
                        "model": edit_model or None,
                        "origin": edit_origin or None,
                        "certifications": certs_selected if certs_selected else None,
                        "production_date": str(edit_production_date) if edit_production_date else None,
                        "expiry_date": str(edit_expiry_date) if edit_expiry_date else None,
                    }
                    # ── Persist the update ──────────────────────────────────────
                    result = client.table("products").update(update_payload).eq("id", product_id).execute()
                    returned_rows = (result.data or []) if result else []

                    # ── Verify it actually persisted ──────────────────────────
                    # RLS can silently drop the UPDATE if the policy doesn't
                    # match (e.g. wrong role check, missing WITH CHECK, or a
                    # transient auth issue). To distinguish "save succeeded"
                    # from "save was rejected by RLS without an error", we
                    # re-read the row and compare. If the new name doesn't
                    # match what we just sent, the update was silently
                    # rejected and we tell the user.
                    try:
                        verify = (
                            client.table("products")
                            .select("name, updated_at")
                            .eq("id", product_id)
                            .maybe_single()
                            .execute()
                        )
                        saved = (verify.data or {}) if verify else {}
                    except Exception:
                        saved = {}

                    if saved and saved.get("name") == edit_name:
                        # ✅ Confirmed: the row was updated and now contains
                        # the new value. Safe to close the editor.
                        st.success(
                            f"✅ '{edit_name}' updated successfully."
                        )
                        st.session_state.pop("editing_product", None)
                        st.rerun()
                    elif not returned_rows:
                        # RLS silently rejected the UPDATE — Supabase returned
                        # 200 OK but with no data because the row didn't match
                        # the USING clause. This is the "RLS no-op" problem.
                        st.error(
                            "❌ **Update was rejected by RLS.** Supabase returned "
                            "success but no rows were modified. This usually means:\n\n"
                            "1. Your JWT is stale or invalid — try logging out and logging back in\n"
                            "2. The `is_admin()` function has the search_path attack vulnerability — "
                            "run `supabase_sql/migration_v6.sql` to fix it\n"
                            "3. The `Producers update own products` policy is missing a `WITH CHECK` "
                            "clause — run `supabase_sql/migration_v6.sql` to add one\n\n"
                            "**Detail:** `update().eq('id', product_id).execute()` returned 0 rows. "
                            "The row was not modified."
                        )
                    else:
                        # Update returned rows but the verify read disagrees.
                        # Could be a network/replication hiccup.
                        st.warning(
                            f"⚠️ Update completed but the verify-read shows the old data. "
                            f"This is usually a transient issue — the change will appear on the "
                            f"next page refresh. If it persists, log out and log back in. "
                            f"Last verified name: {saved.get('name', '—')!r}, expected: {edit_name!r}"
                        )
                        st.session_state.pop("editing_product", None)
                        st.rerun()
                except Exception as e:
                    err = str(e).lower()
                    if "row-level security" in err or "42501" in err:
                        st.error(
                            "❌ Permission denied by RLS. Make sure you are the owner "
                            "of this product and that you're logged in. Try logging "
                            "out and back in."
                        )
