"""Shared UI helpers for consistent styling across pages."""
from __future__ import annotations

from datetime import datetime
import streamlit as st

from .constants import ROLE_COLORS, ROLE_LABELS


def page_header(title: str, subtitle: str = "") -> None:
    """Render a consistent page header."""
    st.markdown(
        f"""
        <div style='margin-bottom: 1.5rem;'>
            <h1 style='font-size: 1.75rem; font-weight: 700; color: #0f172a; margin: 0;'>{title}</h1>
            {f"<p style='color: #64748b; font-size: 0.95rem; margin: 0.25rem 0 0 0;'>{subtitle}</p>" if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def role_badge(role: str) -> str:
    """Return HTML for a colored role badge."""
    color = ROLE_COLORS.get(role, "#64748b")
    label = ROLE_LABELS.get(role, role.capitalize())
    return (
        f"<span style='display:inline-block; padding:0.25rem 0.75rem; "
        f"border-radius:9999px; font-size:0.75rem; font-weight:600; "
        f"background:{color}22; color:{color}; border:1px solid {color}44;'>{label}</span>"
    )


def metric_card(label: str, value: str, delta: str = "", color: str = "#0f172a") -> None:
    """Render a KPI metric card."""
    delta_html = f"<div style='font-size:0.8rem; color:#10b981; margin-top:0.25rem;'>{delta}</div>" if delta else ""
    st.markdown(
        f"""
        <div style='padding:1.25rem; border-radius:12px; background:#ffffff;
                    border:1px solid #e2e8f0; box-shadow:0 1px 3px rgba(0,0,0,0.04);'>
            <div style='font-size:0.8rem; color:#64748b; text-transform:uppercase; letter-spacing:0.05em;'>{label}</div>
            <div style='font-size:1.75rem; font-weight:700; color:{color}; margin-top:0.25rem;'>{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, color: str = "#10b981") -> None:
    """Render a smaller stat card with colored accent."""
    st.markdown(
        f"""
        <div style='padding:1rem; border-radius:10px; background:#ffffff;
                    border-left:4px solid {color}; border-top:1px solid #e2e8f0;
                    border-right:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0;'>
            <div style='font-size:0.75rem; color:#64748b;'>{label}</div>
            <div style='font-size:1.5rem; font-weight:700; color:#0f172a; margin-top:0.15rem;'>{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_user_card(user: dict) -> None:
    """Render a user info card in the sidebar — shows the avatar image if set."""
    name = user.get("full_name", "User")
    email = user.get("email", "")
    role = user.get("role", "")
    avatar_url = user.get("avatar_url")

    # If avatar URL is set, show the image; otherwise show initials circle
    if avatar_url:
        avatar_html = (
            f"<img src='{avatar_url}' "
            f"style='width:40px; height:40px; border-radius:50%; object-fit:cover; "
            f"border:2px solid {ROLE_COLORS.get(role, '#64748b')};' />"
        )
    else:
        avatar_html = (
            f"<div style='width:40px; height:40px; border-radius:50%;"
            f"background:{ROLE_COLORS.get(role, '#64748b')};"
            f"color:white; display:flex; align-items:center; justify-content:center;"
            f"font-weight:700; font-size:1rem;'>"
            f"{name[0].upper() if name else 'U'}</div>"
        )

    st.markdown(
        f"""
        <div style='padding:1rem; border-radius:12px; background:#f8fafc; margin-bottom:1rem;'>
            <div style='display:flex; align-items:center; gap:0.75rem;'>
                {avatar_html}
                <div style='min-width:0; flex:1;'>
                    <div style='font-weight:600; color:#0f172a; font-size:0.95rem;
                                white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>
                        {name}
                    </div>
                    <div style='font-size:0.75rem; color:#64748b;
                                white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>
                        {email}
                    </div>
                </div>
            </div>
            <div style='margin-top:0.75rem;'>{role_badge(role)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_success_toast(message: str) -> None:
    st.toast(message, icon="✅")


def show_error_message(message: str) -> None:
    st.error(message)


def show_info_message(message: str) -> None:
    st.info(message)
