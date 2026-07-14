"""
Notifications tab — visible to all roles.

Two sub-tabs:
  • 🔔 Notifications — system + admin broadcasts (read/unread)
  • 💬 Messages      — direct messages between users

Admins get an extra "📣 Broadcast" sub-tab to send notifications to all users.
"""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user, get_current_role
from database.connection import get_supabase_client, get_supabase_admin_client
from utils.ui import page_header, role_badge
from utils.helpers import format_datetime


def render_notifications():
    page_header("🔔 Notifications & Messages", "Stay in touch with the platform and other users")

    user = get_current_user()
    role = get_current_role()
    if not user:
        return

    if role == "admin":
        sub1, sub2, sub3 = st.tabs(["🔔 Notifications", "💬 Messages", "📣 Broadcast"])
        with sub1:
            _render_notification_list(user)
        with sub2:
            _render_messages(user)
        with sub3:
            _render_broadcast(user)
    else:
        sub1, sub2 = st.tabs(["🔔 Notifications", "💬 Messages"])
        with sub1:
            _render_notification_list(user)
        with sub2:
            _render_messages(user)


# ---------------------------------------------------------------------------
# NOTIFICATIONS (system + admin broadcasts)
# ---------------------------------------------------------------------------
def _render_notification_list(user: dict):
    st.markdown("##### Your Notifications")
    try:
        client = get_supabase_client()
        notifications = (
            client.table("notifications")
            .select("*")
            .eq("user_id", user["id"])
            .order("created_at", desc=True)
            .execute()
        ).data or []
    except Exception as e:
        st.error(f"Failed to load notifications: {e}")
        return

    unread = [n for n in notifications if not n.get("is_read")]
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric("Unread", len(unread))
    with col2:
        if unread and st.button("✓ Mark all read"):
            try:
                for n in unread:
                    client.table("notifications").update({"is_read": True}).eq("id", n["id"]).execute()
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")

    if not notifications:
        st.info("No notifications yet.")
        return

    for n in notifications:
        type_icon = {
            "info": "ℹ️", "warning": "⚠️", "error": "🚨", "success": "✅"
        }.get(n.get("type", "info"), "ℹ️")

        bg = "#fef3c7" if not n.get("is_read") else "#f8fafc"
        border = "#f59e0b" if not n.get("is_read") else "#e2e8f0"

        with st.container(border=True):
            st.markdown(
                f"<div style='background:{bg}; padding:0.5rem; border-left:3px solid {border}; "
                f"border-radius:4px;'>"
                f"<strong>{type_icon} {n.get('title', '')}</strong> "
                f"<span style='color:#64748b; font-size:0.8rem; float:right;'>{format_datetime(n.get('created_at'))}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if n.get("message"):
                st.markdown(n["message"])
            if n.get("link"):
                st.markdown(f"🔗 [{n['link']}]({n['link']})")

            if not n.get("is_read"):
                if st.button("Mark as read", key=f"read_{n['id']}"):
                    try:
                        client.table("notifications").update({"is_read": True}).eq("id", n["id"]).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")


# ---------------------------------------------------------------------------
# MESSAGES (user-to-user direct)
# ---------------------------------------------------------------------------
def _render_messages(user: dict):
    st.markdown("##### Direct Messages")

    try:
        client = get_supabase_client()
        # Fetch users we can message (everyone except self)
        all_users = client.table("profiles").select("id, full_name, email, role").neq("id", user["id"]).execute().data or []
        # Fetch conversations: messages I sent or received
        sent = client.table("messages").select("*").eq("sender_id", user["id"]).order("created_at", desc=True).execute().data or []
        received = client.table("messages").select("*").eq("receiver_id", user["id"]).order("created_at", desc=True).execute().data or []
        all_msgs = sorted(sent + received, key=lambda x: x.get("created_at", ""), reverse=True)
    except Exception as e:
        st.error(f"Failed to load messages: {e}")
        return

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("###### ✉️ Send a Message")
        with st.form("send_message_form"):
            receiver_options = {f"{u['full_name']} ({u['email']})": u["id"] for u in all_users}
            receiver_label = st.selectbox("To", list(receiver_options.keys()))
            subject = st.text_input("Subject", value=st.session_state.get("pending_message_subject", ""))
            body = st.text_area("Message", height=120)
            submitted = st.form_submit_button("Send", type="primary")

            if submitted:
                if not body.strip():
                    st.error("Message body cannot be empty.")
                else:
                    try:
                        client.table("messages").insert({
                            "sender_id": user["id"],
                            "receiver_id": receiver_options[receiver_label],
                            "subject": subject,
                            "body": body,
                        }).execute()
                        st.success("Message sent!")
                        st.session_state.pop("pending_message_subject", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to send: {e}")

    with col2:
        st.markdown("###### 📨 Inbox")
        if not all_msgs:
            st.info("No messages yet. Send your first message on the left!")
        else:
            user_map = {u["id"]: u for u in all_users}
            user_map[user["id"]] = user
            for m in all_msgs[:20]:
                sender = user_map.get(m["sender_id"], {})
                is_received = m["receiver_id"] == user["id"]
                direction = "📥 from" if is_received else "📤 to"
                other = user_map.get(m["sender_id"] if is_received else m["receiver_id"], {})

                bg = "#eff6ff" if is_received else "#f0fdf4"
                with st.container(border=True):
                    st.markdown(
                        f"<div style='background:{bg}; padding:0.5rem; border-radius:4px;'>"
                        f"<strong>{direction} {other.get('full_name', '?')}</strong> "
                        f"{role_badge(other.get('role', ''))} "
                        f"<span style='color:#64748b; font-size:0.8rem; float:right;'>{format_datetime(m.get('created_at'))}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if m.get("subject"):
                        st.markdown(f"**{m['subject']}**")
                    st.markdown(m.get("body", ""))
                    if is_received and not m.get("is_read"):
                        if st.button("Mark read", key=f"msg_read_{m['id']}"):
                            try:
                                client.table("messages").update({
                                    "is_read": True, "read_at": "now()"
                                }).eq("id", m["id"]).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")


# ---------------------------------------------------------------------------
# ADMIN BROADCAST
# ---------------------------------------------------------------------------
def _render_broadcast(admin: dict):
    st.markdown("##### 📣 Admin Broadcast")
    st.warning("This sends a notification to EVERY user on the platform. Use with care.")

    with st.form("broadcast_form"):
        col1, col2 = st.columns([2, 1])
        with col1:
            title = st.text_input("Title *", placeholder="e.g. Scheduled maintenance window")
        with col2:
            ntype = st.selectbox("Type", ["info", "warning", "error", "success"])
        message = st.text_area("Message *", height=120)
        link = st.text_input("Link (optional)", placeholder="/dashboard/...")

        submitted = st.form_submit_button("📢 Broadcast to all users", type="primary")

        if submitted:
            if not title or not message:
                st.error("Title and message are required.")
            else:
                try:
                    admin_client = get_supabase_admin_client()
                    # Fetch all user IDs
                    all_users = admin_client.table("profiles").select("id").execute().data or []
                    if not all_users:
                        st.error("No users found.")
                    else:
                        rows = [{
                            "user_id": u["id"],
                            "sender_id": admin["id"],
                            "title": title,
                            "message": message,
                            "type": ntype,
                            "link": link or None,
                        } for u in all_users]
                        r = admin_client.table("notifications").insert(rows).execute()
                        st.success(f"✅ Broadcast sent to {len(r.data)} users!")
                except Exception as e:
                    st.error(f"Broadcast failed: {e}")
