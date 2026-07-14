"""
User preferences helper — shared by merchant + customer profile pages.

v4 updates:
  • Categories are now a multiselect dropdown + custom text input
  • Added preferred product names, quality grades, brands, models, classes, levels
"""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.constants import (
    PRODUCT_CATEGORIES, PAYMENT_TERMS, QUALITY_GRADES,
)
from utils.db_health import is_table_available


def render_preferences_section():
    """Render the preferences form. Used by merchant + customer profile pages."""
    user = get_current_user()
    if not user:
        return

    st.markdown("---")
    st.markdown("##### ⚙️ My Preferences")
    st.caption("These preferences help us personalize your marketplace, AI recommendations, and merchant matching.")

    # Check if the user_preferences table exists
    if not is_table_available("user_preferences"):
        st.error("❌ The `user_preferences` table doesn't exist yet.")
        st.info(
            "**To fix this:** Run `supabase/migration_v3.sql` in your Supabase SQL Editor.\n\n"
            "Go to: **Supabase Dashboard → SQL Editor → New Query** → "
            "paste the contents of `supabase/migration_v3.sql` → click **Run**."
        )
        return

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
    except Exception as e:
        err = str(e)
        if "PGRST205" in err or "could not find" in err.lower():
            st.error("❌ The `user_preferences` table doesn't exist yet.")
            st.info(
                "**To fix this:** Run `supabase/migration_v3.sql` in your Supabase SQL Editor.\n\n"
                "Go to: **Supabase Dashboard → SQL Editor → New Query** → "
                "paste the contents of `supabase/migration_v3.sql` → click **Run**."
            )
            return
        prefs = {}

    role = user.get("role")

    with st.form("prefs_form"):
        # ---- Section 1: Preferred Categories (dropdown + custom input) ----
        st.markdown("**Preferred Categories**")
        st.caption("Select the product categories you're most interested in. You can also add custom categories.")

        existing_cats = prefs.get("preferred_categories") or []
        # Multiselect dropdown for standard categories
        cats_selected = st.multiselect(
            "Select categories",
            options=PRODUCT_CATEGORIES,
            default=[c for c in existing_cats if c in PRODUCT_CATEGORIES],
            help="Pick one or more categories from the list. These are used for AI recommendations and merchant matching.",
            key="pref_cats_multiselect",
        )

        # Custom category input
        existing_custom = prefs.get("custom_categories") or []
        custom_cats_str = st.text_input(
            "Add custom categories (comma-separated)",
            value=", ".join(existing_custom) if existing_custom else "",
            placeholder="e.g. Coffee Beans, Spices, Handicrafts",
            help="Type any categories not in the list above, separated by commas. They will be saved alongside your selections.",
            key="pref_custom_cats",
        )
        # Parse custom categories
        custom_cats = [c.strip() for c in custom_cats_str.split(",") if c.strip()] if custom_cats_str else []
        all_cats = list(set(cats_selected + custom_cats))

        # ---- Section 2: Preferred Product Attributes (NEW) ----
        st.markdown("**Preferred Product Attributes**")
        st.caption("Specify what you're looking for in products. Used by AI for better matching.")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            # Preferred product names
            existing_names = prefs.get("preferred_product_names") or []
            names_str = st.text_input(
                "Preferred product names (comma-separated)",
                value=", ".join(existing_names) if existing_names else "",
                placeholder="e.g. Organic Wheat, Fresh Milk, Avocados",
                help="List specific product names you're interested in buying or selling.",
                key="pref_product_names",
            )
            preferred_names = [n.strip() for n in names_str.split(",") if n.strip()] if names_str else []

            # Preferred quality grades
            existing_grades = prefs.get("preferred_quality_grades") or []
            preferred_grades = st.multiselect(
                "Preferred quality grades",
                options=QUALITY_GRADES,
                default=[g for g in existing_grades if g in QUALITY_GRADES],
                help="Select the quality tiers you prefer. Producers will be matched based on these.",
                key="pref_grades",
            )

            # Preferred brands
            existing_brands = prefs.get("preferred_brands") or []
            brands_str = st.text_input(
                "Preferred brands (comma-separated)",
                value=", ".join(existing_brands) if existing_brands else "",
                placeholder="e.g. Green Valley, Sundar Organic",
                help="Brand names you trust or prefer.",
                key="pref_brands",
            )
            preferred_brands = [b.strip() for b in brands_str.split(",") if b.strip()] if brands_str else []

        with col_p2:
            # Preferred models
            existing_models = prefs.get("preferred_models") or []
            models_str = st.text_input(
                "Preferred models / variants (comma-separated)",
                value=", ".join(existing_models) if existing_models else "",
                placeholder="e.g. Premium 2024, Size M, Export Grade",
                help="Specific models or variants you're looking for.",
                key="pref_models",
            )
            preferred_models = [m.strip() for m in models_str.split(",") if m.strip()] if models_str else []

            # Preferred classes
            existing_classes = prefs.get("preferred_classes") or []
            classes_str = st.text_input(
                "Preferred classes (comma-separated)",
                value=", ".join(existing_classes) if existing_classes else "",
                placeholder="e.g. Class 1, Class A, Industrial",
                help="Product classification you prefer (e.g. Class 1, Class A).",
                key="pref_classes",
            )
            preferred_classes = [c.strip() for c in classes_str.split(",") if c.strip()] if classes_str else []

            # Preferred levels
            existing_levels = prefs.get("preferred_levels") or []
            levels_str = st.text_input(
                "Preferred levels (comma-separated)",
                value=", ".join(existing_levels) if existing_levels else "",
                placeholder="e.g. Level 1, Premium, Standard",
                help="Quality or tier levels you prefer.",
                key="pref_levels",
            )
            preferred_levels = [l.strip() for l in levels_str.split(",") if l.strip()] if levels_str else []

        # ---- Section 3: Role-specific business preferences ----
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
                    "preferred_categories": all_cats,
                    "custom_categories": custom_cats,
                    "preferred_product_names": preferred_names,
                    "preferred_quality_grades": preferred_grades,
                    "preferred_brands": preferred_brands,
                    "preferred_models": preferred_models,
                    "preferred_classes": preferred_classes,
                    "preferred_levels": preferred_levels,
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
                err = str(e)
                if "PGRST205" in err or "could not find" in err.lower():
                    st.error("❌ The `user_preferences` table doesn't exist yet.")
                    st.info(
                        "**To fix this:** Run `supabase/migration_v3.sql` in your Supabase SQL Editor.\n\n"
                        "Go to: **Supabase Dashboard → SQL Editor → New Query** → "
                        "paste the contents of `supabase/migration_v3.sql` → click **Run**."
                    )
                else:
                    st.error(f"Failed to save preferences: {e}")
