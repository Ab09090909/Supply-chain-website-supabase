"""
Theme system — modern, professional, CALM.

Light mode: clean white + emerald accents + subtle shadows
Dark mode:  deep slate + glassmorphism + emerald highlights

v9.0 — Animation cleanup
========================
After analysis, the previous version had 20 @keyframes which made
the app feel restless and unprofessional. This version keeps only the
6 animations that actually add value:

  KEEP:
  - fadeIn     (300ms) — content appears smoothly
  - fadeInUp   (400ms) — cards/panels rise into place
  - fadeInDown (400ms) — page headers descend gracefully
  - gradientShift (6s, infinite) — primary button color animation
                                   (subtle, professional, "alive" feel)

  REMOVED (too noisy / unprofessional):
  - spin, shimmer, wiggle, glow, pulse, pulseRing, bounceIn,
    flipIn, zoomIn, scaleIn, slideInLeft, slideInRight, fadeInRight,
    progressBar, float, shimmerColor

The app now feels CALM and SERIOUS — appropriate for a business
supply chain platform. The remaining animations are only on:
  • Initial page load (fadeIn — content reveals)
  • Card hover states (subtle transform, no infinite loops)
  • Primary button background (slow gradient shift)
"""
from __future__ import annotations

import streamlit as st


# ===========================================================================
# Initialization
# ===========================================================================
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


# ===========================================================================
# GLOBAL CSS — typography, layout, buttons (animations: fadeIn only)
# ===========================================================================
# Load Inter font from Google Fonts — the modern SaaS font used by
# Linear, Vercel, Stripe, Notion, GitHub. Falls back to system stack.
_GLOBAL_CSS = """<style>
/* ===== Inter font (modern commercial typography) ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root {
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace;
}
* { font-family: var(--font-sans) !important; }

/* ===== Keyframe animations (minimal, professional) ===== */
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-8px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* ===== Smooth transitions on interactive elements (no infinite loops) ===== */
.stButton > button,
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div,
.stNumberInput > div > div > input,
[data-testid="stMetric"],
[data-testid="stExpander"],
.stImage img,
.stTabs [data-baseweb="tab"],
[data-baseweb="select"] {
    transition: all 0.2s ease !important;
}

/* ===== Modern buttons — clean, no animations on hover ===== */
.stButton > button {
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.1rem !important;
    border: 1px solid transparent !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.10) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    background-size: 200% 200% !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 2px 6px rgba(16, 185, 129, 0.25) !important;
    animation: gradientShift 6s ease infinite !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 18px rgba(16, 185, 129, 0.35) !important;
    background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
}

/* ===== Headings — Inter font, proper hierarchy ===== */
.stMarkdown h1 {
    font-size: 1.85rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.028em !important;
    line-height: 1.2 !important;
    animation: fadeInDown 0.4s ease-out !important;
    font-feature-settings: "cv11", "ss01" !important;
}
.stMarkdown h2 {
    font-size: 1.45rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.018em !important;
    line-height: 1.25 !important;
}
.stMarkdown h3 {
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.012em !important;
    line-height: 1.3 !important;
}
.stMarkdown h4 {
    font-size: 1.025rem !important;
    font-weight: 600 !important;
    line-height: 1.35 !important;
}
.stMarkdown h5 {
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.045em !important;
}
.stMarkdown h6 {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
}

/* ===== Body text — readable line-height + measure ===== */
.stMarkdown p, .stMarkdown li {
    line-height: 1.6 !important;
    letter-spacing: -0.005em !important;
}
.stMarkdown strong, .stMarkdown b {
    font-weight: 700 !important;
}

/* ===== Metrics — calm, no bouncing ===== */
[data-testid="stMetric"] {
    animation: fadeInUp 0.3s ease-out !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ===== Dataframes ===== */
.stDataFrame {
    font-size: 0.8rem !important;
    border-radius: 8px !important;
    animation: fadeIn 0.3s ease-out !important;
}
.stDataFrame th {
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    font-size: 0.72rem !important;
}

/* ===== Modern slim scrollbar ===== */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: #cbd5e1 !important;
    border-radius: 4px !important;
}
::-webkit-scrollbar-thumb:hover { background: #94a3b8 !important; }

/* ===== Alerts (calm, no bouncing) ===== */
.stAlert {
    border-radius: 8px !important;
    border-left: 4px solid !important;
}

/* ===== Page entrance (just fade, no sliding) ===== */
.stTabs [data-baseweb="tab-panel"] { animation: fadeIn 0.2s ease-out !important; }

/* ===== Image hover (subtle) ===== */
.stImage img {
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    border-radius: 8px !important;
}
.stImage:hover img {
    transform: scale(1.01) !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08) !important;
}

/* ===== File uploader (subtle) ===== */
[data-testid="stFileUploader"] {
    border-radius: 8px !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover { border-color: #10b981 !important; }

/* ===== Spinner (Streamlit's default is fine — no override) ===== */

/* ===== Border containers (minimal motion) ===== */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px !important;
    transition: box-shadow 0.2s ease !important;
    animation: fadeInUp 0.3s ease-out !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.06) !important;
}

/* ===== Sidebar nav buttons — clean, professional ===== */
[data-testid="stSidebar"] .stButton > button {
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    padding: 0.6rem 1rem !important;
    border-radius: 8px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    transition: all 0.15s ease !important;
    border: 1px solid #e2e8f0 !important;
    background: #ffffff !important;
    color: #475569 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    margin-bottom: 3px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #f0fdf4 !important;
    border-color: #6ee7b7 !important;
    color: #047857 !important;
    transform: translateX(2px) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%) !important;
    border-color: #10b981 !important;
    border-left: 3px solid #10b981 !important;
    color: #047857 !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.15) !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary\"]:hover {
    background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%) !important;
}

/* ===== Status dot (no animation — just a static colored circle) ===== */
.pulse-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
}
</style>"""


# ===========================================================================
# LIGHT MODE
# ===========================================================================
_LIGHT_CSS = """<style>
.stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%) !important;
    background-attachment: fixed !important;
    color: #0f172a !important;
}
.main .block-container { color: #0f172a !important; }

[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
    box-shadow: 1px 0 8px rgba(0,0,0,0.03) !important;
    color: #0f172a !important;
}

.stMarkdown h1 {
    background: linear-gradient(135deg, #047857 0%, #10b981 50%, #34d399 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}
h1, h2, h3, h4, h5, h6 { color: #0f172a !important; }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span { color: #1e293b !important; }

.stTextArea > div > label,
.stTextInput > div > label,
.stNumberInput > div > label,
.stSelectbox > div > label,
.stCheckbox > label,
.stRadio > label,
.stFileUploader > div > label { color: #334155 !important; font-weight: 600 !important; }

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
}
.stTextInput > div > div > input:hover,
.stTextArea > div > div > textarea:hover,
.stNumberInput > div > div > input:hover,
.stSelectbox > div > div > div:hover { border-color: #6ee7b7 !important; }
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.12) !important;
}

.stMarkdown code, code {
    background: #f0fdf4 !important;
    color: #047857 !important;
    padding: 0.15em 0.5em !important;
    border-radius: 4px !important;
    font-size: 0.9em !important;
    border: 1px solid #d1fae5 !important;
}
.stCode, pre {
    background: #f8fafc !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
}
.stCode code, pre code { color: #0f172a !important; background: transparent !important; }

.stDataFrame, .stDataFrame table, .stDataFrame th, .stDataFrame td {
    background: #ffffff !important;
    color: #0f172a !important;
}
.stDataFrame th {
    background: #f0fdf4 !important;
    color: #047857 !important;
    border-bottom: 2px solid #10b981 !important;
}

.stMarkdown table, .stMarkdown th, .stMarkdown td {
    color: #0f172a !important;
    border-color: #e2e8f0 !important;
}
.stMarkdown th { background: #f0fdf4 !important; color: #047857 !important; }
.stMarkdown td { background: #ffffff !important; }

[data-testid="stMetric"] {
    background: #ffffff !important;
    padding: 1rem !important;
    border-radius: 10px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    position: relative !important;
    overflow: hidden !important;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px;
    height: 100%;
    background: #10b981 !important;
}
[data-testid="stMetricLabel"] { color: #64748b !important; }

.stExpander {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #0f172a !important;
}
.stExpander:hover {
    border-color: #6ee7b7 !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.06) !important;
}

.stTabs [data-baseweb="tab-list"] { gap: 4px !important; }
.stTabs [data-baseweb="tab"] {
    background: #f8fafc !important;
    color: #64748b !important;
    border-radius: 8px 8px 0 0 !important;
    border-bottom: 3px solid transparent !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
}
.stTabs [data-baseweb="tab\"]:hover { background: #ecfdf5 !important; color: #047857 !important; }
.stTabs [data-baseweb=\"tab\"][aria-selected=\"true\"] {
    background: #ecfdf5 !important;
    color: #047857 !important;
    border-bottom-color: #10b981 !important;
}

[data-testid="stToast"] {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #10b981 !important;
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.15) !important;
    border-radius: 8px !important;
}

a { color: #059669 !important; }
a:hover { color: #047857 !important; text-decoration: underline !important; }

::-webkit-scrollbar-thumb { background: #cbd5e1 !important; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8 !important; }

.auth-card {
    background: #ffffff !important;
    color: #0f172a !important;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08) !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    position: relative !important;
    overflow: hidden !important;
}
.auth-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #10b981 0%, #34d399 50%, #6ee7b7 100%) !important;
}
.auth-title { color: #047857 !important; }
.auth-subtitle { color: #64748b !important; }
.role-card {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    color: #0f172a !important;
    border-radius: 10px !important;
}
.role-card:hover {
    border-color: #6ee7b7 !important;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.08) !important;
}
.role-card.selected {
    background: #ecfdf5 !important;
    border-color: #10b981 !important;
}

[data-testid="stFileUploader"] {
    border-radius: 8px !important;
    background: #f8fafc !important;
}
[data-testid="stFileUploader\"]:hover {
    border-color: #10b981 !important;
    background: #f0fdf4 !important;
}

.stMarkdown hr {
    border: none !important;
    height: 1px !important;
    background: #e2e8f0 !important;
    margin: 1.25rem 0 !important;
}
</style>"""


# ===========================================================================
# DARK MODE
# ===========================================================================
_DARK_CSS = """<style>
.stApp, [data-testid="stAppViewContainer"] {
    background: #0a0e1a !important;
    background-attachment: fixed !important;
    color: #e2e8f0 !important;
}
.main .block-container { color: #e2e8f0 !important; }

[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b !important;
    color: #e2e8f0 !important;
}

.stMarkdown h1 {
    background: linear-gradient(135deg, #34d399 0%, #10b981 50%, #6ee7b7 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

.stRadio > label,
[data-testid="stRadio"] label,
[data-testid="stRadio"] > label,
[data-testid="stRadio\"] p {
    color: #f1f5f9 !important;
    font-weight: 600 !important;
}

.stCheckbox > label,
[data-testid="stCheckbox\"] label,
[data-testid="stCheckbox\"] p {
    color: #f1f5f9 !important;
    font-weight: 600 !important;
}

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
    font-weight: 600 !important;
}

.stCaption, [data-testid="stCaptionContainer\"] { color: #94a3b8 !important; }

.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span { color: #cbd5e1 !important; }
.stMarkdown strong, .stMarkdown b { color: #f8fafc !important; font-weight: 700 !important; }

.stTextInput input, .stNumberInput input { color: #f8fafc !important; }
.stTextInput input::placeholder,
.stTextArea textarea::placeholder,
.stNumberInput input::placeholder { color: #64748b !important; }

.stSelectbox [data-baseweb="select\"] > div,
.stMultiSelect [data-baseweb=\"select\"] > div,
[data-baseweb=\"select\"] > div { color: #f1f5f9 !important; }

[data-testid=\"stSidebar\"] h1,
[data-testid=\"stSidebar\"] h2,
[data-testid=\"stSidebar\"] h3,
[data-testid=\"stSidebar\"] h4,
[data-testid=\"stSidebar\"] h5,
[data-testid=\"stSidebar\"] h6 { color: #f8fafc !important; font-weight: 700 !important; }
[data-testid=\"stSidebar\"] .stMarkdown,
[data-testid=\"stSidebar\"] .stMarkdown p,
[data-testid=\"stSidebar\"] p,
[data-testid=\"stSidebar\"] span,
[data-testid=\"stSidebar\"] label { color: #cbd5e1 !important; }

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: #1e293b !important;
    color: #f1f5f9 !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
.stTextInput > div > div > input:hover,
.stTextArea > div > div > textarea:hover,
.stNumberInput > div > div > input:hover,
.stSelectbox > div > div > div:hover {
    border-color: #10b981 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2) !important;
}

.stMarkdown code, code {
    background: rgba(16, 185, 129, 0.12) !important;
    color: #6ee7b7 !important;
    padding: 0.15em 0.5em !important;
    border-radius: 4px !important;
    font-size: 0.9em !important;
    border: 1px solid rgba(16, 185, 129, 0.25) !important;
}
.stCode, pre {
    background: #060914 !important;
    color: #e2e8f0 !important;
    border: 1px solid #1e293b !important;
    border-radius: 8px !important;
}
.stCode code, pre code { color: #e2e8f0 !important; background: transparent !important; }

.stDataFrame, .stDataFrame table, .stDataFrame th, .stDataFrame td {
    background: #1e293b !important;
    color: #e2e8f0 !important;
}
.stDataFrame th {
    background: rgba(16, 185, 129, 0.15) !important;
    color: #6ee7b7 !important;
    border-bottom: 2px solid #10b981 !important;
}

.stMarkdown table, .stMarkdown th, .stMarkdown td {
    color: #e2e8f0 !important;
    border-color: #334155 !important;
}
.stMarkdown th { background: rgba(16, 185, 129, 0.15) !important; color: #6ee7b7 !important; }
.stMarkdown td { background: #1e293b !important; }

[data-testid=\"stMetric\"] {
    background: #1e293b !important;
    padding: 1rem !important;
    border-radius: 10px !important;
    border: 1px solid #334155 !important;
    position: relative !important;
    overflow: hidden !important;
}
[data-testid=\"stMetric\"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px;
    height: 100%;
    background: #10b981 !important;
}
[data-testid=\"stMetric\"]:hover { border-color: #10b981 !important; }
[data-testid=\"stMetricLabel\"] { color: #94a3b8 !important; }

.stExpander {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
.stExpander:hover { border-color: #10b981 !important; }
.stExpander details summary { color: #e2e8f0 !important; }
.stExpander p, .stExpander li, .stExpander span { color: #cbd5e1 !important; }

.stTabs [data-baseweb=\"tab-list\"] { gap: 4px !important; }
.stTabs [data-baseweb=\"tab\"] {
    background: #1e293b !important;
    color: #94a3b8 !important;
    border-radius: 8px 8px 0 0 !important;
    border-bottom: 3px solid transparent !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb=\"tab\"]:hover { background: rgba(16, 185, 129, 0.1) !important; color: #6ee7b7 !important; }
.stTabs [data-baseweb=\"tab\"][aria-selected=\"true\"] {
    background: rgba(16, 185, 129, 0.15) !important;
    color: #34d399 !important;
    border-bottom-color: #10b981 !important;
}

[data-testid=\"stToast\"] {
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border: 1px solid #10b981 !important;
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.2) !important;
    border-radius: 8px !important;
}

a { color: #34d399 !important; }
a:hover { color: #6ee7b7 !important; }

::-webkit-scrollbar-thumb { background: #475569 !important; }
::-webkit-scrollbar-thumb:hover { background: #10b981 !important; }

.auth-card {
    background: #1e293b !important;
    color: #e2e8f0 !important;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4) !important;
    border: 1px solid #334155 !important;
    border-radius: 16px !important;
    position: relative !important;
    overflow: hidden !important;
}
.auth-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #10b981 0%, #34d399 50%, #6ee7b7 100%) !important;
}
.auth-title { color: #6ee7b7 !important; }
.auth-subtitle { color: #94a3b8 !important; }
.role-card {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
}
.role-card:hover { border-color: #10b981 !important; }
.role-card.selected {
    background: rgba(16, 185, 129, 0.15) !important;
    border-color: #10b981 !important;
}

[data-testid=\"stFileUploader\"] {
    border-radius: 8px !important;
    background: #1e293b !important;
}
[data-testid=\"stFileUploader\"]:hover { border-color: #10b981 !important; }

.stMarkdown hr {
    border: none !important;
    height: 1px !important;
    background: #334155 !important;
    margin: 1.25rem 0 !important;
}

[data-testid=\"stSidebar\"] .stButton > button {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #cbd5e1 !important;
}
[data-testid=\"stSidebar\"] .stButton > button:hover {
    background: rgba(16, 185, 129, 0.12) !important;
    border-color: #10b981 !important;
    color: #6ee7b7 !important;
}
[data-testid=\"stSidebar\"] .stButton > button[kind=\"primary\"] {
    background: rgba(16, 185, 129, 0.15) !important;
    border-color: #10b981 !important;
    border-left: 3px solid #34d399 !important;
    color: #6ee7b7 !important;
    font-weight: 700 !important;
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
