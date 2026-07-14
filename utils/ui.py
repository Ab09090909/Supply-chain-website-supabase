"""
Shared UI helpers — modern, compact, attractive design.

Design principles (matching the reference):
  • Compact cards with 12px padding (not 20px)
  • Small icons (20-24px) aligned with text
  • Clear visual hierarchy: label (small) → value (large, colored) → description (small)
  • Rounded corners (8px)
  • Subtle borders, minimal shadows
  • Consistent spacing (12px gaps)
"""
from __future__ import annotations

from datetime import datetime
import streamlit as st

from .constants import ROLE_COLORS, ROLE_LABELS


def page_header(title: str, subtitle: str = "") -> None:
    """Render a compact page header."""
    st.markdown(
        f"""
        <div style='margin-bottom: 1rem; padding: 0.5rem 0;'>
            <h1 style='font-size: 1.5rem; font-weight: 700; color: #0f172a; margin: 0; line-height: 1.2;'>{title}</h1>
            {f"<p style='color: #64748b; font-size: 0.875rem; margin: 0.25rem 0 0 0;'>{subtitle}</p>" if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def role_badge(role: str) -> str:
    """Return HTML for a compact colored role badge."""
    color = ROLE_COLORS.get(role, "#64748b")
    label = ROLE_LABELS.get(role, role.capitalize())
    return (
        f"<span style='display:inline-block; padding:0.2rem 0.6rem; "
        f"border-radius:9999px; font-size:0.7rem; font-weight:600; "
        f"background:{color}15; color:{color}; border:1px solid {color}30;'>{label}</span>"
    )


def metric_card(label: str, value: str, delta: str = "", color: str = "#10b981", icon: str = "") -> None:
    """Render a compact KPI metric card — modern style.

    Args:
        label: Small uppercase label (e.g. "Total Users")
        value: Large bold value (e.g. "10")
        delta: Optional small delta text (e.g. "+2 this week")
        color: Accent color for the value
        icon: Optional emoji icon (e.g. "👥")
    """
    delta_html = f"<div style='font-size:0.7rem; color:#10b981; margin-top:0.25rem; font-weight:500;'>{delta}</div>" if delta else ""
    icon_html = f"<span style='font-size:1.1rem; margin-right:0.4rem;'>{icon}</span>" if icon else ""
    st.markdown(
        f"""
        <div style='padding:0.875rem 1rem; border-radius:10px; background:#ffffff;
                    border:1px solid #e5e7eb; box-shadow:0 1px 2px rgba(0,0,0,0.03);
                    transition: all 0.2s ease;'>
            <div style='font-size:0.7rem; color:#6b7280; text-transform:uppercase;
                        letter-spacing:0.03em; font-weight:500; display:flex; align-items:center;'>
                {icon_html}{label}
            </div>
            <div style='font-size:1.5rem; font-weight:700; color:{color}; margin-top:0.15rem; line-height:1.2;'>{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, color: str = "#10b981", icon: str = "") -> None:
    """Render a compact stat card with colored left accent."""
    icon_html = f"<span style='font-size:1rem; margin-right:0.35rem;'>{icon}</span>" if icon else ""
    st.markdown(
        f"""
        <div style='padding:0.75rem 0.875rem; border-radius:8px; background:#ffffff;
                    border-left:3px solid {color}; border-top:1px solid #e5e7eb;
                    border-right:1px solid #e5e7eb; border-bottom:1px solid #e5e7eb;
                    box-shadow:0 1px 2px rgba(0,0,0,0.03);'>
            <div style='font-size:0.7rem; color:#6b7280; font-weight:500; display:flex; align-items:center;'>
                {icon_html}{label}
            </div>
            <div style='font-size:1.25rem; font-weight:700; color:#0f172a; margin-top:0.1rem; line-height:1.2;'>{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_user_card(user: dict) -> None:
    """Render a compact user info card in the sidebar."""
    name = user.get("full_name", "User")
    email = user.get("email", "")
    role = user.get("role", "")
    avatar_url = user.get("avatar_url")

    if avatar_url:
        avatar_html = (
            f"<img src='{avatar_url}' "
            f"style='width:36px; height:36px; border-radius:50%; object-fit:cover; "
            f"border:2px solid {ROLE_COLORS.get(role, '#64748b')};' />"
        )
    else:
        avatar_html = (
            f"<div style='width:36px; height:36px; border-radius:50%;"
            f"background:{ROLE_COLORS.get(role, '#64748b')};"
            f"color:white; display:flex; align-items:center; justify-content:center;"
            f"font-weight:700; font-size:0.9rem;'>"
            f"{name[0].upper() if name else 'U'}</div>"
        )

    st.markdown(
        f"""
        <div style='padding:0.75rem; border-radius:10px; background:#f8fafc; margin-bottom:0.75rem; border:1px solid #e5e7eb;'>
            <div style='display:flex; align-items:center; gap:0.6rem;'>
                {avatar_html}
                <div style='min-width:0; flex:1;'>
                    <div style='font-weight:600; color:#0f172a; font-size:0.85rem;
                                white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>
                        {name}
                    </div>
                    <div style='font-size:0.7rem; color:#64748b;
                                white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>
                        {email}
                    </div>
                </div>
            </div>
            <div style='margin-top:0.5rem;'>{role_badge(role)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def compact_info_card(icon: str, title: str, value: str, description: str = "", color: str = "#10b981") -> None:
    """Render a compact info card with icon + title + value + description.

    This matches the reference design: small card, icon on left,
    title + value in middle, optional description below.
    """
    st.markdown(
        f"""
        <div style='padding:0.875rem 1rem; border-radius:10px; background:#ffffff;
                    border:1px solid #e5e7eb; box-shadow:0 1px 2px rgba(0,0,0,0.03);
                    display:flex; align-items:center; gap:0.75rem; transition: all 0.2s ease;'>
            <div style='font-size:1.5rem; line-height:1;'>{icon}</div>
            <div style='flex:1; min-width:0;'>
                <div style='font-size:0.75rem; color:#6b7280; font-weight:500;'>{title}</div>
                <div style='font-size:1.25rem; font-weight:700; color:{color}; line-height:1.2; margin-top:0.1rem;'>{value}</div>
                {f"<div style='font-size:0.7rem; color:#9ca3af; margin-top:0.15rem;'>{description}</div>" if description else ""}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    """Return HTML for a compact status badge."""
    status_map = {
        "pending": ("⏳", "#f59e0b"),
        "verified": ("✅", "#10b981"),
        "rejected": ("❌", "#ef4444"),
        "active": ("🟢", "#10b981"),
        "inactive": ("⚫", "#6b7280"),
        "delivered": ("📦", "#059669"),
        "shipped": ("🚚", "#8b5cf6"),
        "confirmed": ("✅", "#10b981"),
        "processing": ("🔄", "#3b82f6"),
        "cancelled": ("❌", "#ef4444"),
    }
    icon, color = status_map.get(status.lower(), ("❓", "#6b7280"))
    return (
        f"<span style='display:inline-block; padding:0.2rem 0.6rem; "
        f"border-radius:6px; font-size:0.7rem; font-weight:600; "
        f"background:{color}15; color:{color}; border:1px solid {color}30;'>"
        f"{icon} {status.title()}</span>"
    )


def show_success_toast(message: str) -> None:
    st.toast(message, icon="✅")


def show_error_message(message: str) -> None:
    st.error(message)


def show_info_message(message: str) -> None:
    st.info(message)
