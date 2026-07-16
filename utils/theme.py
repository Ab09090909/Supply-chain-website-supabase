"""
Theme system — modern, professional, attractive.

Light mode: clean white + emerald accents + subtle shadows
Dark mode: deep slate + glassmorphism + emerald highlights
"""
from __future__ import annotations

import streamlit as st


def init_theme():
    if "app_theme" not in st.session_state:
        st.session_state["app_theme"] = "light"


def render_theme_toggle():
    init_theme()
    current = st.session_state.get("app_theme", "light")
    is_dark = st.toggle(
        "🌙 Dark Mode" if current != "dark" else "☀️ Light Mode",
        value=(current == "dark"),
        key="theme_toggle_widget",
        help="Switch between light and dark mode.",
    )
    new_theme = "dark" if is_dark else "light"
    if new_theme != current:
        st.session_state["app_theme"] = new_theme
        st.rerun()


def _inject_css(css: str):
    try:
        st.html(css)
    except AttributeError:
        st.markdown(f'<div style="display:none">{css}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# GLOBAL CSS — applies to both themes (transitions, spacing, animations)
# ---------------------------------------------------------------------------
_GLOBAL_CSS = """<style>
/* ===== Animations ===== */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-12px); }
    to { opacity: 1; transform: translateX(0); }
}

/* Smooth transitions for all interactive elements */
.stButton > button,
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div,
.stNumberInput > div > div > input,
[data-testid="stMetric"] {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* Modern buttons */
.stButton > button {
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 0.45rem 1rem !important;
    border: 1px solid transparent !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    border: none !important;
    color: white !important;
}

/* Headings — professional hierarchy */
.stMarkdown h1 { font-size: 1.5rem !important; font-weight: 700 !important; letter-spacing: -0.01em !important; }
.stMarkdown h2 { font-size: 1.25rem !important; font-weight: 700 !important; }
.stMarkdown h3 { font-size: 1.1rem !important; font-weight: 600 !important; }
.stMarkdown h4 { font-size: 1rem !important; font-weight: 600 !important; }
.stMarkdown h5 { font-size: 0.9rem !important; font-weight: 600 !important; }
.stMarkdown h6 { font-size: 0.85rem !important; font-weight: 600 !important; }

/* Compact metrics */
[data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; font-weight: 500 !important; }

/* Captions */
.stCaption { font-size: 0.75rem !important; }

/* Dataframes */
.stDataFrame { font-size: 0.8rem !important; }
.stDataFrame th { font-weight: 600 !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* Alerts */
.stAlert { border-radius: 10px !important; animation: fadeInUp 0.25s ease-out !important; }

/* Sidebar animation */
[data-testid="stSidebar"] { animation: slideInLeft 0.3s ease-out !important; }

/* Tab transitions */
.stTabs [data-baseweb="tab-panel"] { animation: fadeIn 0.2s ease-out !important; }

/* Image styling */
.stImage img { transition: transform 0.3s ease !important; border-radius: 8px !important; }
</style>"""


# ---------------------------------------------------------------------------
# LIGHT MODE — clean white + emerald
# ---------------------------------------------------------------------------
_LIGHT_CSS = """<style>
/* App background */
.stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
    color: #0f172a !important;
}
.main .block-container { color: #0f172a !important; }

/* Sidebar */
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
    box-shadow: 2px 0 8px rgba(0,0,0,0.03) !important;
    color: #0f172a !important;
}

/* Headers */
h1, h2, h3, h4, h5, h6 { color: #0f172a !important; }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span { color: #1e293b !important; }

/* Form labels */
.stTextArea > div > label,
.stTextInput > div > label,
.stNumberInput > div > label,
.stSelectbox > div > label,
.stCheckbox > label,
.stRadio > label,
.stFileUploader > div > label { color: #334155 !important; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.12) !important;
}

/* Code */
.stMarkdown code, code {
    background: #f1f5f9 !important;
    color: #047857 !important;
    padding: 0.15em 0.4em !important;
    border-radius: 4px !important;
    font-size: 0.9em !important;
}
.stCode, pre {
    background: #f8fafc !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
}
.stCode code, pre code { color: #0f172a !important; background: transparent !important; }

/* Dataframes */
.stDataFrame, .stDataFrame table, .stDataFrame th, .stDataFrame td {
    background: #ffffff !important;
    color: #0f172a !important;
}
.stDataFrame th { background: #f1f5f9 !important; color: #047857 !important; }

/* Tables */
.stMarkdown table, .stMarkdown th, .stMarkdown td {
    color: #0f172a !important;
    border-color: #e2e8f0 !important;
}
.stMarkdown th { background: #f1f5f9 !important; color: #047857 !important; }
.stMarkdown td { background: #ffffff !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: #ffffff !important;
    padding: 1rem !important;
    border-radius: 12px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
[data-testid="stMetricLabel"] { color: #64748b !important; }
[data-testid="stMetricValue"] { color: #047857 !important; }

/* Expander */
.stExpander {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    color: #0f172a !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 4px !important; }
.stTabs [data-baseweb="tab"] {
    background: #f8fafc !important;
    color: #64748b !important;
    border-radius: 8px 8px 0 0 !important;
    border-bottom: 3px solid transparent !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #ecfdf5 !important;
    color: #047857 !important;
    border-bottom-color: #10b981 !important;
}

/* Toast */
[data-testid="stToast"] {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
}

/* Links */
a { color: #059669 !important; }
a:hover { color: #047857 !important; text-decoration: underline !important; }

/* Scrollbar thumb */
::-webkit-scrollbar-thumb { background: #cbd5e1 !important; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8 !important; }

/* Spinner */
.stSpinner > div { border-color: #10b981 transparent transparent transparent !important; }

/* Auth card */
.auth-card {
    background: #ffffff !important;
    color: #0f172a !important;
    box-shadow: 0 12px 40px rgba(15, 23, 42, 0.1) !important;
    border: 1px solid #e2e8f0 !important;
}
.auth-title { color: #0f172a !important; }
.auth-subtitle { color: #64748b !important; }
.role-card {
    background: #ffffff !important;
    border-color: #e2e8f0 !important;
    color: #0f172a !important;
}
.role-card.selected {
    background: #ecfdf5 !important;
    border-color: #10b981 !important;
}
</style>"""


# ---------------------------------------------------------------------------
# DARK MODE — deep slate + emerald accents
# ---------------------------------------------------------------------------
_DARK_CSS = """<style>
/* App background — deep navy gradient */
.stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0f172a 100%) !important;
    color: #e2e8f0 !important;
}
.main .block-container { color: #e2e8f0 !important; }

/* Sidebar — slightly darker than the main app */
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
    background: linear-gradient(180deg, #0b1220 0%, #1e293b 100%) !important;
    border-right: 1px solid #334155 !important;
    color: #e2e8f0 !important;
}

/* Radio buttons (Navigation) — make highly visible */
.stRadio > label,
.stRadio > div[role="radiogroup"] label,
[data-testid="stRadio"] label,
[data-testid="stRadio"] > label {
    color: #f8fafc !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
}
[data-testid="stRadio"] > div[role="radiogroup"] > label {
    color: #e2e8f0 !important;
    font-weight: 600 !important;
}
/* Make the radio circle larger and the text bolder */
[data-testid="stRadio"] p {
    color: #f8fafc !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
}

/* Checkbox labels */
.stCheckbox > label,
[data-testid="stCheckbox"] label,
[data-testid="stCheckbox"] p {
    color: #f8fafc !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
}

/* All form labels — bright and bold */
.stTextArea > div > label,
.stTextInput > div > label,
.stNumberInput > div > label,
.stSelectbox > div > label,
.stFileUploader > div > label,
.stSlider > div > label,
.stMultiSelect > div > label,
.stDateInput > div > label,
.stTimeInput > div > label,
.stRadio > label {
    color: #f1f5f9 !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    text-transform: none !important;
}

/* Captions — bright but smaller */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #cbd5e1 !important;
    font-weight: 500 !important;
}

/* Markdown text — high contrast */
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {
    color: #e2e8f0 !important;
    font-weight: 500 !important;
}
/* Strong/bold inside markdown */
.stMarkdown strong, .stMarkdown b {
    color: #f8fafc !important;
    font-weight: 700 !important;
}

/* Text input / number input text — bright */
.stTextInput input, .stNumberInput input {
    color: #f8fafc !important;
    font-weight: 500 !important;
}

/* Placeholder text in inputs */
.stTextInput input::placeholder,
.stTextArea textarea::placeholder,
.stNumberInput input::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}

/* Selectbox / multiselect selected value */
.stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div,
[data-baseweb="select"] > div {
    color: #f1f5f9 !important;
    font-weight: 500 !important;
}

/* Sidebar nav headers */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6 {
    color: #f8fafc !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: #e2e8f0 !important;
}

/* Captions */
.stCaption { color: #94a3b8 !important; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: rgba(15, 23, 42, 0.7) !important;
    color: #f1f5f9 !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2) !important;
}

/* Code */
.stMarkdown code, code {
    background: rgba(51, 65, 85, 0.6) !important;
    color: #6ee7b7 !important;
    padding: 0.15em 0.4em !important;
    border-radius: 4px !important;
    font-size: 0.9em !important;
}
.stCode, pre {
    background: #0b1220 !important;
    color: #e2e8f0 !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
.stCode code, pre code { color: #e2e8f0 !important; background: transparent !important; }

/* Dataframes */
.stDataFrame, .stDataFrame table, .stDataFrame th, .stDataFrame td {
    background: rgba(15, 23, 42, 0.6) !important;
    color: #e2e8f0 !important;
}
.stDataFrame th { background: #1e293b !important; color: #34d399 !important; }

/* Tables */
.stMarkdown table, .stMarkdown th, .stMarkdown td {
    color: #e2e8f0 !important;
    border-color: #334155 !important;
}
.stMarkdown th { background: #1e293b !important; color: #34d399 !important; }
.stMarkdown td { background: rgba(15, 23, 42, 0.5) !important; }

/* Metrics — emerald accent */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.6) 100%) !important;
    padding: 1rem !important;
    border-radius: 12px !important;
    border: 1px solid #334155 !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
}
[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
[data-testid="stMetricValue"] { color: #34d399 !important; }

/* Expander */
.stExpander {
    background: rgba(15, 23, 42, 0.5) !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
}
.stExpander details summary { color: #e2e8f0 !important; }
.stExpander p, .stExpander li, .stExpander span { color: #cbd5e1 !important; }

/* Tabs — emerald accent on active */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 4px !important; }
.stTabs [data-baseweb="tab"] {
    background: rgba(30, 41, 59, 0.5) !important;
    color: #cbd5e1 !important;
    border-radius: 8px 8px 0 0 !important;
    border-bottom: 3px solid transparent !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: rgba(16, 185, 129, 0.15) !important;
    color: #34d399 !important;
    border-bottom-color: #10b981 !important;
}

/* Toast */
[data-testid="stToast"] {
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border: 1px solid #334155 !important;
}

/* Links */
a { color: #34d399 !important; }
a:hover { color: #6ee7b7 !important; }

/* Scrollbar thumb */
::-webkit-scrollbar-thumb { background: #475569 !important; }
::-webkit-scrollbar-thumb:hover { background: #64748b !important; }

/* Spinner */
.stSpinner > div { border-color: #34d399 transparent transparent transparent !important; }

/* Auth card */
.auth-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    color: #e2e8f0 !important;
    box-shadow: 0 12px 40px rgba(0,0,0,0.5) !important;
    border: 1px solid #334155 !important;
}
.auth-title { color: #f8fafc !important; }
.auth-subtitle { color: #94a3b8 !important; }
.role-card {
    background: rgba(15, 23, 42, 0.8) !important;
    border-color: #334155 !important;
    color: #e2e8f0 !important;
}
.role-card.selected {
    background: rgba(16, 185, 129, 0.15) !important;
    border-color: #10b981 !important;
}
</style>"""


def apply_theme_css():
    init_theme()
    theme = st.session_state.get("app_theme", "light")

    _inject_css(_GLOBAL_CSS)

    if theme == "dark":
        _inject_css(_DARK_CSS)
    else:
        _inject_css(_LIGHT_CSS)
