"""
Shared Marketplace — visible to ALL roles.
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

/* Section label */
.mp-section-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #6b7280; margin: 0 0 14px;
}

/* Product card — top portion (image + info) */
.mp-card {
    background: #fff;
    border-radius: 14px 14px 0 0;
    overflow: hidden;
    border: 1px solid rgba(0,0,0,.07);
    border-bottom: none;
    box-shadow: 0 1px 4px rgba(0,0,0,.05), 0 2px 8px rgba(0,0,0,.03);
    transition: box-shadow .15s ease, transform .15s ease;
}
.mp-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,.10); }

.mp-card-img {
    width: 100%; height: 165px; object-fit: cover; display: block;
}
.mp-card-img-placeholder {
    width: 100%; height: 165px;
    background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 3rem; color: #94a3b8;
}
.mp-card-body { padding: 11px 13px 12px; }
.mp-card-name  { font-size: 0.9rem; font-weight: 700; color: #111827; line-height: 1.3; margin-bottom: 2px; }
.mp-card-by    { font-size: 0.7rem; color: #9ca3af; margin-bottom: 5px; }
.mp-card-tags  { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 5px; }
.mp-tag-grade  { background: #fefce8; color: #854d0e; border: 1px solid #fde68a; border-radius: 20px; font-size: 0.63rem; font-weight: 600; padding: 1px 7px; }
.mp-tag-brand  { background: #f0f9ff; color: #0369a1; border: 1px solid #bae6fd; border-radius: 20px; font-size: 0.63rem; font-weight: 600; padding: 1px 7px; }
.mp-card-price { font-size: 1.1rem; font-weight: 800; color: #047857; margin-bottom: 1px; }
.mp-card-meta  { font-size: 0.68rem; color: #9ca3af; }

/* Action bar — bottom of each card, 3 buttons in one row */
.mp-action-bar {
    background: #fff;
    border: 1px solid rgba(0,0,0,.07);
    border-top: 1px solid #f1f5f9;
    border-radius: 0 0 14px 14px;
    display: flex;
    overflow: hidden;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,.04);
}
.mp-action-bar a, .mp-action-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 7px 4px;
    font-size: 0.72rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    border: none;
    border-right: 1px solid #f1f5f9;
    background: #fff;
    color: #374151;
    transition: background .12s;
    white-space: nowrap;
}
.mp-action-bar .mp-action-btn:last-child { border-right: none; }
.mp-action-btn:hover { background: #f8fafc; }
.mp-action-btn.save  { color: #be185d; }
.mp-action-btn.save:hover  { background: #fdf2f8; }
.mp-action-btn.order { color: #fff; background: #059669; font-weight: 700; }
.mp-action-btn.order:hover { background: #047857; }
.mp-action-btn.contact { color: #1d4ed8; }
.mp-action-btn.contact:hover { background: #eff6ff; }

/* Streamlit button overrides — make them invisible, we use HTML buttons for display */
/* But actual clicks come from st.button hidden behind the HTML via z-index trick */
/* Instead we use st.columns(3) with tiny compact buttons */

/* Compact the 3-column button row */
.mp-btn-row div[data-testid="column"] {
    padding: 0 !important;
}
.mp-btn-row div[data-testid="column"]:not(:last-child) {
    border-right: 1px solid #f1f5f9;
}
.mp-btn-row [data-testid="stButton"] > button {
    border-radius: 0 !important;
    border: none !important;
    border-right: 1px solid #f1f5f9 !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    padding: 6px 2px !important;
    height: 34px !important;
    min-height: 34px !important;
    background: #fff !important;
    color: #374151 !important;
    box-shadow: none !important;
    width: 100% !important;
}
.mp-btn-row [data-testid="stButton"]:last-child > button {
    border-right: none !important;
    border-radius: 0 0 14px 0 !important;
}
.mp-btn-row [data-testid="stButton"]:first-child > button {
    border-radius: 0 0 0 14px !important;
}
.mp-btn-row [data-testid="stButton"] > button:hover {
    background: #f8fafc !important;
    color: #111827 !important;
}
/* Order button — green */
.mp-btn-row .mp-order-col [data-testid="stButton"] > button {
    background: #059669 !important;
    color: #fff !important;
    font-weight: 700 !important;
}
.mp-btn-row .mp-order-col [data-testid="stButton"] > button:hover {
    background: #047857 !important;
}

/* Wrap the 3-col row */
.mp-btn-row {
    background: #fff;
    border: 1px solid rgba(0,0,0,.07);
    border-top: 1px solid #f1f5f9;
    border-radius: 0 0 14px 14px;
    overflow: hidden;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,.04);
    display: flex;
}
/* The stHorizontalBlock inside mp-btn-row */
.mp-btn-row > div { width: 100%; }
.mp-btn-row [data-testid="stHorizontalBlock"] { gap: 0 !important; }

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
            client.table("favorites").select("product_id").execute()
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
        st.html('<div class="mp-empty"><span class="mp-empty-icon">🏪</span>No products available yet.</div>')
        return

    # ── Filters ──────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        search = st.text_input("Search", placeholder="🔍  coffee, wheat, organic…", label_visibility="collapsed")
    with col2:
        category = st.selectbox("Category", ["All"] + PRODUCT_CATEGORIES, label_visibility="collapsed")
    with col3:
        sort_by = st.selectbox("Sort", ["Newest", "Price: Low → High", "Price: High → Low", "Stock: High → Low", "Most Saved"], label_visibility="collapsed")

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
        st.html('<div class="mp-empty"><span class="mp-empty-icon">🔍</span>No products match your search.</div>')
        return

    # ── Product grid ──────────────────────────────────────────────────────────
    grid = st.columns(3, gap="medium")
    for i, p in enumerate(filtered):
        producer  = p.get("profiles") or {}
        is_saved  = p["id"] in fav_ids
        saves     = save_counts.get(p["id"], 0)
        image_url = p.get("image_url")

        tags_html = ""
        if p.get("quality_grade"):
            tags_html += f'<span class="mp-tag-grade">⭐ {p["quality_grade"]}</span>'
        if p.get("brand"):
            tags_html += f'<span class="mp-tag-brand">🏷️ {p["brand"]}</span>'

        img_html = (
            f'<img class="mp-card-img" src="{image_url}" alt="{p["name"]}" />'
            if image_url else
            '<div class="mp-card-img-placeholder">📦</div>'
        )

        with grid[i % 3]:
            # ── Card info (top) ──
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

            # ── Action bar (bottom) — 3 buttons in one row ──
            st.html('<div class="mp-btn-row">')
            heart   = "♥ Saved" if is_saved else "♡ Save"
            fav_key = f"unfav_{p['id']}" if is_saved else f"fav_{p['id']}"

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(heart, key=fav_key, use_container_width=True):
                    try:
                        if is_saved:
                            client.table("favorites").delete().eq("user_id", user["id"]).eq("product_id", p["id"]).execute()
                        else:
                            client.table("favorites").insert({"user_id": user["id"], "product_id": p["id"]}).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")
            with c2:
                if st.button("🛒 Order", key=f"order_{p['id']}", use_container_width=True, type="primary"):
                    st.session_state["view_product_id"] = p["id"]
                    st.rerun()
            with c3:
                if st.button("💬 Contact", key=f"contact_{p['id']}", use_container_width=True):
                    st.session_state.update({
                        "pending_message_to":      producer.get("id"),
                        "pending_message_to_name": producer.get("full_name"),
                        "pending_message_subject": f"Inquiry: {p['name']}",
                        "pending_message_body": (
                            f"Hello {producer.get('full_name', 'there')},\n\n"
                            f"I'm interested in your product: {p['name']} (SKU: {p['sku']}).\n\n"
                            f"- Phone: {producer.get('phone') or 'Not provided'}\n"
                            f"- Email: {producer.get('email') or 'Not provided'}\n"
                            f"- Company: {producer.get('company') or 'Independent Producer'}\n\n"
                            f"Could you provide more details about availability and delivery?\n\nThank you."
                        ),
                        "force_nav": "notifications",
                    })
                    st.rerun()
            st.html('</div>')
