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


def render_producer_merchant_match():
    page_header("🤝 AI Merchant Match", "AI finds the best merchant partners for your products")

    user = get_current_user()
    if not user:
        return

    # Load producer's products for the agreement form
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

    st.info(
        "💡 Our AI analyzes your products, the merchant's preferences, categories, "
        "quality grades, brands, price range, payment terms, and order history to "
        "find your best matches."
    )

    # --- Find matches ---
    with st.spinner("🤖 AI is analyzing and finding your best merchant matches..."):
        matches = find_best_merchant_matches(user["id"], top_n=10)

    if not matches:
        st.warning(
            "No merchant matches found. Make sure you have active products and "
            "there are merchants registered on the platform."
        )
        return

    st.markdown(f"###### Found {len(matches)} potential merchant matches")

    # --- Summary stats ---
    excellent = sum(1 for m in matches if m["match_percentage"] >= 70)
    good = sum(1 for m in matches if 40 <= m["match_percentage"] < 70)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Excellent Matches (≥70%)", excellent)
    with col2:
        st.metric("Good Matches (40-69%)", good)
    with col3:
        st.metric("Total Merchants", len(matches))

    st.markdown("---")

    # --- Match cards ---
    for m in matches:
        _render_match_card(m, user)


def _render_match_card(match: dict, producer: dict):
    """Render a single merchant match card with actions."""
    pct = match["match_percentage"]

    # Color based on match quality
    if pct >= 70:
        color = "#10b981"
        label = "Excellent Match"
    elif pct >= 40:
        color = "#f59e0b"
        label = "Good Match"
    else:
        color = "#6b7280"
        label = "Low Match"

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 3, 2])

        with col1:
            # Match percentage circle
            st.markdown(
                f"""
                <div style='text-align:center; padding:1rem; border-radius:12px;
                            background:{color}11; border:2px solid {color};'>
                    <div style='font-size:2rem; font-weight:700; color:{color};'>{pct}%</div>
                    <div style='font-size:0.75rem; color:{color}; font-weight:600;'>{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            # Merchant info
            avatar = match.get("merchant_avatar")
            if avatar:
                st.markdown(
                    f"<div style='display:flex; align-items:center; gap:0.75rem;'>"
                    f"<img src='{avatar}' style='width:48px; height:48px; border-radius:50%; object-fit:cover;' />"
                    f"<div><strong>{match['merchant_name']}</strong><br/>"
                    f"<span style='color:#64748b; font-size:0.85rem;'>{match['merchant_company'] or 'Independent Merchant'}</span>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"**{match['merchant_name']}**  {role_badge('merchant')}",
                    unsafe_allow_html=True,
                )
                st.caption(match["merchant_company"] or "Independent Merchant")

            st.caption(f"📍 {match['merchant_location'] or 'Unknown'} · 📧 {match['merchant_email']}")
            if match.get("merchant_verified"):
                st.caption("✅ Verified merchant")

            # Matched attributes
            matched_parts = []
            if match["matched_categories"]:
                matched_parts.append("Categories: " + ", ".join(match["matched_categories"]))
            if match["matched_grades"]:
                matched_parts.append("Grades: " + ", ".join(match["matched_grades"]))
            if match["matched_brands"]:
                matched_parts.append("Brands: " + ", ".join(match["matched_brands"]))
            if matched_parts:
                st.caption("✨ " + " | ".join(matched_parts))

        with col3:
            # Status / actions
            existing = match.get("existing_request_status")
            if existing == "pending":
                st.warning("⏳ Request sent (awaiting response)")
                if st.button("❌ Cancel Request", key=f"cancel_{match['merchant_id']}", use_container_width=True):
                    _cancel_request(producer["id"], match["merchant_id"])
            elif existing == "confirmed":
                st.success("✅ Agreement confirmed!")
            elif existing == "cancelled":
                st.error("❌ Request was cancelled")
                if st.button("🔄 Resend Request", key=f"resend_{match['merchant_id']}", use_container_width=True):
                    st.session_state[f"show_form_{match['merchant_id']}"] = True
                    st.rerun()
            else:
                if st.button("📨 Send Request & Agreement", key=f"send_{match['merchant_id']}", use_container_width=True, type="primary"):
                    st.session_state[f"show_form_{match['merchant_id']}"] = True
                    st.rerun()

        # --- Expandable match breakdown ---
        with st.expander("📊 View match breakdown"):
            bd = match["breakdown"]
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("Category Match", f"{bd['category']}%")
                st.metric("Brand Match", f"{bd['brand']}%")
            with col_b:
                st.metric("Quality Grade", f"{bd['quality_grade']}%")
                st.metric("Price Fit", f"{bd['price_fit']}%")
            with col_c:
                st.metric("Payment Terms", f"{bd['payment_terms']}%")
                st.metric("Location", f"{bd['location']}%")
            with col_d:
                st.metric("Order History", f"{bd['order_history']}%")

        # --- Agreement form (shown when "Send Request" is clicked) ---
        if st.session_state.get(f"show_form_{match['merchant_id']}"):
            _render_agreement_form(match, producer)


def _render_agreement_form(match: dict, producer: dict):
    """Render the agreement proposal form."""
    st.markdown("##### 📜 Propose Agreement Terms")

    with st.form(f"agreement_form_{match['merchant_id']}"):
        col1, col2 = st.columns(2)
        with col1:
            product_options = st.session_state.get("producer_products", [])
            if product_options:
                product_label = st.selectbox(
                    "Product for this agreement",
                    options=[p["name"] for p in product_options],
                    help="Select which product this agreement covers.",
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
                help="The price you're offering to this merchant.",
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
            height=100,
            help="Edit these terms as needed. The merchant will see them when reviewing your request.",
            key=f"agr_terms_{match['merchant_id']}",
        )

        producer_message = st.text_area(
            "Message to merchant (optional)",
            placeholder="Hi! I think our businesses would be a great match because...",
            help="A personal message increases the chance of the merchant accepting.",
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
    """Send the merchant request + create agreement + notify merchant."""
    try:
        client = get_supabase_client()
        agreement_code = f"AGR-MATCH-{uuid4().hex[:8].upper()}"

        # Create the merchant request
        client.table("merchant_requests").insert({
            "producer_id": producer["id"],
            "merchant_id": match["merchant_id"],
            "product_id": product["id"] if product else None,
            "match_percentage": match["match_percentage"],
            "status": "pending",
            "proposed_terms": terms,
            "agreement_code": agreement_code,
            "producer_message": message or None,
        }).execute()

        # Also create an entry in the agreements table
        try:
            client.table("agreements").insert({
                "producer_id": producer["id"],
                "merchant_id": match["merchant_id"],
                "agreement_code": agreement_code,
                "title": f"Supply Agreement — {product['name'] if product else 'Products'}",
                "terms": terms,
                "status": "pending",
            }).execute()
        except Exception:
            pass  # agreements table insert is best-effort

        # Notify the merchant
        try:
            client.table("notifications").insert({
                "user_id": match["merchant_id"],
                "sender_id": producer["id"],
                "title": "🤝 New Merchant Match Request!",
                "message": (
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
    """Cancel a pending merchant request."""
    try:
        client = get_supabase_client()
        client.table("merchant_requests").delete().eq(
            "producer_id", producer_id
        ).eq("merchant_id", merchant_id).execute()
        st.success("Request cancelled.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to cancel: {e}")
