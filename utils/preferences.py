"""
User preferences helper — shared by merchant + customer profile pages.

Renders a preferences form for the user_preferences table.
"""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.constants import (
    PRODUCT_CATEGORIES, PAYMENT_TERMS, UNIT_OPTIONS,
)


def render_preferences_section():
    """Render the preferences form. Used by merchant + customer profile pages."""
    user = get_current_user()
    if not user:
        return

    st.markdown("---")
    st.markdown("##### ⚙️ My Preferences")
    st.caption("These preferences help us personalize your marketplace and AI recommendations.")

    client = get_supabase_client()

    # Load existing preferences
    try:
        existing = (
            client.table("user_preferences")
            .select("*")
            .eq("user_id", user["id"])
            .maybe_single()
            .execute()
        )
        prefs = existing.data if existing else {}
    except Exception:
        prefs = {}

    role = user.get("role")

    with st.form("prefs_form"):
        # Preferred categories (multi-select via checkboxes)
        st.markdown("**Preferred Categories**")
        st.caption("Select the product categories you're most interested in.")
        existing_cats = set(prefs.get("preferred_categories") or [])
        cats_selected = []
        cats_cols = st.columns(4)
        for i, cat in enumerate(PRODUCT_CATEGORIES):
            with cats_cols[i % 4]:
                if st.checkbox(cat, value=cat in existing_cats, key=f"pref_cat_{cat}"):
                    cats_selected.append(cat)

        # Role-specific fields
        if role == "merchant":
            st.markdown("**Business Preferences**")
            col1, col2 = st.columns(2)
            with col1:
                max_price = st.number_input(
                    "Max order value (Br)",
                    min_value=0.0,
                    value=float(prefs.get("max_price_range") or 50000),
                    step=1000.0,
                    help="Maximum order value you typically place in a single transaction.",
                )
            with col2:
                typical_size = st.number_input(
                    "Typical order size (units)",
                    min_value=1,
                    value=int(prefs.get("typical_order_size") or 100),
                    step=10,
                    help="Average number of units per order you place.",
                )
            payment_terms = st.selectbox(
                "Preferred payment terms",
                PAYMENT_TERMS,
                index=PAYMENT_TERMS.index(prefs.get("payment_terms")) if prefs.get("payment_terms") in PAYMENT_TERMS else 0,
                help="How you prefer to pay producers.",
            )
        else:  # customer
            st.markdown("**Shopping Preferences**")
            col1, col2 = st.columns(2)
            with col1:
                max_price = st.number_input(
                    "Max price per item (Br)",
                    min_value=0.0,
                    value=float(prefs.get("max_price_range") or 5000),
                    step=100.0,
                    help="Maximum price you're willing to pay for a single product unit.",
                )
            with col2:
                typical_size = st.number_input(
                    "Typical quantity per order",
                    min_value=1,
                    value=int(prefs.get("typical_order_size") or 5),
                    step=1,
                    help="How many units you usually buy at once.",
                )
            payment_terms = st.selectbox(
                "Preferred payment method",
                PAYMENT_TERMS,
                index=PAYMENT_TERMS.index(prefs.get("payment_terms")) if prefs.get("payment_terms") in PAYMENT_TERMS else 0,
                help="How you prefer to pay for orders.",
            )

        # Dietary restrictions (mainly for customers)
        if role == "customer":
            st.markdown("**Dietary Restrictions / Preferences**")
            st.caption("Helps us filter recommendations.")
            existing_diet = set(prefs.get("dietary_restrictions") or [])
            diet_options = ["Vegetarian", "Vegan", "Halal", "Kosher", "Gluten-Free", "Nut-Free", "Lactose-Free", "No restrictions"]
            diet_cols = st.columns(4)
            diet_selected = []
            for i, d in enumerate(diet_options):
                with diet_cols[i % 4]:
                    if st.checkbox(d, value=d in existing_diet, key=f"diet_{d}"):
                        diet_selected.append(d)
        else:
            diet_selected = []

        # Notification preferences
        st.markdown("**Notification Preferences**")
        col_n1, col_n2, col_n3 = st.columns(3)
        with col_n1:
            notif_email = st.checkbox(
                "Email notifications",
                value=bool(prefs.get("notification_email", True)),
                help="Receive order updates and alerts via email.",
            )
        with col_n2:
            notif_push = st.checkbox(
                "In-app notifications",
                value=bool(prefs.get("notification_push", True)),
                help="See notifications inside the app (bell icon).",
            )
        with col_n3:
            newsletter = st.checkbox(
                "Newsletter opt-in",
                value=bool(prefs.get("newsletter_opt_in", False)),
                help="Get weekly product recommendations and platform news.",
            )

        notes = st.text_area(
            "Additional notes (optional)",
            value=prefs.get("notes") or "",
            placeholder="Anything else we should know about your preferences?",
            help="Free-form notes about your preferences.",
        )

        submitted = st.form_submit_button("💾 Save Preferences", type="primary")
        if submitted:
            try:
                payload = {
                    "user_id": user["id"],
                    "preferred_categories": cats_selected,
                    "max_price_range": float(max_price),
                    "typical_order_size": int(typical_size),
                    "payment_terms": payment_terms,
                    "dietary_restrictions": diet_selected,
                    "notification_email": bool(notif_email),
                    "notification_push": bool(notif_push),
                    "newsletter_opt_in": bool(newsletter),
                    "notes": notes or None,
                }
                # Upsert (insert or update on conflict)
                client.table("user_preferences").upsert(payload, on_conflict="user_id").execute()
                st.success("✅ Preferences saved!")
            except Exception as e:
                st.error(f"Failed to save preferences: {e}")