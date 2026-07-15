"""
Shared UI helpers — modern horizontal grid card design.

Design (matching reference):
  • Horizontal grid of cards (3-4 per row)
  • Each card: gradient icon + large number + small label
  • Compact 120px height, 12px radius
  • Clean cards adapting to light/dark theme
"""
from __future__ import annotations

from datetime import datetime
import streamlit as st

from .constants import ROLE_COLORS, ROLE_LABELS


# ── Theme tokens ──────────────────────────────────────────────────────────────
def _t() -> dict:
    """Return color tokens for the current theme."""
    dark = st.session_state.get("dark_mode", False)
    if dark:
        return {
            "bg":        "#1E293B",   # card background
            "border":    "#2D3F55",   # card border
            "text_pri":  "#F1F5F9",   # value text
            "text_sec":  "#94A3B8",   # label text
            "text_head": "#F1F5F9",   # page title
            "text_sub":  "#64748B",   # page subtitle
            "info_bg":   "#0F172A",   # sidebar card bg
            "info_bdr":  "#2D3F55",
        }
    return {
        "bg":        "#ffffff",
        "border":    "#e5e7eb",
        "text_pri":  "#0f172a",
        "text_sec":  "#6b7280",
        "text_head": "#0f172a",
        "text_sub":  "#64748b",
        "info_bg":   "#f8fafc",
        "info_bdr":  "#e5e7eb",
    }


def page_header(title: str, subtitle: str = "") -> None:
    """Render a page header — title + subtitle."""
    t = _t()
    st.markdown(
        f"""
        <div style='margin-bottom: 0.75rem; padding: 0.5rem 0;'>
            <h1 style='font-size: 1.4rem; font-weight: 700; color: {t["text_head"]}; margin: 0; line-height: 1.2;'>{title}</h1>
            {f"<p style='color: {t['text_sub']}; font-size: 0.85rem; margin: 0.2rem 0 0 0;'>{subtitle}</p>" if subtitle else ""}
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


# Gradient color schemes for metric cards
GRADIENTS = {
    "emerald": "linear-gradient(135deg, #34d399 0%, #10b981 100%)",
    "blue":    "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
    "purple":  "linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%)",
    "amber":   "linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)",
    "red":     "linear-gradient(135deg, #f87171 0%, #ef4444 100%)",
    "teal":    "linear-gradient(135deg, #2dd4bf 0%, #14b8a6 100%)",
    "pink":    "linear-gradient(135deg, #f472b6 0%, #ec4899 100%)",
    "indigo":  "linear-gradient(135deg, #818cf8 0%, #6366f1 100%)",
}

ICON_GRADIENTS = {
    "📦": "emerald", "⚠️": "amber",  "💰": "emerald", "⏳": "amber",
    "👥": "blue",    "🚨": "red",    "📜": "purple",  "🛒": "teal",
    "📈": "indigo",  "🎯": "pink",   "🤝": "blue",    "📨": "purple",
    "✅": "emerald", "❌": "red",    "🔄": "blue",    "🚚": "purple",
}


def metric_card(label: str, value: str, delta: str = "", color: str = "#10b981", icon: str = "") -> None:
    """Render a horizontal grid metric card — gradient icon + large number + small label."""
    t = _t()
    delta_html = (
        f"<div style='font-size:0.65rem; color:#10b981; margin-top:0.15rem; font-weight:500;'>{delta}</div>"
        if delta else ""
    )

    gradient_name = ICON_GRADIENTS.get(icon, "emerald")
    gradient = GRADIENTS.get(gradient_name, GRADIENTS["emerald"])

    icon_html = ""
    if icon:
        icon_html = f"""
        <div style='width:36px; height:36px; border-radius:50%;
                    background:{gradient}; display:flex; align-items:center;
                    justify-content:center; font-size:1rem; margin-bottom:0.4rem;
                    box-shadow:0 2px 8px rgba(0,0,0,0.15);'>
            {icon}
        </div>
        """

    st.markdown(
        f"""
        <div style='padding:0.875rem; border-radius:12px;
                    background:{t["bg"]}; border:1px solid {t["border"]};
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);
                    text-align:left; min-height:110px;
                    display:flex; flex-direction:column; justify-content:space-between;'>
            {icon_html}
            <div>
                <div style='font-size:1.5rem; font-weight:700; color:{t["text_pri"]};
                            line-height:1.1; margin-bottom:0.1rem;'>{value}</div>
                <div style='font-size:0.7rem; color:{t["text_sec"]}; text-transform:uppercase;
                            letter-spacing:0.03em; font-weight:500; line-height:1.2;'>{label}</div>
                {delta_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, color: str = "#10b981", icon: str = "") -> None:
    """Render a compact stat card — alias for metric_card."""
    metric_card(label, value, color=color, icon=icon)


def sidebar_user_card(user: dict) -> None:
    """Render a compact user info card in the sidebar."""
    t = _t()
    name      = user.get("full_name", "User")
    email     = user.get("email", "")
    role      = user.get("role", "")
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
        <div style='padding:0.7rem; border-radius:8px;
                    background:{t["info_bg"]}; margin-bottom:0.6rem;
                    border:1px solid {t["info_bdr"]};'>
            <div style='display:flex; align-items:center; gap:0.6rem;'>
                {avatar_html}
                <div style='min-width:0; flex:1;'>
                    <div style='font-weight:600; color:{t["text_pri"]}; font-size:0.85rem;
                                white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>
                        {name}
                    </div>
                    <div style='font-size:0.7rem; color:{t["text_sec"]};
                                white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>
                        {email}
                    </div>
                </div>
            </div>
            <div style='margin-top:0.4rem;'>{role_badge(role)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def compact_info_card(icon: str, title: str, value: str, description: str = "", color: str = "#10b981") -> None:
    """Render a full-width info card with icon + title + value."""
    t = _t()
    gradient_name = ICON_GRADIENTS.get(icon, "emerald")
    gradient = GRADIENTS.get(gradient_name, GRADIENTS["emerald"])
    st.markdown(
        f"""
        <div style='padding:0.875rem; border-radius:12px;
                    background:{t["bg"]}; border:1px solid {t["border"]};
                    box-shadow:0 1px 3px rgba(0,0,0,0.06);
                    display:flex; align-items:center; gap:0.875rem; margin-bottom:0.5rem;'>
            <div style='width:40px; height:40px; border-radius:50%;
                        background:{gradient}; display:flex; align-items:center;
                        justify-content:center; font-size:1.2rem; flex-shrink:0;
                        box-shadow:0 2px 8px rgba(0,0,0,0.1);'>
                {icon}
            </div>
            <div style='flex:1; min-width:0;'>
                <div style='font-size:0.7rem; color:{t["text_sec"]}; font-weight:500;
                            text-transform:uppercase; letter-spacing:0.03em;'>{title}</div>
                <div style='font-size:1.2rem; font-weight:700; color:{t["text_pri"]}; line-height:1.2;'>{value}</div>
                {f"<div style='font-size:0.7rem; color:{t['text_sec']}; margin-top:0.1rem;'>{description}</div>" if description else ""}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    """Return HTML for a compact status badge."""
    status_map = {
        "pending":    ("⏳", "#f59e0b"),
        "verified":   ("✅", "#10b981"),
        "rejected":   ("❌", "#ef4444"),
        "active":     ("🟢", "#10b981"),
        "inactive":   ("⚫", "#6b7280"),
        "delivered":  ("📦", "#059669"),
        "shipped":    ("🚚", "#8b5cf6"),
        "confirmed":  ("✅", "#10b981"),
        "processing": ("🔄", "#3b82f6"),
        "cancelled":  ("❌", "#ef4444"),
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
