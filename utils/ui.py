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
import textwrap

from .constants import ROLE_COLORS, ROLE_LABELS


def _html(html: str) -> None:
    """Render a raw HTML string safely.

    Always use this instead of ``st.markdown(..., unsafe_allow_html=True)``
    for multi-line HTML. Why? ``st.markdown`` passes the content through a
    Markdown parser first, and an indented multi-line HTML string is
    sometimes mis-interpreted as a code block — which makes the raw
    ``<div>...</div>`` source appear as text on the page (the bug the
    user pasted in the screenshot).

    This helper:
      1. Strips leading whitespace from every line so there's no indented
         block that could be parsed as a Markdown code block.
      2. Uses ``st.html()`` (Streamlit 1.39+) which doesn't run the
         string through the Markdown parser at all.

    The result: HTML is always rendered as HTML, never as text.
    """
    cleaned = "\n".join(line.lstrip() for line in html.splitlines())
    try:
        st.html(cleaned)
    except AttributeError:
        st.markdown(cleaned, unsafe_allow_html=True)


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
def page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Render an attractive, animated page header with title + subtitle.

    Uses ``st.html()`` (Streamlit 1.39+) instead of
    ``st.markdown(..., unsafe_allow_html=True)`` because the markdown
    parser sometimes mis-interprets multi-line HTML f-strings as code
    blocks, which renders the raw HTML as visible text on the page.
    ``st.html()`` bypasses the markdown parser entirely so the styling
    is always applied.
    """
    icon_html = ""
    if icon:
        icon_html = (
            f"<div style='display:inline-flex;align-items:center;justify-content:center;"
            f"width:42px;height:42px;border-radius:12px;"
            f"background:linear-gradient(135deg,#10b981 0%,#34d399 50%,#6ee7b7 100%);"
            f"background-size:200% 200%;animation:gradientShift 6s ease infinite,bounceIn 0.5s ease-out;"
            f"font-size:1.4rem;box-shadow:0 4px 14px rgba(16,185,129,0.3);"
            f"margin-right:12px;vertical-align:middle;'>{icon}</div>"
        )

    subtitle_html = (
        f"<p style='color:#64748b;font-size:0.85rem;margin:0.25rem 0 0 0;font-weight:500;'>{subtitle}</p>"
        if subtitle else ""
    )

    # Single-line HTML — no internal newlines, no leading whitespace, no
    # markdown-confusing indentation.  ``st.html()`` (Streamlit 1.39+)
    # renders the string as raw HTML so this always works.
    _html(
        "<div style='margin:0 0 1.5rem 0;padding:1rem 1.25rem;"
        "background:linear-gradient(135deg,rgba(16,185,129,0.04) 0%,rgba(52,211,153,0.02) 100%);"
        "border-radius:14px;border:1px solid rgba(16,185,129,0.12);"
        "border-left:4px solid #10b981;"
        "position:relative;overflow:hidden;animation:fadeInDown 0.4s ease-out;'>"
        "<div style='display:flex;align-items:center;'>"
        + icon_html +
        "<div style='flex:1;min-width:0;'>"
        "<h1 style='font-size:1.5rem;font-weight:800;"
        "background:linear-gradient(135deg,#047857 0%,#10b981 60%,#34d399 100%);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"
        "margin:0;line-height:1.2;letter-spacing:-0.02em;'>"
        + str(title) +
        "</h1>"
        + subtitle_html +
        "</div>"
        "<div class='pulse-dot' style='flex-shrink:0;'></div>"
        "</div>"
        "</div>"
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

    _html(
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
        """
    )


# ============================================================
# COMPACT INFO CARD — full-width horizontal card
# ============================================================
def compact_info_card(icon: str, title: str, value: str, description: str = "", color: str = "#10b981") -> None:
    """Render a full-width info card with gradient icon + title + value."""
    gradient_name = ICON_GRADIENTS.get(icon, "emerald")
    gradient = GRADIENTS.get(gradient_name, GRADIENTS["emerald"])
    _html(
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
        """
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


# ============================================================
# ANIMATED SECTION HEADER
# ============================================================
def section_header(label: str, icon: str = "", color: str = "emerald") -> None:
    """Render an animated section header — small uppercase label with optional icon.

    Useful to separate logical sections of a page with a consistent look.
    """
    gradient = GRADIENTS.get(color, GRADIENTS["emerald"])
    icon_html = (
        f"<span style='display:inline-block; width:24px; height:24px; line-height:24px;"
        f"text-align:center; background:{gradient}; border-radius:6px; "
        f"font-size:0.8rem; margin-right:6px; box-shadow:0 2px 6px rgba(0,0,0,0.1);'>{icon}</span>"
        if icon else ""
    )
    _html(
        f"""
        <div style='
            display:flex; align-items:center; gap:4px;
            margin: 1.5rem 0 0.75rem 0;
            padding: 0.25rem 0;
            border-bottom: 2px solid;
            border-image: linear-gradient(90deg, {gradient.replace('linear-gradient', 'linear-gradient')} 0%, transparent 100%) 1;
            animation: fadeInLeft 0.4s ease-out;
        '>
            <span style='
                font-size: 0.72rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                color: #047857;
            '>{icon_html}{label}</span>
        </div>
        """
    )


# ============================================================
# KPI DASHBOARD GRID — 4 gradient cards in one row
# ============================================================
def kpi_dashboard(cards: list[dict]) -> None:
    """Render a row of colorful gradient KPI cards.

    Each card is a dict: ``{"label": str, "value": str, "icon": str, "color": str, "delta": str}``
    where ``color`` is one of the keys of ``GRADIENTS`` (emerald, blue,
    purple, amber, red, teal, pink, indigo) and ``delta`` is optional.

    The whole row is wrapped in a 1fr grid that adapts to up to 4 cards
    on desktop, 2 on tablet, 1 on mobile.
    """
    n = len(cards)
    if n == 0:
        return
    grid_cols = min(n, 4)

    html_cards = []
    for c in cards:
        label   = c.get("label", "")
        value   = c.get("value", "")
        icon    = c.get("icon", "")
        color   = c.get("color", "emerald")
        delta   = c.get("delta", "")
        gradient = GRADIENTS.get(color, GRADIENTS["emerald"])
        # Optional: light/dark variant for the gradient (opacity in the corners)
        delta_html = ""
        if delta:
            delta_color = "#059669" if not delta.startswith("-") else "#dc2626"
            arrow = "▲" if not delta.startswith("-") else "▼"
            delta_html = (
                f"<div style='font-size:0.7rem; color:{delta_color}; font-weight:600; margin-top:0.25rem;'>"
                f"{arrow} {delta}</div>"
            )

        html_cards.append(
            f"""
            <div style='
                background: {gradient};
                color: white;
                border-radius: 14px;
                padding: 1rem 1.1rem;
                box-shadow: 0 4px 14px rgba(0,0,0,0.12);
                position: relative;
                overflow: hidden;
                min-height: 100px;
                transition: transform 0.25s ease, box-shadow 0.25s ease;
                animation: scaleIn 0.4s ease-out backwards;
            ' onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 12px 28px rgba(0,0,0,0.2)';"
               onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 14px rgba(0,0,0,0.12)';">
                <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
                    <div style='font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; opacity:0.95;'>{label}</div>
                    <div style='font-size:1.4rem; opacity:0.9;'>{icon}</div>
                </div>
                <div style='font-size:1.65rem; font-weight:800; margin-top:0.25rem; line-height:1.1;'>{value}</div>
                {delta_html}
                <!-- decorative blob in the corner -->
                <div style='
                    position:absolute; bottom:-20px; right:-20px;
                    width:80px; height:80px; border-radius:50%;
                    background: rgba(255,255,255,0.12);
                '></div>
            </div>
            """
        )

    _html(
        f"""
        <div style='
            display:grid;
            grid-template-columns: repeat({grid_cols}, minmax(0, 1fr));
            gap: 12px;
            margin: 0.5rem 0 1.25rem 0;
        '>
            {"".join(html_cards)}
        </div>
        """
    )


# ============================================================
# ANIMATED PROGRESS BAR
# ============================================================
def animated_progress(label: str, value: float, max_value: float = 100.0, color: str = "emerald") -> None:
    """Render a custom animated progress bar with a label.

    ``value`` / ``max_value`` are unit-less (e.g. 7 / 10 for 70% complete).
    """
    pct = max(0.0, min(100.0, (value / max(1, max_value)) * 100.0))
    gradient = GRADIENTS.get(color, GRADIENTS["emerald"])
    _html(
        f"""
        <div style='margin: 0.5rem 0;'>
            <div style='display:flex; justify-content:space-between; font-size:0.78rem; font-weight:600; color:#475569; margin-bottom:4px;'>
                <span>{label}</span>
                <span style='color:#047857;'>{pct:.0f}%</span>
            </div>
            <div style='background:#e2e8f0; border-radius:8px; height:10px; overflow:hidden;'>
                <div style='
                    width: {pct}%;
                    height: 100%;
                    background: {gradient};
                    background-size: 200% 100%;
                    border-radius: 8px;
                    animation: gradientShift 3s ease infinite;
                    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
                '></div>
            </div>
        </div>
        """
    )
