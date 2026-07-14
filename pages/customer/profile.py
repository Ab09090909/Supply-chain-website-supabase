"""Customer profile — now with avatar image upload."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.storage import render_image_uploader


def render_customer_profile():
    page_header("My Profile", "Manage your account details")

    user = get_current_user()
    if not user:
        return

    # ---- Avatar image upload (NEW) ----
    st.markdown("##### Profile Photo")
    avatar_url, avatar_err = render_image_uploader(
        label="Upload new avatar",
        folder="avatars",
        current_url=user.get("avatar_url"),
        key="avatar_uploader_customer",
    )

    st.markdown("---")

    with st.form("customer_profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full name", value=user.get("full_name", ""))
            email = st.text_input("Email", value=user.get("email", ""), disabled=True)
            phone = st.text_input("Phone", value=user.get("phone", "") or "")
        with col2:
            location = st.text_input("Location", value=user.get("location", "") or "")

        submitted = st.form_submit_button("Save changes", type="primary")
        if submitted:
            try:
                client = get_supabase_client()
                client.table("profiles").update({
                    "full_name": full_name,
                    "phone": phone,
                    "location": location,
                    "avatar_url": avatar_url,
                }).eq("id", user["id"]).execute()
                st.session_state["user"].update({
                    "full_name": full_name,
                    "phone": phone,
                    "location": location,
                    "avatar_url": avatar_url,
                })
                st.success("Profile updated!")
            except Exception as e:
                st.error(f"Update failed: {e}")
