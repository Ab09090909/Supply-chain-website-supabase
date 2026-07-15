"""
Producer — AI Merchant Match page.

Shows AI-matched merchants with match percentage.
Producer can:
  • Send a request + proposed agreement terms to a merchant
  • Cancel a pending request
"""
from __future__ import annotations

import streamlit as st
from uuid import uuid4

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header, role_badge
from utils.helpers import format_currency
from ai.matchmaking import find_best_merchant_matches


_CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background: #f0f4f1;
    font-family: 'Inter', system-ui, sans-serif;
}
[data-testid="stHeader"] { background: transparent; }

/* Page header */
.pm-page-header {
    background: linear-gradient(135deg, #1a3a2e 0%, #14532d 60%, #0f3d23 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.pm-page-header h1 { color: #f0fdf4; font-size: 1.75rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
.pm-page-header p  { color: #86efac; font-size: 0.875rem; margin: 4px 0 0; }
.pm-header-icon    { font-size: 2.4rem; line-height: 1; }

/* Info banner */
.pm-info-banner {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 0.8rem;
    color: #1e40af;
    margin-bottom: 20px;
}

/* KPI strip */
.pm-kpi-strip { display: flex; gap: 12px; margin-bottom: 20px; }
.pm-kpi-pill {
    flex: 1;
    background: #fff;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    border: 1px solid rgba(0,0,0,.05);
    box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.pm-kpi-pill .kv { font-size: 1.6rem; font-weight: 800; color: #111827; line-height: 1; }
.pm-kpi-pill .kl { font-size: 0.67rem; font-weight: 600; letter-spacing: 0.09em; text-transform: uppercase; color: #9ca3af; margin-top: 4px; }

/* Section label */
.pm-section-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #6b7280; margin: 0 0 12px;
}

/* Match card */
.pm-card {
    background: #fff;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 14px;
    border: 1px solid rgba(0,0,0,.05);
    box-shadow: 0 1px 4px rgba(0,0,0,.05), 0 2px 8px rgba(0,0,0,.03);
}

/* Match score circle */
.pm-score-circle {
    width: 86px; height: 86px;
    border-radius: 50%;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    border: 3px solid;
    flex-shrink: 0;
}
.pm-score-circle .pct  { font-size: 1.4rem; font-weight: 800; line-height: 1; }
.pm-score-circle .lbl  { font-size: 0.58rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 2px; }

/* Merchant name / meta */
.pm-merchant-name { font-size: 1rem; font-weight: 700; color: #111827; }
.pm-merchant-company { font-size: 0.78rem; color: #6b7280; }
.pm-merchant-meta { font-size: 0.76rem; color: #9ca3af; margin-top: 3px; }

/* Matched tags */
.pm-tag {
    display: inline-block;
    background: #f0fdf4; color: #15803d;
    border: 1px solid #bbf7d0;
    border-radius: 20px; font-size: 0.68rem; font-weight: 600;
    padding: 2px 9px; margin: 2px 3px 2px 0;
}

/* Breakdown chips */
.pm-bd-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.pm-bd-chip {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 6px 12px;
    font-size: 0.75rem; color: #374151;
    display: flex; flex-direction: column; align-items: center;
}
.pm-bd-chip .bdv { font-weight: 800; color: #111827; font-size: 0.9rem; }
.pm-bd-chip .bdl { font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.07em; color: #9ca3af; margin-top: 1px; }

/* Status badges */
.pm-badge-pending  { display:inline-block; background:#fffbeb; color:#92400e; border:1px solid #fde68a; border-radius:20px; font-size:0.72rem; font-weight:600; padding:3px 10px; }
.pm-badge-confirmed{ display:inline-block; background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; border-radius:20px; font-size:0.72rem; font-weight:600; padding:3px 10px; }
.pm-badge-cancelled{ display:inline-block; background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; border-radius:20px; font-size:0.72rem; font-weight:600; padding:3px 10px; }

/* Divider */
.pm-divider { border:none; border-top:1px solid #e5e7eb; margin:14px 0; }

/* Form section label */
.pm-form-section {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #0d9488;
    padding: 10px 0 4px; border-bottom: 1px solid #e5e7eb; margin-bottom: 6px;
}

/* Empty */
.pm-empty {
    text-align: center; padding: 48px 16px; background: #fff;
    border-radius: 14px; border: 1px solid rgba(0,0,0,.05);
    color: #9ca3af; font-size: 0.85rem;
}
.pm-empty-icon { font-size: 2.5rem; display: block; margin-bottom: 10px; }
</style>
"""


def _score_color(pct: int) -> tuple[str, str]:
    if pct >= 70:
        return "#10b981", "Excellent"
    if pct >= 40:
        return "#f59e0b", "Good Match"
    return "#6b7280", "Low Match"


def render_producer_merchant_match():
    st.html(_CSS)

    st.html("""
    <div class="pm-page-header">
      <div class="pm-header-icon">🤝</div>
      <div>
        <h1>AI Merchant Match</h1>
        <p>AI finds the best merchant partners for your products</p>
      </div>
    </div>
    """)

    user = get_current_user()
    if not user:
        return

    try:
        client = get_supabase_client()
        products = (
            client.table("products")
            .select("*")
            .eq("producer_id", user["id"])
            .eq("status", "active")
            .execute()
        ).data or []
        st.session_state["producer_products"] = products
    except Exception:
        st.session_state["producer_products"] = []

    st.html("""
    <div class="pm-info-banner">
      💡 Our AI analyzes your products, the merchant's preferences, categories, quality grades,
      brands, price range, payment terms, and order history to find your best matches.
    </div>
    """)

    with st.spinner("🤖 Finding your best merchant matches…"):
        matches = find_best_merchant_matches(user["id"], top_n=10)

    if not matches:
        st.html('<div class="pm-empty"><span class="pm-empty-icon">🤝</span>No merchant matches found. Make sure you have active products and there are merchants registered on the platform.</div>')
        return

    # ── KPI strip ────────────────────────────────────────────────────────────
    excellent = sum(1 for m in matches if m["match_percentage"] >= 70)
    good      = sum(1 for m in matches if 40 <= m["match_percentage"] < 70)
    pills = "".join(
        f'<div class="pm-kpi-pill"><div class="kv">{v}</div><div class="kl">{l}</div></div>'
        for v, l in [(excellent, "🌟 Excellent"), (good, "👍 Good"), (len(matches), "Total Matches")]
    )
    st.html(f'<div class="pm-kpi-strip">{pills}</div>')
    st.html(f'<p class="pm-section-label">{len(matches)} merchant matches</p>')

    for m in matches:
        _render_match_card(m, user)


def _render_match_card(match: dict, producer: dict):
    pct   = match["match_percentage"]
    color, qlabel = _score_color(pct)

    # Build matched tags HTML
    tags_html = ""
    for cat in (match["matched_categories"] or []):
        tags_html += f'<span class="pm-tag">📂 {cat}</span>'
    for g in (match["matched_grades"] or []):
        tags_html += f'<span class="pm-tag">⭐ {g}</span>'
    for b in (match["matched_brands"] or []):
        tags_html += f'<span class="pm-tag">🏷️ {b}</span>'

    # Build breakdown chips
    bd = match["breakdown"]
    bd_items = [("Category", bd["category"]), ("Grade", bd["quality_grade"]),
                ("Brand", bd["brand"]), ("Price", bd["price_fit"]),
                ("Payment", bd["payment_terms"]), ("Location", bd["location"]),
                ("History", bd["order_history"])]
    bd_html = "".join(
        f'<div class="pm-bd-chip"><span class="bdv">{v}%</span><span class="bdl">{l}</span></div>'
        for l, v in bd_items
    )

    existing = match.get("existing_request_status")
    if existing == "pending":
        status_html = '<span class="pm-badge-pending">⏳ Request Pending</span>'
    elif existing == "confirmed":
        status_html = '<span class="pm-badge-confirmed">✅ Confirmed</span>'
    elif existing == "cancelled":
        status_html = '<span class="pm-badge-cancelled">❌ Cancelled</span>'
    else:
        status_html = ""

    avatar = match.get("merchant_avatar")
    avatar_html = (
        f'<img src="{avatar}" style="width:42px;height:42px;border-radius:50%;object-fit:cover;flex-shrink:0;" />'
        if avatar else
        '<div style="width:42px;height:42px;border-radius:50%;background:#f1f5f9;display:flex;align-items:center;justify-content:center;font-size:1.3rem;flex-shrink:0;">🏪</div>'
    )

    verified = '<span style="font-size:0.72rem;color:#15803d;">✅ Verified</span>' if match.get("merchant_verified") else ""

    st.html(f"""
    <div class="pm-card">
      <div style="display:flex;gap:16px;align-items:flex-start;">

        <!-- Score circle -->
        <div class="pm-score-circle" style="background:{color}12;border-color:{color};">
          <span class="pct" style="color:{color};">{pct}%</span>
          <span class="lbl" style="color:{color};">{qlabel}</span>
        </div>

        <!-- Merchant info -->
        <div style="flex:1;min-width:0;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
            {avatar_html}
            <div>
              <div class="pm-merchant-name">{match['merchant_name']} {verified}</div>
              <div class="pm-merchant-company">{match.get('merchant_company') or 'Independent Merchant'}</div>
            </div>
          </div>
          <div class="pm-merchant-meta">
            📍 {match.get('merchant_location') or 'Unknown'} &nbsp;·&nbsp; 📧 {match['merchant_email']}
          </div>
          {('<div style="margin-top:6px;">' + tags_html + '</div>') if tags_html else ''}
        </div>

        <!-- Status -->
        <div style="flex-shrink:0;text-align:right;">
          {status_html}
        </div>
      </div>

      <!-- Breakdown strip -->
      <div class="pm-divider"></div>
      <div class="pm-bd-row">{bd_html}</div>
    </div>
    """)

    # Action buttons (outside HTML for Streamlit interactivity)
    if existing == "pending":
        if st.button("❌ Cancel Request", key=f"cancel_{match['merchant_id']}", use_container_width=True):
            _cancel_request(producer["id"], match["merchant_id"])

    elif existing == "cancelled":
        if st.button("🔄 Resend Request", key=f"resend_{match['merchant_id']}", type="primary", use_container_width=True):
            st.session_state[f"show_form_{match['merchant_id']}"] = True
            st.rerun()

    elif not existing:
        if st.button("📨 Send Request & Agreement", key=f"send_{match['merchant_id']}", type="primary", use_container_width=True):
            st.session_state[f"show_form_{match['merchant_id']}"] = True
            st.rerun()

    if st.session_state.get(f"show_form_{match['merchant_id']}"):
        _render_agreement_form(match, producer)


def _render_agreement_form(match: dict, producer: dict):
    st.html('<div class="pm-form-section">Propose Agreement Terms</div>')

    with st.form(f"agreement_form_{match['merchant_id']}"):
        col1, col2 = st.columns(2)
        with col1:
            product_options = st.session_state.get("producer_products", [])
            if product_options:
                product_label    = st.selectbox(
                    "Product for this agreement",
                    options=[p["name"] for p in product_options],
                    key=f"agr_product_{match['merchant_id']}",
                )
                selected_product = next((p for p in product_options if p["name"] == product_label), None)
            else:
                st.text_input("Product", value="All active products", disabled=True)
                selected_product = None

        with col2:
            proposed_price = st.number_input(
                "Proposed unit price (Br)",
                min_value=0.0,
                value=float(selected_product["price"]) if selected_product else 100.0,
                step=10.0,
                key=f"agr_price_{match['merchant_id']}",
            )

        proposed_terms = st.text_area(
            "Agreement terms",
            value=(
                f"Producer {producer['full_name']} proposes to supply "
                f"{selected_product['name'] if selected_product else 'products'} to "
                f"{match['merchant_name']} at {format_currency(proposed_price)} per unit. "
                f"Payment: Net 30. Delivery: FOB producer location. "
                f"Quality: {selected_product.get('quality_grade', 'Standard') if selected_product else 'Standard'}."
            ),
            height=90,
            key=f"agr_terms_{match['merchant_id']}",
        )

        producer_message = st.text_area(
            "Message to merchant (optional)",
            placeholder="Hi! I think our businesses would be a great match because…",
            key=f"agr_msg_{match['merchant_id']}",
        )

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            submitted = st.form_submit_button("📨 Send Request", type="primary", use_container_width=True)
        with col_b2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)

        if submitted:
            _send_request(producer, match, selected_product, proposed_price, proposed_terms, producer_message)
        if cancelled:
            st.session_state.pop(f"show_form_{match['merchant_id']}", None)
            st.rerun()


def _send_request(producer: dict, match: dict, product: dict, price: float, terms: str, message: str):
    try:
        client         = get_supabase_client()
        agreement_code = f"AGR-MATCH-{uuid4().hex[:8].upper()}"

        client.table("merchant_requests").insert({
            "producer_id":      producer["id"],
            "merchant_id":      match["merchant_id"],
            "product_id":       product["id"] if product else None,
            "match_percentage": match["match_percentage"],
            "status":           "pending",
            "proposed_terms":   terms,
            "agreement_code":   agreement_code,
            "producer_message": message or None,
        }).execute()

        try:
            client.table("agreements").insert({
                "producer_id":    producer["id"],
                "merchant_id":    match["merchant_id"],
                "agreement_code": agreement_code,
                "title":          f"Supply Agreement — {product['name'] if product else 'Products'}",
                "terms":          terms,
                "status":         "pending",
            }).execute()
        except Exception:
            pass

        try:
            client.table("notifications").insert({
                "user_id":   match["merchant_id"],
                "sender_id": producer["id"],
                "title":     "🤝 New Merchant Match Request!",
                "message":   (
                    f"{producer['full_name']} (match: {match['match_percentage']}%) "
                    f"wants to establish a supply agreement with you. "
                    f"Check your Merchant Requests tab to review and confirm."
                ),
                "type": "info",
            }).execute()
        except Exception:
            pass

        st.success(f"✅ Request sent to {match['merchant_name']}! Agreement code: {agreement_code}")
        st.session_state.pop(f"show_form_{match['merchant_id']}", None)
        st.rerun()
    except Exception as e:
        st.error(f"Failed to send request: {e}")


def _cancel_request(producer_id: str, merchant_id: str):
    try:
        client = get_supabase_client()
        client.table("merchant_requests").delete().eq(
            "producer_id", producer_id
        ).eq("merchant_id", merchant_id).execute()
        st.success("Request cancelled.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to cancel: {e}")
