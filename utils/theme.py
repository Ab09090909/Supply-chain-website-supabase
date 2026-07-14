"""
Theme toggle — dark/light mode + global animations for the whole app.

v6 fix: Improved color combinations for both dark and light modes.
- Dark mode: uses a proper layered palette with consistent contrast
- Light mode: cleaner whites with subtle depth
- Removed overly broad selectors that were fighting Streamlit's own styles
- Better text contrast throughout (WCAG AA compliant)
"""
from __future__ import annotations

import streamlit as st


def init_theme():
    """Initialize theme state. Call once at app startup."""
    if "app_theme" not in st.session_state:
        st.session_state["app_theme"] = "light"


def render_theme_toggle():
    """Render a light/dark toggle in the sidebar using st.toggle."""
    init_theme()
    current = st.session_state.get("app_theme", "light")

    is_dark = st.toggle(
        "🌙 Dark Mode" if not (current == "dark") else "☀️ Light Mode",
        value=(current == "dark"),
        key="theme_toggle_widget",
        help="Switch between light and dark mode.",
    )

    new_theme = "dark" if is_dark else "light"
    if new_theme != current:
        st.session_state["app_theme"] = new_theme
        st.rerun()


def _inject_css(css: str):
    """Inject CSS into the page using the safest method available."""
    try:
        st.html(css)
    except AttributeError:
        st.markdown(
            f'<div style="display:none">{css}</div>',
            unsafe_allow_html=True,
        )


def apply_theme_css():
    """Inject CSS for the current theme + global animations."""
    init_theme()
    theme = st.session_state.get("app_theme", "light")

    # ── Palette reference ────────────────────────────────────────────────────
    # DARK:
    #   bg-base      #0d1117   deepest background (app shell)
    #   bg-surface   #161b22   cards, sidebar
    #   bg-elevated  #21262d   inputs, code blocks, hover states
    #   border       #30363d   subtle dividers
    #   border-focus #10b981   emerald — brand accent
    #   text-primary #e6edf3   main readable text
    #   text-muted   #8b949e   secondary / captions
    #   text-faint   #484f58   disabled / placeholder
    #   accent-green #34d399   metric values, links, active tabs
    #   accent-dim   #065f46   muted accent backgrounds
    #
    # LIGHT:
    #   bg-base      #f6f8fa   app shell
    #   bg-surface   #ffffff   cards, sidebar
    #   bg-elevated  #f1f5f9   inputs, code blocks
    #   border       #d0d7de   dividers
    #   border-focus #10b981   emerald accent
    #   text-primary #1f2328   main text
    #   text-muted   #57606a   secondary
    #   text-faint   #8c959f   placeholder
    #   accent-green #047857   metric values, links (darker for contrast on white)
    #   accent-dim   #ecfdf5   muted accent backgrounds
    # ─────────────────────────────────────────────────────────────────────────

    animations_css = """<style>
/* ===== GLOBAL ANIMATIONS ===== */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-16px); }
    to   { opacity: 1; transform: translateX(0); }
}

/* Page entry */
.stApp > div > div > div {
    animation: fadeInUp 0.35s ease-out;
}

/* Sidebar entry */
[data-testid="stSidebar"] {
    animation: slideInLeft 0.35s ease-out;
}

/* Tab panels */
.stTabs [data-baseweb="tab-panel"] {
    animation: fadeIn 0.25s ease-out;
}

/* Smooth interactive elements */
.stButton > button,
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div,
.stNumberInput > div > div > input,
[data-testid="stMetric"] {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(16, 185, 129, 0.22) !important;
}

.stImage img {
    transition: transform 0.3s ease !important;
    border-radius: 8px !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { border-radius: 4px; }

a { transition: color 0.15s ease !important; }
a:hover { text-decoration: underline !important; }

.stAlert { border-radius: 10px !important; animation: fadeInUp 0.25s ease-out !important; }
</style>"""

    if theme == "dark":
        dark_css = """<style>
/* ===== DARK MODE — layered slate palette ===== */

/* ── App shell ── */
.stApp,
[data-testid="stAppViewContainer"] {
    background-color: #0d1117 !important;
    color: #e6edf3 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
    background-color: #161b22 !important;
    border-right: 1px solid #30363d !important;
}

/* Sidebar text */
[data-testid="stSidebar"] *,
[data-testid="stSidebarContent"] * {
    color: #e6edf3 !important;
}

/* ── Cards / containers — target only named containers, not everything ── */
[data-testid="stVerticalBlock"] > [data-testid="element-container"] > div[class*="card"],
.auth-card,
.role-card {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 12px !important;
    color: #e6edf3 !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}
[data-testid="stMetricLabel"]  { color: #8b949e !important; }
[data-testid="stMetricValue"]  { color: #34d399 !important; }
[data-testid="stMetricDelta"]  { color: #8b949e !important; }

/* ── Form inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
    background-color: #0d1117 !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    caret-color: #34d399 !important;
}
.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder,
.stNumberInput > div > div > input::placeholder {
    color: #484f58 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stNumberInput > div > div > input:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.18) !important;
    outline: none !important;
}

/* Selectbox */
.stSelectbox > div > div > div {
    background-color: #0d1117 !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
}

/* ── Form labels ── */
.stTextInput > div > label,
.stTextArea > div > label,
.stNumberInput > div > label,
.stSelectbox > div > label,
.stCheckbox > label,
.stRadio > label,
.stFileUploader > div > label {
    color: #8b949e !important;
    font-size: 0.85rem !important;
}

/* ── Markdown text ── */
.stMarkdown p,
.stMarkdown li,
.stMarkdown span,
.stMarkdown div {
    color: #c9d1d9 !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #e6edf3 !important;
}

/* ── Inline code ── */
.stMarkdown code,
code:not(pre code) {
    background-color: #21262d !important;
    color: #79c0ff !important;   /* blue — clearly distinct from green accents */
    padding: 0.15em 0.4em !important;
    border-radius: 4px !important;
    font-size: 0.88em !important;
    border: 1px solid #30363d !important;
}

/* ── Code blocks ── */
pre,
.stCode,
.stCodeBlock {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
}
pre code,
.stCode code {
    color: #e6edf3 !important;
    background: transparent !important;
}

/* ── Data tables ── */
.stDataFrame,
.stDataFrame table {
    background-color: #161b22 !important;
}
.stDataFrame th {
    background-color: #21262d !important;
    color: #34d399 !important;
    border-bottom: 1px solid #30363d !important;
}
.stDataFrame td {
    color: #c9d1d9 !important;
    border-bottom: 1px solid #21262d !important;
}

/* ── Markdown tables ── */
.stMarkdown table { border-collapse: collapse !important; width: 100% !important; }
.stMarkdown th {
    background-color: #21262d !important;
    color: #34d399 !important;
    padding: 0.5rem 0.75rem !important;
    border: 1px solid #30363d !important;
}
.stMarkdown td {
    color: #c9d1d9 !important;
    padding: 0.5rem 0.75rem !important;
    border: 1px solid #21262d !important;
}
.stMarkdown tr:nth-child(even) td {
    background-color: rgba(33, 38, 45, 0.5) !important;
}

/* ── Expanders ── */
.stExpander {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 12px !important;
}
.stExpander summary,
.stExpander details,
.stExpander p,
.stExpander li,
.stExpander span {
    color: #c9d1d9 !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 4px !important;
    border-bottom: 1px solid #30363d !important;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    color: #8b949e !important;
    border-radius: 8px 8px 0 0 !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.5rem 1rem !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #c9d1d9 !important;
    background-color: #21262d !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #34d399 !important;
    border-bottom-color: #10b981 !important;
    background-color: transparent !important;
}

/* ── Links ── */
a { color: #58a6ff !important; }         /* blue links — familiar & distinct */
a:hover { color: #79c0ff !important; }

/* ── Captions ── */
.stCaption,
[data-testid="stCaptionContainer"] {
    color: #8b949e !important;
}

/* ── Toast notifications ── */
[data-testid="stToast"] {
    background-color: #21262d !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 10px !important;
}

/* ── Spinner ── */
.stSpinner > div {
    border-color: #10b981 transparent transparent transparent !important;
}

/* ── Scrollbar (dark) ── */
::-webkit-scrollbar-thumb { background: #30363d !important; }
::-webkit-scrollbar-thumb:hover { background: #484f58 !important; }

/* ── Custom auth card classes ── */
.auth-card {
    background: linear-gradient(135deg, #161b22 0%, #0d1117 100%) !important;
    border: 1px solid #30363d !important;
    border-radius: 16px !important;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6) !important;
    color: #e6edf3 !important;
}
.auth-title   { color: #e6edf3 !important; }
.auth-subtitle { color: #8b949e !important; }

.role-card {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 12px !important;
    color: #c9d1d9 !important;
}
.role-card:hover {
    border-color: #10b981 !important;
    background-color: #0d2818 !important;
}
</style>"""
        _inject_css(animations_css + dark_css)

    else:
        light_css = """<style>
/* ===== LIGHT MODE ===== */

/* ── App shell ── */
.stApp {
    background-color: #f6f8fa !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
    background-color: #ffffff !important;
    border-right: 1px solid #d0d7de !important;
    box-shadow: 2px 0 6px rgba(0, 0, 0, 0.04) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background-color: #ffffff !important;
    border: 1px solid #d0d7de !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
}
[data-testid="stMetricLabel"] { color: #57606a !important; }
[data-testid="stMetricValue"] { color: #047857 !important; }

/* ── Form inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
    background-color: #ffffff !important;
    border: 1px solid #d0d7de !important;
    border-radius: 8px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stNumberInput > div > div > input:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.12) !important;
    outline: none !important;
}

/* Selectbox */
.stSelectbox > div > div > div {
    background-color: #ffffff !important;
    border: 1px solid #d0d7de !important;
    border-radius: 8px !important;
}

/* ── Data tables ── */
.stDataFrame th {
    background-color: #f6f8fa !important;
    color: #047857 !important;
    font-weight: 600 !important;
    border-bottom: 1px solid #d0d7de !important;
}
.stDataFrame td {
    color: #1f2328 !important;
    border-bottom: 1px solid #f1f5f9 !important;
}

/* ── Expanders ── */
.stExpander {
    background-color: #ffffff !important;
    border: 1px solid #d0d7de !important;
    border-radius: 12px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 4px !important;
    border-bottom: 1px solid #d0d7de !important;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    color: #57606a !important;
    border-radius: 8px 8px 0 0 !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.5rem 1rem !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #1f2328 !important;
    background-color: #f6f8fa !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #047857 !important;
    border-bottom-color: #10b981 !important;
    background-color: #ecfdf5 !important;
}

/* ── Links ── */
a { color: #0969da !important; }
a:hover { color: #0550ae !important; }

/* ── Scrollbar (light) ── */
::-webkit-scrollbar-thumb { background: #d0d7de !important; }
::-webkit-scrollbar-thumb:hover { background: #8c959f !important; }

/* ── Custom card classes ── */
.auth-card {
    background-color: #ffffff !important;
    border: 1px solid #d0d7de !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08) !important;
}
.auth-title    { color: #1f2328 !important; }
.auth-subtitle { color: #57606a !important; }

.role-card {
    background-color: #ffffff !important;
    border: 1px solid #d0d7de !important;
    border-radius: 12px !important;
    color: #1f2328 !important;
}
.role-card:hover {
    border-color: #10b981 !important;
    background-color: #ecfdf5 !important;
}
</style>"""
        _inject_css(animations_css + light_css)
