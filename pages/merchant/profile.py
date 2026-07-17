"""Merchant profile page — now with avatar image upload + preferences."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.storage import render_image_uploader
from utils.preferences import render_preferences_section


def render_merchant_profile():
    page_header("Merchant Profile", "Manage your business profile")

    user = get_current_user()
    if not user:
        return

    # ---- Account verification section (shown for unverified users) ----
    vstatus = user.get("verification_status")
    if vstatus != "verified":
        st.markdown("---")
        st.markdown("### 🔐 Account Verification")
        st.caption("Verify your business identity to unlock ordering, AI features, and producer matching.")
        try:
            from auth.verification import render_verification_page
            render_verification_page()
        except Exception as e:
            st.error(f"Verification module failed to load: {e}")
        st.markdown("---")

    # ---- Avatar image upload (auto-saves to DB) ----
    st.markdown("##### Profile Photo")
    avatar_url, avatar_err = render_image_uploader(
        label="Upload new avatar",
        folder="avatars",
        current_url=user.get("avatar_url"),
        key="avatar_uploader_merchant",
    )

    # If a new avatar was uploaded, auto-save the URL to the profile
    # row so the user doesn't have to also click "Save changes".
    if avatar_url and avatar_url != user.get("avatar_url") and not avatar_err:
        try:
            from database.connection import get_supabase_admin_client, get_supabase_client
            try:
                writer = get_supabase_admin_client()
            except Exception:
                writer = get_supabase_client()
            writer.table("profiles").update({"avatar_url": avatar_url}).eq("id", user["id"]).execute()
            st.session_state["user"]["avatar_url"] = avatar_url
            st.success("✅ Avatar updated!")
            st.rerun()
        except Exception as e:
            st.error(f"Avatar save failed: {e}")

    st.markdown("---")

    with st.form("merchant_profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Business name", value=user.get("full_name", ""))
            email = st.text_input("Email", value=user.get("email", ""), disabled=True)
            phone = st.text_input("Phone", value=user.get("phone", "") or "")
        with col2:
            location = st.text_input("Location", value=user.get("location", "") or "")
            company = st.text_input("Company", value=user.get("company", "") or "")

        submitted = st.form_submit_button("Save changes", type="primary")
        if submitted:
            try:
                client = get_supabase_client()
                client.table("profiles").update({
                    "full_name": full_name,
                    "phone": phone,
                    "location": location,
                    "company": company,
                    "avatar_url": avatar_url,
                }).eq("id", user["id"]).execute()
                st.session_state["user"].update({
                    "full_name": full_name,
                    "phone": phone,
                    "location": location,
                    "company": company,
                    "avatar_url": avatar_url,
                })
                st.success("Profile updated!")
                st.rerun()  # Force rerun so sidebar avatar refreshes
            except Exception as e:
                st.error(f"Update failed: {e}")

    # ---- Preferences section (NEW) ----
    render_preferences_section()

    # ---- Digital business card + QR code (offline, downloadable) ----
    try:
        from utils.business_card import render_business_card
        render_business_card(user)
    except Exception as e:
        st.error(f"Business card unavailable: {e}")
