"""
Modern UI Design System — professional, attractive, consistent.

Design tokens:
  • Colors: emerald primary, slate neutrals, semantic colors
  • Spacing: 4/8/12/16/24px scale
  • Radius: 8/12px
  • Shadows: subtle, layered
  • Typography: system sans-serif, clear hierarchy
"""
from __future__ import annotations

from datetime import datetime
import streamlit as st

from .constants import ROLE_COLORS, ROLE_LABELS


# ============================================================
# DESIGN TOKENS
# ============================================================
COLORS = {
    "primary": "#10b981",
    "primary_dark": "#059669",
    "primary_light": "#d1fae5",
    "slate_900": "#0f172a",
    "slate_700": "#334155",
    "slate_500": "#64748b",
    "slate_400": "#94a3b8",
    "slate_300": "#cbd5e1",
    "slate_200": "#e2e8f0",
    "slate_100": "#f1f5f9",
    "slate_50": "#f8fafc",
    "white": "#ffffff",
    "amber": "#f59e0b",
    "amber_light": "#fef3c7",
    "red": "#ef4444",
    "red_light": "#fee2e2",
    "blue": "#3b82f6",
    "blue_light": "#dbeafe",
    "purple": "#8b5cf6",
    "purple_light": "#ede9fe",
}

GRADIENTS = {
    "emerald": "linear-gradient(135deg, #34d399 0%, #10b981 100%)",
    "blue": "linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)",
    "purple": "linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%)",
    "amber": "linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)",
    "red": "linear-gradient(135deg, #f87171 0%, #ef4444 100%)",
    "teal": "linear-gradient(135deg, #2dd4bf 0%, #14b8a6 100%)",
    "pink": "linear-gradient(135deg, #f472b6 0%, #ec4899 100%)",
    "indigo": "linear-gradient(135deg, #818cf8 0%, #6366f1 100%)",
}

ICON_GRADIENTS = {
    "📦": "emerald", "⚠️": "amber", "💰": "emerald", "⏳": "amber",
    "👥": "blue", "🚨": "red", "📜": "purple", "🛒": "teal",
    "📈": "indigo", "🎯": "pink", "🤝": "blue", "📨": "purple",
    "✅": "emerald", "❌": "red", "🔄": "blue", "🚚": "purple",
    "🔔": "amber", "💬": "teal", "🤖": "indigo", "🔐": "red",
    "📊": "blue", "⚙️": "slate",
}


# ============================================================
# PAGE HEADER
# ============================================================
def page_header(title: str, subtitle: str = "") -> None:
    """Render a clean page header with title + subtitle."""
    st.markdown(
        f"""
        <div style='margin-bottom: 1rem; padding: 0.5rem 0;'>
            <h1 style='font-size: 1.5rem; font-weight: 700; color: {COLORS['slate_900']};
                       margin: 0; line-height: 1.2; letter-spacing: -0.01em;'>{title}</h1>
            {f"<p style='color: {COLORS['slate_500']}; font-size: 0.875rem; margin: 0.25rem 0 0 0;'>{subtitle}</p>" if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# ROLE BADGE
# ============================================================
def role_badge(role: str) -> str:
    """Return HTML for a colored role badge."""
    color = ROLE_COLORS.get(role, "#64748b")
    label = ROLE_LABELS.get(role, role.capitalize())
    return (
        f"<span style='display:inline-block; padding:0.2rem 0.6rem; "
        f"border-radius:9999px; font-size:0.7rem; font-weight:600; "
        f"background:{color}15; color:{color}; border:1px solid {color}30;'>{label}</span>"
    )


# ============================================================
# METRIC CARD — horizontal grid card with gradient icon
# ============================================================
def metric_card(label: str, value: str, delta: str = "", color: str = "#10b981", icon: str = "") -> None:
    """Render a modern metric card — gradient icon + large value + small label.

    Designed for horizontal grid layout (3-4 cards per row).

    Implementation note (v6.1): the previous version used a complex
    ``display:flex; flex-direction:column;`` HTML structure that looked
    great on desktop but **collapsed to 0 height on mobile/narrow
    viewports** (and on some older Streamlit builds the inner content
    was rendered as visible HTML text instead of as HTML). The fix is
    to use Streamlit's native ``st.metric`` component (which is
    mobile-safe, accessible, and never breaks) wrapped with a thin
    accent bar so the card still has visual identity.
    """
    gradient = GRADIENTS.get(ICON_GRADIENTS.get(icon, "emerald"), GRADIENTS["emerald"])

    # 3px accent bar at the top of the card — single inline-style div,
    # sanitiser-safe (no `style=` with quotes that could trip up old
    # renderers).  The bar is in the primary color of the chosen icon.
    st.markdown(
        f'<div style="height:3px;background:{gradient};'
        f'border-radius:6px 6px 0 0;margin-bottom:1px;"></div>',
        unsafe_allow_html=True,
    )

    # Native Streamlit metric — bulletproof, mobile-safe, accessible.
    # Icon is prepended to the label so the visual hierarchy stays.
    st.metric(
        label=f"{icon}  {label}" if icon else label,
        value=value,
        delta=delta if delta else None,
    )


def stat_card(label: str, value: str, color: str = "#10b981", icon: str = "") -> None:
    """Alias for metric_card."""
    metric_card(label, value, color=color, icon=icon)


# ============================================================
# SIDEBAR USER CARD
# ============================================================
def sidebar_user_card(user: dict) -> None:
    """Render a compact user info card in the sidebar."""
    name = user.get("full_name", "User")
    email = user.get("email", "")
    role = user.get("role", "")
    avatar_url = user.get("avatar_url")
    color = ROLE_COLORS.get(role, "#64748b")

    if avatar_url:
        avatar_html = (
            f"<img src='{avatar_url}' "
            f"style='width:40px; height:40px; border-radius:50%; object-fit:cover; "
            f"border:2px solid {color};' />"
        )
    else:
        avatar_html = (
            f"<div style='width:40px; height:40px; border-radius:50%;"
            f"background:{color}; color:white; display:flex; align-items:center; "
            f"justify-content:center; font-weight:700; font-size:1rem;'>"
            f"{name[0].upper() if name else 'U'}</div>"
        )

    st.markdown(
        f"""
        <div style='padding:0.875rem; border-radius:12px; background:{COLORS["slate_50"]};
                    margin-bottom:0.75rem; border:1px solid {COLORS["slate_200"]};'>
            <div style='display:flex; align-items:center; gap:0.75rem;'>
                {avatar_html}
                <div style='min-width:0; flex:1;'>
                    <div style='font-weight:600; color:{COLORS["slate_900"]}; font-size:0.875rem;
                                white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>
                        {name}
                    </div>
                    <div style='font-size:0.7rem; color:{COLORS["slate_500"]};
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


# ============================================================
# COMPACT INFO CARD — full-width horizontal card
# ============================================================
def compact_info_card(icon: str, title: str, value: str, description: str = "", color: str = "#10b981") -> None:
    """Render a full-width info card with gradient icon + title + value."""
    gradient_name = ICON_GRADIENTS.get(icon, "emerald")
    gradient = GRADIENTS.get(gradient_name, GRADIENTS["emerald"])
    st.markdown(
        f"""
        <div style='padding:0.875rem 1rem; border-radius:12px; background:{COLORS["white"]};
                    border:1px solid {COLORS["slate_200"]};
                    box-shadow:0 1px 3px rgba(0,0,0,0.04);
                    display:flex; align-items:center; gap:0.875rem; margin-bottom:0.5rem;'>
            <div style='width:44px; height:44px; border-radius:12px;
                        background:{gradient}; display:flex; align-items:center;
                        justify-content:center; font-size:1.3rem; flex-shrink:0;
                        box-shadow:0 4px 12px rgba(0,0,0,0.1);'>
                {icon}
            </div>
            <div style='flex:1; min-width:0;'>
                <div style='font-size:0.7rem; color:{COLORS["slate_500"]}; font-weight:600;
                            text-transform:uppercase; letter-spacing:0.04em;'>{title}</div>
                <div style='font-size:1.2rem; font-weight:700; color:{COLORS["slate_900"]}; line-height:1.2;'>{value}</div>
                {f"<div style='font-size:0.7rem; color:{COLORS['slate_400']}; margin-top:0.1rem;'>{description}</div>" if description else ""}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# STATUS BADGE
# ============================================================
def status_badge(status: str) -> str:
    """Return HTML for a compact status badge."""
    status_map = {
        "pending": ("⏳", COLORS["amber"]),
        "verified": ("✅", COLORS["primary"]),
        "rejected": ("❌", COLORS["red"]),
        "active": ("🟢", COLORS["primary"]),
        "inactive": ("⚫", COLORS["slate_500"]),
        "delivered": ("📦", COLORS["primary_dark"]),
        "shipped": ("🚚", COLORS["purple"]),
        "confirmed": ("✅", COLORS["primary"]),
        "processing": ("🔄", COLORS["blue"]),
        "cancelled": ("❌", COLORS["red"]),
    }
    icon, color = status_map.get(status.lower(), ("❓", COLORS["slate_500"]))
    return (
        f"<span style='display:inline-block; padding:0.2rem 0.6rem; "
        f"border-radius:6px; font-size:0.7rem; font-weight:600; "
        f"background:{color}15; color:{color}; border:1px solid {color}30;'>"
        f"{icon} {status.title()}</span>"
    )


# ============================================================
# TOAST / ERROR / INFO
# ============================================================
def show_success_toast(message: str) -> None:
    st.toast(message, icon="✅")


def show_error_message(message: str) -> None:
    st.error(message)


def show_info_message(message: str) -> None:
    st.info(message)
