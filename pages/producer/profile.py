"""Producer profile settings — now with avatar image upload."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user, get_current_role
from database.connection import get_supabase_client
from utils.ui import page_header, sidebar_user_card
from utils.storage import render_image_uploader


def render_producer_profile():
    page_header("Profile & Settings", "Manage your account information")

    user = get_current_user()
    if not user:
        return

    # ---- Avatar image upload (NEW) ----
    st.markdown("##### Profile Photo")
    avatar_url, avatar_err = render_image_uploader(
        label="Upload new avatar",
        folder="avatars",
        current_url=user.get("avatar_url"),
        key="avatar_uploader",
    )

    st.markdown("---")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full name / Company name", value=user.get("full_name", ""))
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
                st.success("Profile updated successfully!")
                st.rerun()  # Force rerun so the sidebar avatar refreshes
            except Exception as e:
                st.error(f"Update failed: {e}")
