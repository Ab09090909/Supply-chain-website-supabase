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


_CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background: #f0f4f1;
    font-family: 'Inter', system-ui, sans-serif;
}
[data-testid="stHeader"] { background: transparent; }

/* Page header */
.mp-page-header {
    background: linear-gradient(135deg, #1a3a2e 0%, #14532d 60%, #0f3d23 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.mp-page-header h1 { color: #f0fdf4; font-size: 1.75rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
.mp-page-header p  { color: #86efac; font-size: 0.875rem; margin: 4px 0 0; }
.mp-header-icon    { font-size: 2.4rem; line-height: 1; }

/* Filter bar */
.mp-filter-bar {
    background: #fff;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 20px;
    border: 1px solid rgba(0,0,0,.05);
    box-shadow: 0 1px 4px rgba(0,0,0,.04);
}

/* Section label */
.mp-section-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #6b7280; margin: 0 0 14px;
}

/* Product card */
.mp-card {
    background: #fff;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(0,0,0,.05);
    box-shadow: 0 1px 4px rgba(0,0,0,.05), 0 2px 8px rgba(0,0,0,.03);
    transition: box-shadow .15s ease, transform .15s ease;
    margin-bottom: 18px;
    height: 100%;
}
.mp-card:hover {
    box-shadow: 0 6px 20px rgba(0,0,0,.10);
    transform: translateY(-2px);
}

/* Image zone */
.mp-card-img {
    width: 100%; height: 170px;
    object-fit: cover;
    display: block;
}
.mp-card-img-placeholder {
    width: 100%; height: 170px;
    background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 3rem; color: #94a3b8;
}

/* Card body */
.mp-card-body { padding: 12px 14px 6px; }
.mp-card-name { font-size: 0.92rem; font-weight: 700; color: #111827; line-height: 1.3; margin-bottom: 2px; }
.mp-card-by   { font-size: 0.72rem; color: #9ca3af; margin-bottom: 5px; }
.mp-card-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px; }

.mp-tag-grade {
    background: #fefce8; color: #854d0e;
    border: 1px solid #fde68a;
    border-radius: 20px; font-size: 0.65rem; font-weight: 600; padding: 2px 7px;
}
.mp-tag-brand {
    background: #f0f9ff; color: #0369a1;
    border: 1px solid #bae6fd;
    border-radius: 20px; font-size: 0.65rem; font-weight: 600; padding: 2px 7px;
}

.mp-card-price { font-size: 1.15rem; font-weight: 800; color: #047857; margin-bottom: 2px; }
.mp-card-meta  { font-size: 0.7rem; color: #9ca3af; margin-bottom: 10px; }

/* Button tray — snaps flush under card, same border-radius bottom */
.mp-btn-tray {
    background: #fff;
    border: 1px solid rgba(0,0,0,.07);
    border-top: none;
    border-radius: 0 0 14px 14px;
    padding: 8px 10px 10px;
    margin-top: -6px;
    margin-bottom: 18px;
    display: flex;
    flex-direction: column;
    gap: 5px;
}
.mp-btn-row { display: flex; gap: 5px; }

/* Make Streamlit buttons inside tray compact */
.mp-btn-tray [data-testid="stButton"] > button {
    padding: 4px 8px !important;
    font-size: 0.75rem !important;
    height: 30px !important;
    min-height: 30px !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
    line-height: 1 !important;
}

/* Remove extra gap Streamlit adds above/below buttons */
.mp-btn-tray [data-testid="stButton"] {
    margin: 0 !important;
}
.mp-btn-tray div[data-testid="column"] {
    padding: 0 !important;
    gap: 0 !important;
}

/* Card itself — remove bottom radius so tray connects seamlessly */
.mp-card { border-bottom-left-radius: 0 !important; border-bottom-right-radius: 0 !important; margin-bottom: 0 !important; }

/* Button tray — snaps flush under card */
.mp-btn-tray {
    background: #fff;
    border: 1px solid rgba(0,0,0,.07);
    border-top: none;
    border-radius: 0 0 14px 14px;
    padding: 7px 10px 10px;
    margin-top: -4px;
    margin-bottom: 18px;
}

/* Compact buttons inside tray */
.mp-btn-tray [data-testid="stButton"] > button {
    padding: 4px 8px !important;
    font-size: 0.75rem !important;
    height: 30px !important;
    min-height: 30px !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
    line-height: 1 !important;
}
.mp-btn-tray [data-testid="stButton"] { margin: 0 !important; }
.mp-btn-tray div[data-testid="column"] { padding: 0 !important; }
.mp-btn-tray [data-testid="stVerticalBlockBorderWrapper"] { margin-bottom: 0 !important; }

/* Card — flat bottom so tray attaches cleanly */
.mp-card {
    border-bottom-left-radius: 0 !important;
    border-bottom-right-radius: 0 !important;
    margin-bottom: 0 !important;
}

/* Empty */
.mp-empty {
    text-align: center; padding: 60px 16px; background: #fff;
    border-radius: 14px; border: 1px solid rgba(0,0,0,.05);
    color: #9ca3af; font-size: 0.85rem;
}
.mp-empty-icon { font-size: 2.5rem; display: block; margin-bottom: 10px; }
</style>
"""


def render_shared_marketplace():
    st.html(_CSS)

    st.html("""
    <div class="mp-page-header">
      <div class="mp-header-icon">🏪</div>
      <div>
        <h1>Marketplace</h1>
        <p>Browse all products from every producer on the platform</p>
      </div>
    </div>
    """)

    user = get_current_user()
    role = get_current_role()
    if not user:
        return

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
        st.html('<div class="mp-empty"><span class="mp-empty-icon">🏪</span>No products available yet. Be the first to add one!</div>')
        return

    # ── Filters ──────────────────────────────────────────────────────────────
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            search = st.text_input(
                "Search",
                placeholder="🔍  Try 'coffee', 'wheat', 'organic'…",
                label_visibility="collapsed",
            )
        with col2:
            category = st.selectbox(
                "Category",
                ["All"] + PRODUCT_CATEGORIES,
                label_visibility="collapsed",
            )
        with col3:
            sort_by = st.selectbox(
                "Sort",
                ["Newest", "Price: Low → High", "Price: High → Low", "Stock: High → Low", "Most Saved"],
                label_visibility="collapsed",
            )

    # ── Filter + sort ─────────────────────────────────────────────────────────
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

    st.html(f'<p class="mp-section-label">{len(filtered)} product{"s" if len(filtered) != 1 else ""} found</p>')

    if not filtered:
        st.html('<div class="mp-empty"><span class="mp-empty-icon">🔍</span>No products match your search. Try a different keyword or category.</div>')
        return

    # ── Product grid ──────────────────────────────────────────────────────────
    cols = st.columns(3, gap="medium")
    for i, p in enumerate(filtered):
        producer   = p.get("profiles") or {}
        is_saved   = p["id"] in fav_ids
        saves      = save_counts.get(p["id"], 0)
        image_url  = p.get("image_url")

        # Build tag HTML
        tags_html = ""
        if p.get("quality_grade"):
            tags_html += f'<span class="mp-tag-grade">⭐ {p["quality_grade"]}</span>'
        if p.get("brand"):
            tags_html += f'<span class="mp-tag-brand">🏷️ {p["brand"]}</span>'

        # Image HTML
        if image_url:
            img_html = f'<img class="mp-card-img" src="{image_url}" alt="{p["name"]}" />'
        else:
            img_html = '<div class="mp-card-img-placeholder">📦</div>'

        with cols[i % 3]:
            # Card HTML (static display)
            st.html(f"""
            <div class="mp-card">
              {img_html}
              <div class="mp-card-body">
                <div class="mp-card-name">{p['name']}</div>
                <div class="mp-card-by">by {producer.get('full_name', 'Unknown')} · {p.get('category', 'Other')}</div>
                {('<div class="mp-card-tags">' + tags_html + '</div>') if tags_html else ''}
                <div class="mp-card-price">{format_currency(p['price'])}</div>
                <div class="mp-card-meta">📦 {p['stock']} {format_unit(p.get('unit'))} &nbsp;·&nbsp; 💖 {saves} saved</div>
              </div>
            </div>
            """)

            # Button tray — styled to snap flush under the card
            st.html('<div class="mp-btn-tray">')

            btn_col1, btn_col2 = st.columns(2, gap="small")
            with btn_col1:
                heart   = "♥ Saved" if is_saved else "♡ Save"
                fav_key = f"unfav_{p['id']}" if is_saved else f"fav_{p['id']}"
                if st.button(heart, key=fav_key, use_container_width=True):
                    try:
                        if is_saved:
                            client.table("favorites").delete().eq("user_id", user["id"]).eq("product_id", p["id"]).execute()
                        else:
                            client.table("favorites").insert({"user_id": user["id"], "product_id": p["id"]}).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")
            with btn_col2:
                if st.button("🛒 Order", key=f"order_{p['id']}", use_container_width=True, type="primary"):
                    st.session_state["view_product_id"] = p["id"]
                    st.rerun()

            if st.button("💬 Contact Producer", key=f"contact_{p['id']}", use_container_width=True):
                producer_phone   = producer.get("phone") or "Not provided"
                producer_email   = producer.get("email") or "Not provided"
                producer_company = producer.get("company") or "Independent Producer"
                st.session_state.update({
                    "pending_message_to":      producer.get("id"),
                    "pending_message_to_name": producer.get("full_name"),
                    "pending_message_subject": f"Inquiry: {p['name']}",
                    "pending_message_body": (
                        f"Hello {producer.get('full_name', 'there')},\n\n"
                        f"I'm interested in your product: {p['name']} (SKU: {p['sku']}).\n\n"
                        f"Producer contact information:\n"
                        f"- Phone: {producer_phone}\n"
                        f"- Email: {producer_email}\n"
                        f"- Company: {producer_company}\n\n"
                        f"Could you please provide more details about availability and delivery?\n\n"
                        f"Thank you."
                    ),
                    "force_nav": "notifications",
                })
                st.rerun()

            st.html('</div>')
