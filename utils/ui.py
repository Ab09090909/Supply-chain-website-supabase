"""
Shared UI helpers — modern horizontal grid card design.
"""
from __future__ import annotations

import streamlit as st
from .constants import ROLE_COLORS, ROLE_LABELS


# ── Theme tokens ──────────────────────────────────────────────────────────────
def _t() -> dict:
    dark = st.session_state.get("dark_mode", False)
    if dark:
        return {
            "bg":       "#1E293B",
            "border":   "#2D3F55",
            "text_pri": "#F1F5F9",
            "text_sec": "#94A3B8",
            "head":     "#F1F5F9",
            "sub":      "#64748B",
            "info_bg":  "#0F172A",
            "info_bdr": "#2D3F55",
        }
    return {
        "bg":       "#ffffff",
        "border":   "#e5e7eb",
        "text_pri": "#0f172a",
        "text_sec": "#6b7280",
        "head":     "#0f172a",
        "sub":      "#64748b",
        "info_bg":  "#f8fafc",
        "info_bdr": "#e5e7eb",
    }


# Gradient map (accent only — no bg colors)
GRADIENTS = {
    "emerald": "linear-gradient(135deg,#34d399 0%,#10b981 100%)",
    "blue":    "linear-gradient(135deg,#3b82f6 0%,#2563eb 100%)",
    "purple":  "linear-gradient(135deg,#a78bfa 0%,#8b5cf6 100%)",
    "amber":   "linear-gradient(135deg,#fbbf24 0%,#f59e0b 100%)",
    "red":     "linear-gradient(135deg,#f87171 0%,#ef4444 100%)",
    "teal":    "linear-gradient(135deg,#2dd4bf 0%,#14b8a6 100%)",
    "pink":    "linear-gradient(135deg,#f472b6 0%,#ec4899 100%)",
    "indigo":  "linear-gradient(135deg,#818cf8 0%,#6366f1 100%)",
}
ICON_GRADIENTS = {
    "📦":"emerald","⚠️":"amber","💰":"emerald","⏳":"amber",
    "👥":"blue",   "🚨":"red",  "📜":"purple", "🛒":"teal",
    "📈":"indigo", "🎯":"pink", "🤝":"blue",   "📨":"purple",
    "✅":"emerald","❌":"red",  "🔄":"blue",   "🚚":"purple",
}


def _card_css():
    """Inject CSS that styles native st.metric as a card + fixes page bg."""
    t = _t()
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid] {{
    font-family: 'Inter', sans-serif !important;
}}
.block-container {{ padding-top: 1.2rem !important; }}

[data-testid="stMetric"] {{
    background: {t["bg"]};
    border: 1px solid {t["border"]};
    border-radius: 12px;
    padding: 16px 18px !important;
    min-height: 100px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
}}
[data-testid="stMetricValue"] {{
    color: {t["text_pri"]} !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
}}
[data-testid="stMetricLabel"] {{
    color: {t["text_sec"]} !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
}}
[data-testid="stMetricDelta"] {{ display: none; }}

[data-testid="stDataFrame"] {{
    border-radius: 12px !important;
    border: 1px solid {t["border"]} !important;
    overflow: hidden;
}}
[data-testid="stDataFrame"] th {{
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    opacity: .6;
}}
[data-testid="stDataFrame"] td {{
    font-size: 13px !important;
    font-weight: 500 !important;
}}
hr {{ opacity: .12 !important; margin: 6px 0 !important; }}
</style>
""", unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    _card_css()          # inject once at the top of every page
    t = _t()
    sub_html = (f"<p style='color:{t['sub']};font-size:.85rem;margin:.2rem 0 0;'>"
                f"{subtitle}</p>") if subtitle else ""
    st.markdown(
        f"<div style='margin-bottom:.75rem;padding:.5rem 0;'>"
        f"<h1 style='font-size:1.4rem;font-weight:700;color:{t['head']};"
        f"margin:0;line-height:1.2;'>{title}</h1>{sub_html}</div>",
        unsafe_allow_html=True,
    )


def role_badge(role: str) -> str:
    color = ROLE_COLORS.get(role, "#64748b")
    label = ROLE_LABELS.get(role, role.capitalize())
    return (
        f"<span style='display:inline-block;padding:.2rem .6rem;"
        f"border-radius:9999px;font-size:.7rem;font-weight:600;"
        f"background:{color}15;color:{color};border:1px solid {color}30;'>{label}</span>"
    )


def metric_card(label: str, value: str, delta: str = "",
                color: str = "#10b981", icon: str = "") -> None:
    """
    Render a metric card using native st.metric (always renders correctly)
    with a coloured accent bar above it via a safe inline-style div.
    The icon is prepended to the label so it shows in the metric widget.
    """
    gradient = GRADIENTS.get(ICON_GRADIENTS.get(icon, "emerald"), GRADIENTS["emerald"])
    # Thin accent bar — pure inline style, no class, Streamlit-safe
    st.markdown(
        f'<div style="height:3px;background:{gradient};'
        f'border-radius:6px 6px 0 0;margin-bottom:1px;"></div>',
        unsafe_allow_html=True,
    )
    st.metric(
        label=f"{icon}  {label}" if icon else label,
        value=value,
        delta=delta if delta else None,
    )


def stat_card(label: str, value: str, color: str = "#10b981", icon: str = "") -> None:
    metric_card(label, value, color=color, icon=icon)


def sidebar_user_card(user: dict) -> None:
    t = _t()
    name       = user.get("full_name", "User")
    email      = user.get("email", "")
    role       = user.get("role", "")
    avatar_url = user.get("avatar_url")

    if avatar_url:
        av = (f"<img src='{avatar_url}' style='width:36px;height:36px;"
              f"border-radius:50%;object-fit:cover;"
              f"border:2px solid {ROLE_COLORS.get(role,\"#64748b\")};'/>")
    else:
        av = (f"<div style='width:36px;height:36px;border-radius:50%;"
              f"background:{ROLE_COLORS.get(role,'#64748b')};color:white;"
              f"display:flex;align-items:center;justify-content:center;"
              f"font-weight:700;font-size:.9rem;'>"
              f"{name[0].upper() if name else 'U'}</div>")

    st.markdown(
        f"<div style='padding:.7rem;border-radius:8px;background:{t['info_bg']};"
        f"margin-bottom:.6rem;border:1px solid {t['info_bdr']};'>"
        f"<div style='display:flex;align-items:center;gap:.6rem;'>"
        f"{av}"
        f"<div style='min-width:0;flex:1;'>"
        f"<div style='font-weight:600;color:{t['text_pri']};font-size:.85rem;"
        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{name}</div>"
        f"<div style='font-size:.7rem;color:{t['text_sec']};"
        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{email}</div>"
        f"</div></div>"
        f"<div style='margin-top:.4rem;'>{role_badge(role)}</div></div>",
        unsafe_allow_html=True,
    )


def compact_info_card(icon: str, title: str, value: str,
                      description: str = "", color: str = "#10b981") -> None:
    t = _t()
    gradient = GRADIENTS.get(ICON_GRADIENTS.get(icon, "emerald"), GRADIENTS["emerald"])
    desc_html = (f"<div style='font-size:.7rem;color:{t['text_sec']};margin-top:.1rem;'>"
                 f"{description}</div>") if description else ""
    st.markdown(
        f"<div style='padding:.875rem;border-radius:12px;background:{t['bg']};"
        f"border:1px solid {t['border']};box-shadow:0 1px 3px rgba(0,0,0,.06);"
        f"display:flex;align-items:center;gap:.875rem;margin-bottom:.5rem;'>"
        f"<div style='width:40px;height:40px;border-radius:50%;background:{gradient};"
        f"display:flex;align-items:center;justify-content:center;font-size:1.2rem;"
        f"flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,.1);'>{icon}</div>"
        f"<div style='flex:1;min-width:0;'>"
        f"<div style='font-size:.7rem;color:{t['text_sec']};font-weight:500;"
        f"text-transform:uppercase;letter-spacing:.03em;'>{title}</div>"
        f"<div style='font-size:1.2rem;font-weight:700;color:{t['text_pri']};"
        f"line-height:1.2;'>{value}</div>{desc_html}</div></div>",
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    status_map = {
        "pending":    ("⏳","#f59e0b"), "verified":   ("✅","#10b981"),
        "rejected":   ("❌","#ef4444"), "active":     ("🟢","#10b981"),
        "inactive":   ("⚫","#6b7280"), "delivered":  ("📦","#059669"),
        "shipped":    ("🚚","#8b5cf6"), "confirmed":  ("✅","#10b981"),
        "processing": ("🔄","#3b82f6"), "cancelled":  ("❌","#ef4444"),
    }
    icon, c = status_map.get(status.lower(), ("❓","#6b7280"))
    return (f"<span style='display:inline-block;padding:.2rem .6rem;"
            f"border-radius:6px;font-size:.7rem;font-weight:600;"
            f"background:{c}15;color:{c};border:1px solid {c}30;'>"
            f"{icon} {status.title()}</span>")


def show_success_toast(message: str) -> None:
    st.toast(message, icon="✅")

def show_error_message(message: str) -> None:
    st.error(message)

def show_info_message(message: str) -> None:
    st.info(message)
