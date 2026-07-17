"""Admin profile page — avatar upload + account details."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client, get_supabase_admin_client
from utils.ui import page_header
from utils.storage import render_image_uploader


def _get_writer():
    """Get the best client for writes — admin bypasses RLS, falls back to anon."""
    try:
        return get_supabase_admin_client()
    except Exception:
        return get_supabase_client()


def render_admin_profile():
    page_header("Admin Profile", "Manage your admin account")

    user = get_current_user()
    if not user:
        return

    # ---- Avatar image upload (auto-saves to DB) ----
    st.markdown("##### Profile Photo")
    avatar_url, avatar_err = render_image_uploader(
        label="Upload new avatar",
        folder="avatars",
        current_url=user.get("avatar_url"),
        key="avatar_uploader_admin",
    )

    # If a new avatar was uploaded (and there's no error), immediately
    # save the URL to the profile row and refresh the session. This
    # way the user doesn't have to click "Save changes" for the avatar
    # to actually persist.
    if avatar_url and avatar_url != user.get("avatar_url") and not avatar_err:
        try:
            writer = _get_writer()
            writer.table("profiles").update({"avatar_url": avatar_url}).eq("id", user["id"]).execute()
            st.session_state["user"]["avatar_url"] = avatar_url
            st.success("✅ Avatar updated!")
            st.rerun()
        except Exception as e:
            st.error(f"Avatar save failed: {e}")

    st.markdown("---")

    # ---- Account details form ----
    with st.form("admin_profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full name", value=user.get("full_name", ""))
            email = st.text_input("Email", value=user.get("email", ""), disabled=True)
        with col2:
            phone = st.text_input("Phone", value=user.get("phone", "") or "")
            location = st.text_input("Location", value=user.get("location", "") or "")

        submitted = st.form_submit_button("Save changes", type="primary")
        if submitted:
            try:
                writer = _get_writer()
                writer.table("profiles").update({
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
                st.rerun()
            except Exception as e:
                st.error(f"Update failed: {e}")

    # ---- Digital business card + QR code (offline, downloadable) ----
    try:
        from utils.business_card import render_business_card
        render_business_card(user)
    except Exception as e:
        st.error(f"Business card unavailable: {e}")
