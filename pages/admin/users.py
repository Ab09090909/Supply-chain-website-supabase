"""Admin user management."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_admin_client, get_supabase_client
from utils.ui import page_header, role_badge
from utils.helpers import format_datetime
from utils.db_health import render_db_health_warning


def render_admin_users():
    page_header("User Management", "View, search, and manage all platform users")

    user = get_current_user()
    if not user:
        return

    # Try admin client first; fall back to anon client (RLS-limited)
    try:
        client = get_supabase_admin_client()
    except Exception:
        client = get_supabase_client()

    try:
        users = client.table("profiles").select("*").order("created_at", desc=True).execute().data or []
    except Exception as e:
        err = str(e)
        if "401" in err or "Invalid API key" in err or "invalid api key" in err.lower():
            st.error("❌ Admin access failed: Invalid Supabase API key.")
            st.info(
                "**To fix this:** Check your Supabase credentials in Streamlit secrets.\n\n"
                "The User Management page needs the **service_role key** (`SUPABASE_SERVICE_ROLE_KEY`) "
                "to see all users. Without it, RLS restricts you to seeing only your own profile.\n\n"
                "Get the service_role key from: **Supabase Dashboard → Project Settings → API**"
            )
        elif "PGRST205" in err or "could not find" in err.lower():
            st.error("❌ Database tables are missing.")
            st.info("Run `supabase/schema.sql` in your Supabase SQL Editor first.")
            render_db_health_warning()
        else:
            st.error(f"Failed to load users: {e}")
        return

    # Filters
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 Search by name or email", placeholder="Search...")
    with col2:
        role_filter = st.selectbox("Filter by role", ["All", "producer", "merchant", "customer", "admin"])

    filtered = [
        u for u in users
        if (not search or search.lower() in u.get("email", "").lower() or search.lower() in u.get("full_name", "").lower())
        and (role_filter == "All" or u.get("role") == role_filter)
    ]

    st.markdown(f"###### {len(filtered)} user(s)")

    for u in filtered:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
            with col1:
                st.markdown(f"**{u.get('full_name', '—')}**")
                st.caption(u.get("email", ""))
            with col2:
                st.markdown(role_badge(u.get("role", "")), unsafe_allow_html=True)
                st.caption(f"Joined {format_datetime(u.get('created_at'), '%Y-%m-%d')}")
            with col3:
                st.metric("Active", "✅" if u.get("is_active") else "❌")
            with col4:
                st.metric("Verified", "✅" if u.get("is_verified") else "❌")
            with col5:
                if u.get("id") == user["id"]:
                    st.caption("You")
                else:
                    new_status = not u.get("is_active", True)
                    if st.button(
                        "Deactivate" if u.get("is_active") else "Activate",
                        key=f"toggle_{u['id']}"
                    ):
                        try:
                            client.table("profiles").update({
                                "is_active": new_status
                            }).eq("id", u["id"]).execute()
                            st.success(f"User {'activated' if new_status else 'deactivated'}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
