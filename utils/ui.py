"""
Modern UI Design System — professional, attractive, consistent.

Design tokens (v8 — commercial/enterprise grade):
  • Typography: Inter (system fallback), 8-step scale, tight line-heights
  • Spacing: 4/8/12/16/24/32/48/64px scale (4px base)
  • Radius: 6/10/14/20px (small / medium / large / hero)
  • Shadows: 5 levels (none, xs, sm, md, lg, xl)
  • Colors: emerald primary + 8 gradient families + semantic colors
  • Buttons: 4 variants (primary, secondary, ghost, link) × 2 shapes (rounded, pill)
  • Cards: 4 variants (default, outlined, elevated, gradient)
"""
from __future__ import annotations

from datetime import datetime
import streamlit as st
import textwrap

from .constants import ROLE_COLORS, ROLE_LABELS


# ===========================================================================
# HELPERS
# ===========================================================================
def _html(html: str) -> None:
    """Render raw HTML safely. Bypasses Markdown parser. See full docstring."""
    cleaned = "\n".join(line.lstrip() for line in html.splitlines())
    try:
        st.html(cleaned)
    except AttributeError:
        st.markdown(cleaned, unsafe_allow_html=True)


# ===========================================================================
# DESIGN TOKENS — single source of truth
# ===========================================================================
COLORS = {
    "primary":         "#10b981",
    "primary_dark":    "#059669",
    "primary_darker":  "#047857",
    "primary_light":   "#d1fae5",
    "primary_pale":    "#ecfdf5",
    "slate_900":       "#0f172a",
    "slate_800":       "#1e293b",
    "slate_700":       "#334155",
    "slate_600":       "#475569",
    "slate_500":       "#64748b",
    "slate_400":       "#94a3b8",
    "slate_300":       "#cbd5e1",
    "slate_200":       "#e2e8f0",
    "slate_100":       "#f1f5f9",
    "slate_50":        "#f8fafc",
    "white":           "#ffffff",
    "amber":           "#f59e0b",
    "amber_light":     "#fef3c7",
    "red":             "#ef4444",
    "red_light":       "#fee2e2",
    "blue":            "#3b82f6",
    "blue_light":      "#dbeafe",
    "purple":          "#8b5cf6",
    "purple_light":    "#ede9fe",
    "teal":            "#14b8a6",
}

GRADIENTS = {
    "emerald": "linear-gradient(135deg, #34d399 0%, #10b981 50%, #059669 100%)",
    "blue":    "linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #2563eb 100%)",
    "purple":  "linear-gradient(135deg, #a78bfa 0%, #8b5cf6 50%, #7c3aed 100%)",
    "amber":   "linear-gradient(135deg, #fcd34d 0%, #f59e0b 50%, #d97706 100%)",
    "red":     "linear-gradient(135deg, #f87171 0%, #ef4444 50%, #dc2626 100%)",
    "teal":    "linear-gradient(135deg, #5eead4 0%, #14b8a6 50%, #0d9488 100%)",
    "pink":    "linear-gradient(135deg, #f9a8d4 0%, #ec4899 50%, #db2777 100%)",
    "indigo":  "linear-gradient(135deg, #a5b4fc 0%, #6366f1 50%, #4f46e5 100%)",
    "slate":   "linear-gradient(135deg, #cbd5e1 0%, #64748b 50%, #334155 100%)",
    "sunset":  "linear-gradient(135deg, #fbbf24 0%, #f97316 50%, #ea580c 100%)",
    "ocean":   "linear-gradient(135deg, #67e8f9 0%, #06b6d4 50%, #0891b2 100%)",
    "forest":  "linear-gradient(135deg, #86efac 0%, #22c55e 50%, #15803d 100%)",
    "royal":   "linear-gradient(135deg, #c4b5fd 0%, #7c3aed 50%, #5b21b6 100%)",
    "rose":    "linear-gradient(135deg, #fda4af 0%, #f43f5e 50%, #e11d48 100%)",
}

ICON_GRADIENTS = {
    "📦": "emerald", "⚠️": "amber", "💰": "emerald", "⏳": "amber",
    "👥": "blue", "🚨": "red", "📜": "purple", "🛒": "teal",
    "📈": "indigo", "🎯": "pink", "🤝": "blue", "📨": "purple",
    "✅": "emerald", "❌": "red", "🔄": "blue", "🚚": "purple",
    "🔔": "amber", "💬": "teal", "🤖": "indigo", "🔐": "red",
    "📊": "blue", "⚙️": "slate", "🏆": "amber", "⭐": "amber",
    "💼": "emerald", "🌍": "blue", "🔍": "slate", "📞": "emerald",
    "✉️": "blue", "📍": "red", "🏠": "emerald", "📷": "pink",
    "📘": "blue", "🎨": "purple", "⚡": "amber", "🚀": "ocean",
    "💡": "amber", "🔗": "blue", "👤": "emerald", "🌟": "amber",
    "📈": "indigo", "📉": "red", "🎁": "pink", "🏷️": "amber",
    "⏰": "amber", "💯": "emerald", "🌱": "forest", "🔥": "red",
    "🎉": "amber", "👁️": "blue", "🛡️": "blue", "📋": "slate",
}

# 5-level shadow system
SHADOWS = {
    "none": "none",
    "xs":   "0 1px 2px rgba(15, 23, 42, 0.05)",
    "sm":   "0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04)",
    "md":   "0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.06)",
    "lg":   "0 10px 15px -3px rgba(15, 23, 42, 0.10), 0 4px 6px -4px rgba(15, 23, 42, 0.05)",
    "xl":   "0 20px 25px -5px rgba(15, 23, 42, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.06)",
    "2xl":  "0 25px 50px -12px rgba(15, 23, 42, 0.20)",
}


# ===========================================================================
# TYPOGRAPHY — Inter font + JetBrains Mono fallback
# ===========================================================================
FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif"
MONO_STACK = "'JetBrains Mono', 'Fira Code', 'SF Mono', Menlo, Consolas, monospace"


# ===========================================================================
# PAGE HEADER — gradient title with icon
# ===========================================================================
def page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Modern page header with gradient title, optional icon, and subtitle.

    Best practice pattern (used by Stripe, Linear, Vercel):
        [icon]  TITLE
                Small muted subtitle
    """
    icon_html = ""
    if icon:
        icon_html = (
            f"<div style='display:inline-flex;align-items:center;justify-content:center;"
            f"width:48px;height:48px;border-radius:14px;"
            f"background:linear-gradient(135deg,#10b981 0%,#34d399 50%,#6ee7b7 100%);"
            f"background-size:200% 200%;animation:gradientShift 6s ease infinite,bounceIn 0.5s ease-out;"
            f"font-size:1.5rem;box-shadow:0 6px 20px rgba(16,185,129,0.35);"
            f"margin-right:14px;vertical-align:middle;flex-shrink:0;'>{icon}</div>"
        )

    subtitle_html = (
        f"<p style='color:#64748b;font-size:0.92rem;margin:0.35rem 0 0 0;font-weight:500;line-height:1.5;letter-spacing:-0.005em;'>{subtitle}</p>"
        if subtitle else ""
    )

    _html(
        "<div style='margin:0 0 1.75rem 0;padding:1.25rem 1.5rem;"
        "background:linear-gradient(135deg,rgba(16,185,129,0.05) 0%,rgba(52,211,153,0.02) 100%);"
        "border-radius:16px;border:1px solid rgba(16,185,129,0.14);"
        "border-left:4px solid #10b981;"
        "position:relative;overflow:hidden;animation:fadeInDown 0.4s ease-out;"
        "box-shadow:0 1px 3px rgba(15,23,42,0.04);'>"
        "<div style='display:flex;align-items:center;'>"
        + icon_html +
        "<div style='flex:1;min-width:0;'>"
        "<h1 style='font-family:-apple-system,BlinkMacSystemFont,Inter,sans-serif;"
        "font-size:1.65rem;font-weight:800;"
        "background:linear-gradient(135deg,#047857 0%,#10b981 60%,#34d399 100%);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"
        "margin:0;line-height:1.2;letter-spacing:-0.025em;'>"
        + str(title) +
        "</h1>"
        + subtitle_html +
        "</div>"
        "<div class='pulse-dot' style='flex-shrink:0;margin-left:1rem;'></div>"
        "</div>"
        "</div>"
    )


# ===========================================================================
# ROLE BADGE
# ===========================================================================
def role_badge(role: str) -> str:
    """Return HTML for a colored role badge."""
    color = ROLE_COLORS.get(role, "#64748b")
    label = ROLE_LABELS.get(role, role.capitalize())
    return (
        f"<span style='display:inline-block; padding:0.25rem 0.7rem; "
        f"border-radius:9999px; font-size:0.72rem; font-weight:700; "
        f"background:{color}15; color:{color}; border:1px solid {color}40;"
        f"letter-spacing:0.02em;text-transform:uppercase;'>{label}</span>"
    )


# ===========================================================================
# METRIC CARD — modern KPI card with gradient accent bar
# ===========================================================================
def metric_card(label: str, value: str, delta: str = "", color: str = "#10b981", icon: str = "") -> None:
    """Modern metric card with gradient accent bar (uses native st.metric)."""
    gradient = GRADIENTS.get(ICON_GRADIENTS.get(icon, "emerald"), GRADIENTS["emerald"])
    st.markdown(
        f'<div style="height:3px;background:{gradient};'
        f'border-radius:8px 8px 0 0;margin-bottom:1px;"></div>',
        unsafe_allow_html=True,
    )
    st.metric(
        label=f"{icon}  {label}" if icon else label,
        value=value,
        delta=delta if delta else None,
    )


def stat_card(label: str, value: str, color: str = "#10b981", icon: str = "") -> None:
    """Alias for metric_card."""
    metric_card(label, value, color=color, icon=icon)


# ===========================================================================
# SIDEBAR USER CARD
# ===========================================================================
def sidebar_user_card(user: dict) -> None:
    """Compact user info card in the sidebar."""
    name = user.get("full_name", "User")
    email = user.get("email", "")
    role = user.get("role", "")
    avatar_url = user.get("avatar_url")
    color = ROLE_COLORS.get(role, "#64748b")

    if avatar_url:
        avatar_html = (
            f"<img src='{avatar_url}' "
            f"style='width:44px; height:44px; border-radius:50%; object-fit:cover; "
            f"border:2px solid {color};' />"
        )
    else:
        avatar_html = (
            f"<div style='width:44px; height:44px; border-radius:50%;"
            f"background:linear-gradient(135deg,{color} 0%,{color}dd 100%); color:white; display:flex; align-items:center; "
            f"justify-content:center; font-weight:700; font-size:1.05rem;"
            f"box-shadow:0 2px 8px {color}40;'>"
            f"{name[0].upper() if name else 'U'}</div>"
        )

    _html(
        f"""
        <div style='padding:0.875rem; border-radius:14px; background:{COLORS["slate_50"]};
                    margin-bottom:0.75rem; border:1px solid {COLORS["slate_200"]};
                    box-shadow:0 1px 3px rgba(0,0,0,0.04);'>
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
            <div style='margin-top:0.6rem;'>{role_badge(role)}</div>
        </div>
        """
    )


# ===========================================================================
# COMPACT INFO CARD — full-width horizontal card
# ===========================================================================
def compact_info_card(icon: str, title: str, value: str, description: str = "", color: str = "#10b981") -> None:
    """Full-width info card with gradient icon + title + value."""
    gradient_name = ICON_GRADIENTS.get(icon, "emerald")
    gradient = GRADIENTS.get(gradient_name, GRADIENTS["emerald"])
    _html(
        f"""
        <div style='padding:0.95rem 1.1rem; border-radius:14px; background:{COLORS["white"]};
                    border:1px solid {COLORS["slate_200"]};
                    box-shadow:0 1px 3px rgba(0,0,0,0.04);
                    display:flex; align-items:center; gap:0.95rem; margin-bottom:0.5rem;
                    transition:all 0.2s ease;'>
            <div style='width:48px; height:48px; border-radius:14px;
                        background:{gradient}; display:flex; align-items:center;
                        justify-content:center; font-size:1.4rem; flex-shrink:0;
                        box-shadow:0 4px 12px rgba(0,0,0,0.10);'>
                {icon}
            </div>
            <div style='flex:1; min-width:0;'>
                <div style='font-size:0.7rem; color:{COLORS["slate_500"]}; font-weight:700;
                            text-transform:uppercase; letter-spacing:0.06em;line-height:1.2;'>{title}</div>
                <div style='font-size:1.2rem; font-weight:700; color:{COLORS["slate_900"]}; line-height:1.2;margin-top:0.15rem;letter-spacing:-0.01em;'>{value}</div>
                {f"<div style='font-size:0.7rem; color:{COLORS['slate_400']}; margin-top:0.15rem;line-height:1.3;'>{description}</div>" if description else ""}
            </div>
        </div>
        """
    )


# ===========================================================================
# STATUS BADGE
# ===========================================================================
def status_badge(status: str) -> str:
    """Return HTML for a compact status badge with icon."""
    status_map = {
        "pending":    ("⏳", COLORS["amber"],   COLORS["amber_light"]),
        "verified":   ("✅", COLORS["primary"], COLORS["primary_pale"]),
        "rejected":   ("❌", COLORS["red"],     COLORS["red_light"]),
        "active":     ("🟢", COLORS["primary"], COLORS["primary_pale"]),
        "inactive":   ("⚫", COLORS["slate_500"],COLORS["slate_100"]),
        "delivered":  ("📦", COLORS["primary_dark"], COLORS["primary_pale"]),
        "shipped":    ("🚚", COLORS["purple"],  COLORS["purple_light"]),
        "confirmed":  ("✅", COLORS["primary"], COLORS["primary_pale"]),
        "processing": ("🔄", COLORS["blue"],    COLORS["blue_light"]),
        "cancelled":  ("❌", COLORS["red"],     COLORS["red_light"]),
    }
    icon, color, bg = status_map.get(status.lower(), ("❓", COLORS["slate_500"], COLORS["slate_100"]))
    return (
        f"<span style='display:inline-block; padding:0.25rem 0.65rem; "
        f"border-radius:8px; font-size:0.72rem; font-weight:700; "
        f"background:{bg}; color:{color}; border:1px solid {color}40;'>"
        f"{icon} {status.title()}</span>"
    )


# ===========================================================================
# TOAST / ERROR / INFO
# ===========================================================================
def show_success_toast(message: str) -> None:
    st.toast(message, icon="✅")


def show_error_message(message: str) -> None:
    st.error(message)


def show_info_message(message: str) -> None:
    st.info(message)


# ===========================================================================
# SECTION HEADER
# ===========================================================================
def section_header(label: str, icon: str = "", color: str = "emerald") -> None:
    """Animated section header — small uppercase label with optional icon."""
    gradient = GRADIENTS.get(color, GRADIENTS["emerald"])
    icon_html = (
        f"<span style='display:inline-flex;align-items:center;justify-content:center; width:26px; height:26px;"
        f"background:{gradient}; border-radius:7px; "
        f"font-size:0.85rem; margin-right:8px; box-shadow:0 2px 6px rgba(0,0,0,0.1);'>{icon}</span>"
        if icon else ""
    )
    _html(
        f"""
        <div style='
            display:flex; align-items:center; gap:4px;
            margin: 1.75rem 0 0.85rem 0;
            padding: 0.25rem 0;
            border-bottom: 2px solid;
            border-image: linear-gradient(90deg, {gradient} 0%, transparent 100%) 1;
            animation: fadeInLeft 0.4s ease-out;
        '>
            <span style='
                font-size: 0.74rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.14em;
                color: #047857;
                display:flex;align-items:center;
            '>{icon_html}{label}</span>
        </div>
        """
    )


# ===========================================================================
# KPI DASHBOARD GRID — 4 gradient cards in one row
# ===========================================================================
def kpi_dashboard(cards: list[dict]) -> None:
    """Render a row of colorful gradient KPI cards.

    Each card is a dict: ``{"label": str, "value": str, "icon": str, "color": str, "delta": str}``
    where ``color`` is one of the keys of ``GRADIENTS`` (emerald, blue, etc).
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

        delta_html = ""
        if delta:
            is_up = not str(delta).startswith("-")
            delta_color = "#dcfce7" if is_up else "#fecaca"
            arrow = "▲" if is_up else "▼"
            delta_html = (
                f"<div style='font-size:0.72rem; color:{delta_color}; font-weight:700; margin-top:0.4rem;"
                f"display:inline-block;background:rgba(255,255,255,0.2);padding:0.15rem 0.5rem;border-radius:6px;'>"
                f"{arrow} {delta}</div>"
            )

        html_cards.append(
            f"""
            <div style='
                background: {gradient};
                color: white;
                border-radius: 16px;
                padding: 1.1rem 1.2rem;
                box-shadow: 0 4px 14px rgba(0,0,0,0.12);
                position: relative;
                overflow: hidden;
                min-height: 110px;
                transition: transform 0.25s ease, box-shadow 0.25s ease;
                animation: scaleIn 0.4s ease-out backwards;
            ' onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 14px 32px rgba(0,0,0,0.22)';"
               onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 14px rgba(0,0,0,0.12)';">
                <div style='display:flex; justify-content:space-between; align-items:flex-start;gap:8px;'>
                    <div style='font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.07em; opacity:0.95;line-height:1.3;'>{label}</div>
                    <div style='font-size:1.5rem; opacity:0.9;flex-shrink:0;'>{icon}</div>
                </div>
                <div style='font-size:1.75rem; font-weight:800; margin-top:0.4rem; line-height:1.1;letter-spacing:-0.02em;'>{value}</div>
                {delta_html}
                <div style='
                    position:absolute; bottom:-22px; right:-22px;
                    width:90px; height:90px; border-radius:50%;
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
            gap: 14px;
            margin: 0.5rem 0 1.5rem 0;
        '>
            {"".join(html_cards)}
        </div>
        """
    )


# ===========================================================================
# ANIMATED PROGRESS BAR
# ===========================================================================
def animated_progress(label: str, value: float, max_value: float = 100.0, color: str = "emerald") -> None:
    """Render a custom animated progress bar with a label."""
    pct = max(0.0, min(100.0, (value / max(1, max_value)) * 100.0))
    gradient = GRADIENTS.get(color, GRADIENTS["emerald"])
    _html(
        f"""
        <div style='margin: 0.5rem 0;'>
            <div style='display:flex; justify-content:space-between; font-size:0.8rem; font-weight:600; color:#475569; margin-bottom:5px;'>
                <span>{label}</span>
                <span style='color:#047857;font-weight:700;'>{pct:.0f}%</span>
            </div>
            <div style='background:#e2e8f0; border-radius:10px; height:10px; overflow:hidden;'>
                <div style='
                    width: {pct}%;
                    height: 100%;
                    background: {gradient};
                    background-size: 200% 100%;
                    border-radius: 10px;
                    animation: gradientShift 3s ease infinite;
                    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
                    box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
                '></div>
            </div>
        </div>
        """
    )


# ===========================================================================
# BUTTON HELPERS — programmatic button renderers
# ===========================================================================
def render_button_html(
    label: str,
    icon: str = "",
    variant: str = "primary",
    size: str = "md",
    shape: str = "rounded",
    full_width: bool = False,
    color: str = "emerald",
) -> str:
    """Generate HTML for a styled button (for use in st.markdown).

    Use this when you need a custom-styled button that Streamlit's
    ``st.button`` can't produce (e.g. inside a card layout).

    Variants: primary | secondary | ghost | outline
    Sizes:    sm | md | lg
    Shapes:   rounded | pill
    """
    size_map = {
        "sm": ("0.4rem 0.85rem", "0.78rem", "8px",  "8px 14px"),
        "md": ("0.55rem 1.2rem",  "0.85rem", "10px", "10px 18px"),
        "lg": ("0.7rem 1.6rem",   "0.95rem", "12px", "12px 22px"),
    }
    pad, fs, rad, shadow_pad = size_map.get(size, size_map["md"])
    width = "100%" if full_width else "auto"
    radius = "9999px" if shape == "pill" else rad

    gradient = GRADIENTS.get(color, GRADIENTS["emerald"])
    if variant == "primary":
        bg = gradient
        color_text = "white"
        border = "transparent"
        box_shadow = f"0 4px {shadow_pad} rgba(16, 185, 129, 0.3)"
    elif variant == "secondary":
        bg = COLORS["slate_100"]
        color_text = COLORS["slate_900"]
        border = COLORS["slate_200"]
        box_shadow = "0 1px 2px rgba(0,0,0,0.04)"
    elif variant == "ghost":
        bg = "transparent"
        color_text = COLORS["slate_700"]
        border = "transparent"
        box_shadow = "none"
    elif variant == "outline":
        bg = "transparent"
        color_text = COLORS["primary_dark"]
        border = COLORS["primary"]
        box_shadow = "none"
    else:
        bg = gradient
        color_text = "white"
        border = "transparent"
        box_shadow = f"0 4px {shadow_pad} rgba(16, 185, 129, 0.3)"

    icon_html = f"<span style='margin-right:6px;'>{icon}</span>" if icon else ""

    return (
        f"<button style='"
        f"background:{bg};color:{color_text};border:1px solid {border};"
        f"border-radius:{radius};padding:{pad};font-size:{fs};font-weight:700;"
        f"width:{width};cursor:pointer;box-shadow:{box_shadow};"
        f"letter-spacing:0.01em;transition:all 0.2s ease;"
        f"font-family:{FONT_STACK};"
        f'">{icon_html}{label}</button>'
    )


# ===========================================================================
# MODERN CARD COMPONENTS
# ===========================================================================
def card(
    title: str = "",
    body: str = "",
    icon: str = "",
    color: str = "emerald",
    variant: str = "default",
    cta_text: str = "",
    cta_href: str = "#",
    *,
    actions_html: str = "",
    footer_html: str = "",
) -> str:
    """Render a modern card as HTML (caller puts it in st.html/markdown).

    Variants:
      default  — white bg, subtle border
      outlined — white bg, colored border
      elevated — white bg, bigger shadow
      gradient — gradient bg, white text

    Returns the HTML string. Wrap in ``_html(...)`` or use with
    ``st.markdown(..., unsafe_allow_html=True)``.
    """
    variant_styles = {
        "default":  ("#ffffff",  COLORS["slate_900"], COLORS["slate_200"],  "0 1px 3px rgba(0,0,0,0.05)"),
        "outlined": ("#ffffff",  COLORS["slate_900"], COLORS["primary"],    "0 1px 3px rgba(0,0,0,0.05)"),
        "elevated": ("#ffffff",  COLORS["slate_900"], COLORS["slate_200"], "0 12px 32px rgba(0,0,0,0.10)"),
        "gradient": (GRADIENTS.get(color, GRADIENTS["emerald"]), "white", "transparent",
                     "0 12px 32px rgba(16, 185, 129, 0.20)"),
    }
    bg, fg, border, shadow = variant_styles.get(variant, variant_styles["default"])

    icon_html = ""
    if icon:
        icon_bg = "rgba(255,255,255,0.18)" if variant == "gradient" else GRADIENTS.get(color, GRADIENTS["emerald"])
        icon_color = "white" if variant == "gradient" else "white"
        icon_html = (
            f"<div style='display:inline-flex;align-items:center;justify-content:center;"
            f"width:40px;height:40px;border-radius:12px;background:{icon_bg};"
            f"color:{icon_color};font-size:1.2rem;margin-right:10px;"
            f"box-shadow:0 4px 12px rgba(0,0,0,0.12);flex-shrink:0;'>"
            f"{icon}</div>"
        )

    title_html = f"""
        <div style='display:flex;align-items:center;margin-bottom:0.5rem;'>
            {icon_html}
            <div style='font-size:1.05rem;font-weight:700;color:{fg};letter-spacing:-0.015em;line-height:1.3;'>
                {title}
            </div>
        </div>
    """ if title else ""

    cta_html = ""
    if cta_text:
        cta_bg = "rgba(255,255,255,0.25)" if variant == "gradient" else GRADIENTS.get(color, GRADIENTS["emerald"])
        cta_fg = "white" if variant == "gradient" else "white"
        cta_html = f"""
            <a href='{cta_href}' style='display:inline-block;background:{cta_bg};color:{cta_fg};
                padding:0.45rem 1rem;border-radius:8px;font-weight:700;font-size:0.82rem;
                text-decoration:none;margin-top:0.5rem;letter-spacing:0.01em;'>
                {cta_text} →
            </a>
        """

    footer_block = f"<div style='margin-top:0.85rem;padding-top:0.85rem;border-top:1px solid rgba(0,0,0,0.08);'>{footer_html}</div>" if footer_html else ""

    return f"""
    <div style='
        background:{bg}; color:{fg};
        border:1px solid {border};
        border-radius:16px;
        padding:1.25rem 1.4rem;
        margin-bottom:0.85rem;
        box-shadow:{shadow};
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position:relative;overflow:hidden;
    ' onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 16px 40px rgba(0,0,0,0.14)';"
       onmouseout="this.style.transform='translateY(0)';">
        {title_html}
        {f"<div style='color:{fg};font-size:0.9rem;line-height:1.55;opacity:0.9;'>{body}</div>" if body else ""}
        {actions_html}
        {cta_html}
        {footer_block}
    </div>
    """


# ===========================================================================
# FEATURE GRID — used for landing pages / marketing
# ===========================================================================
def feature_grid(features: list[dict], columns: int = 3) -> None:
    """Render a grid of feature cards (icon + title + description).

    Each feature is a dict: ``{"icon": str, "title": str, "description": str, "color": str}``
    """
    if not features:
        return
    n = len(features)
    grid_cols = min(columns, 4)

    html_cards = []
    for f in features:
        icon = f.get("icon", "✨")
        title = f.get("title", "")
        desc = f.get("description", "")
        color = f.get("color", "emerald")
        gradient = GRADIENTS.get(color, GRADIENTS["emerald"])

        html_cards.append(f"""
            <div style='background:#ffffff;border:1px solid {COLORS["slate_200"]};
                border-radius:16px;padding:1.5rem 1.4rem;text-align:left;
                box-shadow:0 2px 8px rgba(0,0,0,0.04);
                transition:all 0.2s ease;'
                onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 12px 28px rgba(0,0,0,0.10)';this.style.borderColor='#10b981';"
                onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 2px 8px rgba(0,0,0,0.04)';this.style.borderColor='{COLORS["slate_200"]}';">
                <div style='display:inline-flex;align-items:center;justify-content:center;
                    width:48px;height:48px;border-radius:12px;background:{gradient};
                    color:white;font-size:1.4rem;margin-bottom:0.75rem;
                    box-shadow:0 4px 14px rgba(0,0,0,0.12);'>{icon}</div>
                <div style='font-size:1.05rem;font-weight:700;color:{COLORS["slate_900"]};
                    margin-bottom:0.4rem;letter-spacing:-0.015em;line-height:1.3;'>{title}</div>
                <div style='font-size:0.85rem;color:{COLORS["slate_600"]};line-height:1.5;'>{desc}</div>
            </div>
        """)

    _html(f"""
        <div style='display:grid;grid-template-columns:repeat({grid_cols},minmax(0,1fr));
            gap:18px;margin:1.5rem 0;'>
            {"".join(html_cards)}
        </div>
    """)


# ===========================================================================
# EMPTY STATE
# ===========================================================================
def empty_state(
    icon: str = "📭",
    title: str = "Nothing here yet",
    description: str = "",
    action_text: str = "",
    action_href: str = "#",
    color: str = "emerald",
) -> None:
    """Render a friendly empty state with icon, message, and optional CTA."""
    gradient = GRADIENTS.get(color, GRADIENTS["emerald"])
    cta_html = ""
    if action_text:
        cta_html = f"""
            <a href='{action_href}' style='display:inline-block;background:{gradient};color:white;
                padding:0.6rem 1.3rem;border-radius:10px;font-weight:700;font-size:0.85rem;
                text-decoration:none;margin-top:1rem;box-shadow:0 4px 14px rgba(0,0,0,0.12);
                letter-spacing:0.01em;'>{action_text} →</a>
        """
    _html(f"""
        <div style='text-align:center;padding:3rem 1.5rem;background:linear-gradient(135deg,#f8fafc 0%,#ecfdf5 100%);
            border-radius:16px;border:1px dashed {COLORS["primary_light"]};margin:1.5rem 0;'>
            <div style='display:inline-flex;align-items:center;justify-content:center;
                width:80px;height:80px;border-radius:50%;background:{gradient};
                color:white;font-size:2.2rem;margin-bottom:1rem;
                box-shadow:0 8px 24px rgba(0,0,0,0.15);animation:float 3s ease-in-out infinite;'>{icon}</div>
            <div style='font-size:1.15rem;font-weight:700;color:{COLORS["slate_900"]};letter-spacing:-0.015em;margin-bottom:0.4rem;'>{title}</div>
            {f"<div style='font-size:0.9rem;color:{COLORS['slate_600']};max-width:380px;margin:0 auto;line-height:1.5;'>{description}</div>" if description else ""}
            {cta_html}
        </div>
    """)


# ===========================================================================
# LOADING SKELETON
# ===========================================================================
def loading_skeleton(height: int = 80, width: str = "100%") -> None:
    """Render a shimmering loading skeleton (placeholder while data loads)."""
    _html(f"""
        <div style='
            height:{height}px;width:{width};border-radius:10px;
            background: linear-gradient(90deg,
                {COLORS["slate_100"]} 0%,
                {COLORS["slate_200"]} 50%,
                {COLORS["slate_100"]} 100%);
            background-size: 800px 100%;
            animation: shimmer 1.5s linear infinite;
            margin: 0.5rem 0;
        '></div>
    """)


# ===========================================================================
# LOADING SPINNER (enhanced)
# ===========================================================================
def loading_spinner(message: str = "Loading...") -> None:
    """Render a beautiful loading spinner with the given message."""
    _html(f"""
        <div style='text-align:center;padding:2rem 1rem;'>
            <div style='display:inline-block;width:40px;height:40px;border-radius:50%;
                border:3px solid {COLORS["primary_light"]};
                border-top-color:{COLORS["primary"]};
                animation:spin 0.8s linear infinite;margin-bottom:0.75rem;'></div>
            <div style='font-size:0.9rem;color:{COLORS["slate_600"]};font-weight:500;'>{message}</div>
        </div>
    """)


# ===========================================================================
# BADGE / TAG (small inline label)
# ===========================================================================
def tag(label: str, color: str = "emerald", filled: bool = False) -> str:
    """Render a small badge/tag for use in cards or tables."""
    if filled:
        bg = GRADIENTS.get(color, GRADIENTS["emerald"])
        fg = "white"
        border = "transparent"
    else:
        bg = COLORS.get(f"{color}_light", COLORS["primary_light"])
        fg = COLORS.get(color, COLORS["primary_dark"])
        border = COLORS.get(color, COLORS["primary"]) + "30"
    return (
        f"<span style='display:inline-block;padding:0.2rem 0.6rem;border-radius:6px;"
        f"font-size:0.7rem;font-weight:700;background:{bg};color:{fg};"
        f"border:1px solid {border};letter-spacing:0.02em;'>{label}</span>"
    )


# ===========================================================================
# NOTIFICATION BANNER
# ===========================================================================
def notification_banner(
    message: str,
    icon: str = "ℹ️",
    type: str = "info",  # info | success | warning | error
    dismissible: bool = False,
) -> None:
    """Render a modern, dismissible notification banner.

    type: info | success | warning | error
    """
    type_styles = {
        "info":    (GRADIENTS["blue"],   "rgba(59, 130, 246, 0.10)"),
        "success": (GRADIENTS["emerald"],"rgba(16, 185, 129, 0.10)"),
        "warning": (GRADIENTS["amber"],  "rgba(245, 158, 11, 0.10)"),
        "error":   (GRADIENTS["red"],    "rgba(239, 68, 68, 0.10)"),
    }
    gradient, bg = type_styles.get(type, type_styles["info"])

    _html(f"""
        <div style='
            background:{bg};
            border:1px solid {gradient.split(",")[1].strip()};
            border-left:4px solid {gradient.split(",")[1].strip()};
            border-radius:12px;
            padding:0.85rem 1.1rem;
            margin:0.5rem 0;
            display:flex;align-items:center;gap:0.75rem;
            animation:slideInLeft 0.3s ease-out;
        '>
            <div style='font-size:1.2rem;'>{icon}</div>
            <div style='flex:1;font-size:0.88rem;font-weight:500;line-height:1.4;'>{message}</div>
        </div>
    """)


# ===========================================================================
# HERO SECTION — for marketing/landing
# ===========================================================================
def hero_section(
    eyebrow: str = "",
    title: str = "",
    subtitle: str = "",
    primary_cta: tuple = None,    # (text, href)
    secondary_cta: tuple = None,  # (text, href)
    badge_icon: str = "✨",
) -> None:
    """Render a beautiful hero section (used on landing pages)."""
    eyebrow_html = ""
    if eyebrow:
        eyebrow_html = f"""
            <div style='display:inline-flex;align-items:center;gap:6px;
                background:linear-gradient(135deg,#ecfdf5 0%,#d1fae5 100%);
                color:#047857;padding:0.4rem 0.9rem;border-radius:9999px;
                font-size:0.75rem;font-weight:700;letter-spacing:0.04em;
                text-transform:uppercase;border:1px solid #a7f3d0;
                margin-bottom:1.25rem;'>
                <span>{badge_icon}</span><span>{eyebrow}</span>
            </div>
        """

    cta_html = ""
    if primary_cta or secondary_cta:
        cta_buttons = []
        if primary_cta:
            text, href = primary_cta
            cta_buttons.append(
                f"<a href='{href}' style='display:inline-flex;align-items:center;gap:6px;"
                f"background:linear-gradient(135deg,#10b981 0%,#059669 100%);color:white;"
                f"padding:0.75rem 1.6rem;border-radius:10px;font-weight:700;font-size:0.95rem;"
                f"text-decoration:none;box-shadow:0 6px 18px rgba(16,185,129,0.35);"
                f"letter-spacing:0.01em;transition:all 0.2s ease;'>{text} →</a>"
            )
        if secondary_cta:
            text, href = secondary_cta
            cta_buttons.append(
                f"<a href='{href}' style='display:inline-flex;align-items:center;gap:6px;"
                f"background:white;color:#0f172a;padding:0.75rem 1.6rem;border-radius:10px;"
                f"font-weight:700;font-size:0.95rem;text-decoration:none;"
                f"border:1px solid #e2e8f0;box-shadow:0 2px 8px rgba(0,0,0,0.06);"
                f"letter-spacing:0.01em;transition:all 0.2s ease;'>{text}</a>"
            )
        cta_html = f"<div style='display:flex;gap:12px;flex-wrap:wrap;justify-content:center;margin-top:1.75rem;'>{''.join(cta_buttons)}</div>"

    _html(f"""
        <div style='
            text-align:center;padding:4rem 1.5rem 3.5rem 1.5rem;
            background:
                radial-gradient(at 20% 30%,rgba(167, 243, 208, 0.18) 0px, transparent 50%),
                radial-gradient(at 80% 20%,rgba(196, 181, 253, 0.15) 0px, transparent 50%),
                radial-gradient(at 50% 90%,rgba(253, 230, 138, 0.12) 0px, transparent 50%);
            border-radius:24px;margin:1rem 0 2rem 0;
        '>
            {eyebrow_html}
            <h1 style='
                font-size:3rem;font-weight:900;
                background:linear-gradient(135deg,#047857 0%,#10b981 40%,#34d399 70%,#6ee7b7 100%);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                background-clip:text;margin:0 0 1rem 0;line-height:1.1;letter-spacing:-0.035em;
            '>{title}</h1>
            <p style='
                font-size:1.1rem;color:#475569;max-width:680px;margin:0 auto;line-height:1.6;
                font-weight:500;letter-spacing:-0.01em;
            '>{subtitle}</p>
            {cta_html}
        </div>
    """)


# ===========================================================================
# STAT COUNTER — large animated number with label
# ===========================================================================
def stat_counter(value: str, label: str, icon: str = "", color: str = "emerald") -> None:
    """Render a large stat counter (used in dashboards)."""
    gradient = GRADIENTS.get(color, GRADIENTS["emerald"])
    icon_html = f"<div style='font-size:2rem;margin-bottom:0.5rem;'>{icon}</div>" if icon else ""
    _html(f"""
        <div style='text-align:center;padding:1.25rem;background:white;
            border:1px solid {COLORS["slate_200"]};border-radius:14px;
            box-shadow:0 1px 3px rgba(0,0,0,0.04);'>
            {icon_html}
            <div style='font-size:2.25rem;font-weight:800;
                background:{gradient};
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                background-clip:text;letter-spacing:-0.025em;line-height:1;'>{value}</div>
            <div style='font-size:0.78rem;color:{COLORS["slate_500"]};font-weight:600;
                text-transform:uppercase;letter-spacing:0.07em;margin-top:0.5rem;'>{label}</div>
        </div>
    """)
