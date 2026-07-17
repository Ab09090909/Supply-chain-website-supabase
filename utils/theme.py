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
# GLOBAL CSS — applies to both themes (transitions, animations, polish)
# ---------------------------------------------------------------------------
_GLOBAL_CSS = """<style>
/* ===== Keyframe animations ===== */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-12px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-16px); }
    to { opacity: 1; transform: translateX(0); }
}
@keyframes slideInRight {
    from { opacity: 0; transform: translateX(16px); }
    to { opacity: 1; transform: translateX(0); }
}
@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.96); }
    to { opacity: 1; transform: scale(1); }
}
@keyframes fadeInRight {
    from { opacity: 0; transform: translateX(12px); }
    to { opacity: 1; transform: translateX(0); }
}
@keyframes zoomIn {
    from { opacity: 0; transform: scale(0.85); }
    to { opacity: 1; transform: scale(1); }
}
@keyframes flipIn {
    from { opacity: 0; transform: perspective(600px) rotateY(-90deg); }
    to { opacity: 1; transform: perspective(600px) rotateY(0deg); }
}
@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50%      { transform: scale(1.05); opacity: 0.85; }
}
@keyframes pulseRing {
    0%   { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5); }
    70%  { box-shadow: 0 0 0 12px rgba(16, 185, 129, 0); }
    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}
@keyframes shimmer {
    0%   { background-position: -800px 0; }
    100% { background-position: 800px 0; }
}
@keyframes shimmerColor {
    0%   { background-position: -400px 0; }
    100% { background-position: 400px 0; }
}
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50%      { transform: translateY(-6px); }
}
@keyframes glow {
    0%, 100% { box-shadow: 0 0 16px rgba(16, 185, 129, 0.25); }
    50%      { box-shadow: 0 0 28px rgba(16, 185, 129, 0.55); }
}
@keyframes spin {
    to { transform: rotate(360deg); }
}
@keyframes bounceIn {
    0%   { opacity: 0; transform: scale(0.7); }
    60%  { opacity: 1; transform: scale(1.06); }
    100% { transform: scale(1); }
}
@keyframes wiggle {
    0%, 100% { transform: rotate(0deg); }
    25%      { transform: rotate(-2deg); }
    75%      { transform: rotate(2deg); }
}
@keyframes progressBar {
    0%   { width: 0%; }
    100% { width: 100%; }
}

/* ===== Smooth transitions for all interactive elements ===== */
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
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* ===== Modern gradient buttons ===== */
.stButton > button {
    border-radius: 10px !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.1rem !important;
    border: 1px solid transparent !important;
    position: relative !important;
    overflow: hidden !important;
}
.stButton > button::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    transform: translate(-50%, -50%);
    transition: width 0.4s ease, height 0.4s ease;
}
.stButton > button:hover::before {
    width: 300px;
    height: 300px;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(16, 185, 129, 0.25) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #10b981 0%, #059669 50%, #047857 100%) !important;
    background-size: 200% 200% !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3) !important;
    animation: gradientShift 6s ease infinite !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4) !important;
}

/* ===== Headings — modern hierarchy ===== */
.stMarkdown h1 {
    font-size: 1.75rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    animation: fadeInDown 0.4s ease-out !important;
}
.stMarkdown h2 {
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em !important;
}
.stMarkdown h3 {
    font-size: 1.15rem !important;
    font-weight: 700 !important;
}
.stMarkdown h4 {
    font-size: 1rem !important;
    font-weight: 600 !important;
}
.stMarkdown h5 {
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
}
.stMarkdown h6 {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
}

/* ===== Metrics — animated KPI cards ===== */
[data-testid="stMetric"] {
    animation: fadeInUp 0.4s ease-out backwards !important;
    position: relative !important;
    overflow: hidden !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px) !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.65rem !important;
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

/* ===== Captions ===== */
.stCaption { font-size: 0.75rem !important; }

/* ===== Dataframes — modern look ===== */
.stDataFrame {
    font-size: 0.8rem !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    animation: fadeIn 0.3s ease-out !important;
}
.stDataFrame th {
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    font-size: 0.72rem !important;
}

/* ===== Scrollbar — modern slim ===== */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #cbd5e1, #94a3b8) !important;
    border-radius: 4px !important;
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #94a3b8, #64748b) !important;
}

/* ===== Alerts — animated ===== */
.stAlert {
    border-radius: 12px !important;
    animation: slideInLeft 0.3s ease-out !important;
    border-left: 4px solid !important;
}

/* ===== Sidebar — subtle entrance ===== */
[data-testid="stSidebar"] { animation: slideInLeft 0.4s ease-out !important; }

/* ===== Tabs — animated underline ===== */
.stTabs [data-baseweb="tab-panel"] { animation: fadeIn 0.25s ease-out !important; }
.stTabs [data-baseweb="tab"] {
    transition: all 0.2s ease !important;
    border-radius: 10px 10px 0 0 !important;
}
.stTabs [data-baseweb="tab"]:hover {
    transform: translateY(-1px) !important;
}

/* ===== Image styling ===== */
.stImage img {
    transition: transform 0.3s ease, box-shadow 0.3s ease !important;
    border-radius: 10px !important;
}
.stImage:hover img {
    transform: scale(1.02) !important;
    box-shadow: 0 8px 20px rgba(0,0,0,0.12) !important;
}

/* ===== File uploader — modern ===== */
[data-testid="stFileUploader"] {
    border-radius: 12px !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #10b981 !important;
}

/* ===== Progress bar ===== */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #10b981 0%, #34d399 50%, #10b981 100%) !important;
    background-size: 200% 100% !important;
    animation: gradientShift 2s linear infinite !important;
    border-radius: 4px !important;
}

/* ===== Spinner ===== */
.stSpinner > div {
    border-color: #10b981 transparent transparent transparent !important;
    animation: spin 0.7s linear infinite !important;
}

/* ===== Container borders — modern cards ===== */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
    transition: box-shadow 0.25s ease, transform 0.25s ease !important;
    animation: fadeInUp 0.35s ease-out backwards !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 8px 24px rgba(0,0,0,0.08) !important;
}

/* ===== Checkbox + radio — modern touch ===== */
.stCheckbox, [data-testid="stCheckbox"] {
    transition: all 0.2s ease !important;
}

/* ===== Slider ===== */
.stSlider [data-baseweb="slider"] [role="slider"] {
    transition: all 0.2s ease !important;
}
.stSlider [data-baseweb="slider"] [role="slider"]:hover {
    transform: scale(1.15) !important;
}

/* ===== Tooltip-like helpers ===== */
[data-testid="stTooltipHoverTarget"] {
    transition: all 0.2s ease !important;
}

/* ===== Banner / page header animation ===== */
.page-header, .auth-card, .role-card {
    animation: scaleIn 0.35s ease-out !important;
}

/* ===== Sidebar nav buttons — beautiful nav cards ===== */
[data-testid="stSidebar"] .stButton > button {
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    padding: 0.65rem 1rem !important;
    border-radius: 10px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    position: relative !important;
    transition: all 0.2s ease !important;
    border: 1px solid #e2e8f0 !important;
    background: #ffffff !important;
    color: #475569 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    margin-bottom: 4px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #f0fdf4 !important;
    border-color: #6ee7b7 !important;
    color: #047857 !important;
    transform: translateX(2px) !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.12) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%) !important;
    border-color: #10b981 !important;
    border-left: 4px solid #10b981 !important;
    color: #047857 !important;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2) !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%) !important;
    transform: translateX(2px) !important;
}

/* ===== Decorative animated badge (pulsing dot) ===== */
.pulse-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    animation: pulse 1.5s ease-in-out infinite;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5);
}

/* ===== Loading shimmer ===== */
.shimmer {
    background: linear-gradient(90deg,
        rgba(255,255,255,0) 0%,
        rgba(255,255,255,0.3) 50%,
        rgba(255,255,255,0) 100%);
    background-size: 800px 100%;
    animation: shimmer 2s linear infinite;
}

/* ===== Notification badge bounce ===== */
.notif-badge {
    display: inline-block;
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: white;
    border-radius: 10px;
    padding: 1px 7px;
    font-size: 0.7rem;
    font-weight: 700;
    animation: bounceIn 0.5s ease-out;
}
</style>"""


# ---------------------------------------------------------------------------
# LIGHT MODE — vibrant, modern, colorful
# ---------------------------------------------------------------------------
_LIGHT_CSS = """<style>
/* App background — subtle animated gradient */
.stApp, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(at 0% 0%, rgba(167, 243, 208, 0.18) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(196, 181, 253, 0.15) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(253, 230, 138, 0.12) 0px, transparent 50%),
        linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
    background-attachment: fixed !important;
    color: #0f172a !important;
}
.main .block-container { color: #0f172a !important; }

/* Sidebar */
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
    border-right: 1px solid #e2e8f0 !important;
    box-shadow: 2px 0 12px rgba(0,0,0,0.04) !important;
    color: #0f172a !important;
}

/* Headers — colorful gradient text for h1 */
.stMarkdown h1 {
    background: linear-gradient(135deg, #047857 0%, #10b981 50%, #34d399 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}
h1, h2, h3, h4, h5, h6 { color: #0f172a !important; }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span { color: #1e293b !important; }

/* Form labels */
.stTextArea > div > label,
.stTextInput > div > label,
.stNumberInput > div > label,
.stSelectbox > div > label,
.stCheckbox > label,
.stRadio > label,
.stFileUploader > div > label { color: #334155 !important; font-weight: 600 !important; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
}
.stTextInput > div > div > input:hover,
.stTextArea > div > div > textarea:hover,
.stNumberInput > div > div > input:hover,
.stSelectbox > div > div > div:hover {
    border-color: #6ee7b7 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15) !important;
    background: #ffffff !important;
}

/* Code */
.stMarkdown code, code {
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%) !important;
    color: #047857 !important;
    padding: 0.15em 0.5em !important;
    border-radius: 6px !important;
    font-size: 0.9em !important;
    border: 1px solid #a7f3d0 !important;
}
.stCode, pre {
    background: #f8fafc !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
}
.stCode code, pre code { color: #0f172a !important; background: transparent !important; }

/* Dataframes — colorful header */
.stDataFrame, .stDataFrame table, .stDataFrame th, .stDataFrame td {
    background: #ffffff !important;
    color: #0f172a !important;
}
.stDataFrame th {
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%) !important;
    color: #047857 !important;
    border-bottom: 2px solid #10b981 !important;
}

/* Tables */
.stMarkdown table, .stMarkdown th, .stMarkdown td {
    color: #0f172a !important;
    border-color: #e2e8f0 !important;
}
.stMarkdown th {
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%) !important;
    color: #047857 !important;
}
.stMarkdown td { background: #ffffff !important; }

/* Metrics — colorful gradient cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%) !important;
    padding: 1.1rem !important;
    border-radius: 14px !important;
    border: 1px solid #d1fae5 !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.08) !important;
    position: relative !important;
    overflow: hidden !important;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, #10b981 0%, #34d399 100%) !important;
}
[data-testid="stMetricLabel"] { color: #64748b !important; }
[data-testid="stMetricValue"] {
    background: linear-gradient(135deg, #047857 0%, #10b981 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

/* Expander */
.stExpander {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    color: #0f172a !important;
    transition: all 0.2s ease !important;
}
.stExpander:hover {
    border-color: #6ee7b7 !important;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.08) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 4px !important; }
.stTabs [data-baseweb="tab"] {
    background: #f8fafc !important;
    color: #64748b !important;
    border-radius: 10px 10px 0 0 !important;
    border-bottom: 3px solid transparent !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: #ecfdf5 !important;
    color: #047857 !important;
    transform: translateY(-1px) !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%) !important;
    color: #047857 !important;
    border-bottom-color: #10b981 !important;
}

/* Toast */
[data-testid="stToast"] {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #10b981 !important;
    box-shadow: 0 8px 24px rgba(16, 185, 129, 0.2) !important;
    border-radius: 12px !important;
}

/* Links */
a { color: #059669 !important; }
a:hover { color: #047857 !important; text-decoration: underline !important; }

/* Scrollbar thumb */
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #cbd5e1, #94a3b8) !important;
    border-radius: 4px !important;
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #10b981, #059669) !important;
}

/* Auth card — colorful gradient */
.auth-card {
    background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%) !important;
    color: #0f172a !important;
    box-shadow: 0 20px 50px rgba(16, 185, 129, 0.15) !important;
    border: 1px solid #d1fae5 !important;
    border-radius: 20px !important;
    position: relative !important;
    overflow: hidden !important;
}
.auth-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #10b981 0%, #34d399 50%, #6ee7b7 100%) !important;
}
.auth-title { color: #047857 !important; }
.auth-subtitle { color: #64748b !important; }
.role-card {
    background: #ffffff !important;
    border-color: #e2e8f0 !important;
    color: #0f172a !important;
    border-radius: 14px !important;
    transition: all 0.2s ease !important;
}
.role-card:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(16, 185, 129, 0.1) !important;
    border-color: #6ee7b7 !important;
}
.role-card.selected {
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%) !important;
    border-color: #10b981 !important;
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.2) !important;
}

/* File uploader — colorful hover */
[data-testid="stFileUploader"] {
    border-radius: 12px !important;
    background: #f8fafc !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #10b981 !important;
    background: #f0fdf4 !important;
}

/* Decorative elements */
.stMarkdown hr {
    border: none !important;
    height: 2px !important;
    background: linear-gradient(90deg, transparent, #d1fae5, transparent) !important;
    margin: 1.5rem 0 !important;
}
</style>"""


# ---------------------------------------------------------------------------
# DARK MODE — vibrant emerald + deep slate, with colored highlights
# ---------------------------------------------------------------------------
_DARK_CSS = """<style>
/* App background — deep navy with colorful radial accents */
.stApp, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(at 10% 10%, rgba(16, 185, 129, 0.15) 0px, transparent 50%),
        radial-gradient(at 90% 20%, rgba(139, 92, 246, 0.12) 0px, transparent 50%),
        radial-gradient(at 50% 90%, rgba(59, 130, 246, 0.1) 0px, transparent 50%),
        linear-gradient(135deg, #0a0e1a 0%, #0f172a 60%, #1e293b 100%) !important;
    background-attachment: fixed !important;
    color: #e2e8f0 !important;
}
.main .block-container { color: #e2e8f0 !important; }

/* Sidebar */
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
    background: linear-gradient(180deg, #060914 0%, #0f172a 100%) !important;
    border-right: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    box-shadow: 2px 0 16px rgba(0,0,0,0.4) !important;
}

/* H1 — gradient emerald text */
.stMarkdown h1 {
    background: linear-gradient(135deg, #34d399 0%, #10b981 50%, #6ee7b7 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

/* Radio buttons (Navigation) — highly visible */
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

/* Form labels */
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
}

/* Captions */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #cbd5e1 !important;
    font-weight: 500 !important;
}

/* Markdown text */
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {
    color: #e2e8f0 !important;
    font-weight: 500 !important;
}
.stMarkdown strong, .stMarkdown b {
    color: #f8fafc !important;
    font-weight: 700 !important;
}

/* Text input / number input text */
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

/* Selectbox / multiselect */
.stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div,
[data-baseweb="select"] > div {
    color: #f1f5f9 !important;
    font-weight: 500 !important;
}

/* Sidebar nav */
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

.stCaption { color: #94a3b8 !important; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: rgba(15, 23, 42, 0.7) !important;
    color: #f1f5f9 !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
}
.stTextInput > div > div > input:hover,
.stTextArea > div > div > textarea:hover,
.stNumberInput > div > div > input:hover,
.stSelectbox > div > div > div:hover {
    border-color: #10b981 !important;
    background: rgba(15, 23, 42, 0.9) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25) !important;
    background: rgba(15, 23, 42, 0.95) !important;
}

/* Code */
.stMarkdown code, code {
    background: rgba(16, 185, 129, 0.15) !important;
    color: #6ee7b7 !important;
    padding: 0.15em 0.5em !important;
    border-radius: 6px !important;
    font-size: 0.9em !important;
    border: 1px solid rgba(16, 185, 129, 0.3) !important;
}
.stCode, pre {
    background: #060914 !important;
    color: #e2e8f0 !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}
.stCode code, pre code { color: #e2e8f0 !important; background: transparent !important; }

/* Dataframes — emerald header */
.stDataFrame, .stDataFrame table, .stDataFrame th, .stDataFrame td {
    background: rgba(15, 23, 42, 0.6) !important;
    color: #e2e8f0 !important;
}
.stDataFrame th {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(52, 211, 153, 0.15) 100%) !important;
    color: #6ee7b7 !important;
    border-bottom: 2px solid #10b981 !important;
}

/* Tables */
.stMarkdown table, .stMarkdown th, .stMarkdown td {
    color: #e2e8f0 !important;
    border-color: #334155 !important;
}
.stMarkdown th {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(52, 211, 153, 0.15) 100%) !important;
    color: #6ee7b7 !important;
}
.stMarkdown td { background: rgba(15, 23, 42, 0.5) !important; }

/* Metrics — colorful gradient cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.7) 100%) !important;
    padding: 1.1rem !important;
    border-radius: 14px !important;
    border: 1px solid #334155 !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3) !important;
    position: relative !important;
    overflow: hidden !important;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, #34d399 0%, #10b981 100%) !important;
}
[data-testid="stMetric"]:hover {
    border-color: #10b981 !important;
    box-shadow: 0 8px 24px rgba(16, 185, 129, 0.2) !important;
}
[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
[data-testid="stMetricValue"] {
    background: linear-gradient(135deg, #34d399 0%, #6ee7b7 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

/* Expander */
.stExpander {
    background: rgba(15, 23, 42, 0.5) !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    transition: all 0.2s ease !important;
}
.stExpander:hover {
    border-color: #10b981 !important;
    background: rgba(15, 23, 42, 0.7) !important;
}
.stExpander details summary { color: #e2e8f0 !important; }
.stExpander p, .stExpander li, .stExpander span { color: #cbd5e1 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 4px !important; }
.stTabs [data-baseweb="tab"] {
    background: rgba(30, 41, 59, 0.5) !important;
    color: #cbd5e1 !important;
    border-radius: 10px 10px 0 0 !important;
    border-bottom: 3px solid transparent !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(16, 185, 129, 0.1) !important;
    color: #6ee7b7 !important;
    transform: translateY(-1px) !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(52, 211, 153, 0.15) 100%) !important;
    color: #34d399 !important;
    border-bottom-color: #10b981 !important;
}

/* Toast */
[data-testid="stToast"] {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    color: #e2e8f0 !important;
    border: 1px solid #10b981 !important;
    box-shadow: 0 8px 24px rgba(16, 185, 129, 0.25) !important;
    border-radius: 12px !important;
}

/* Links */
a { color: #34d399 !important; }
a:hover { color: #6ee7b7 !important; }

/* Scrollbar thumb */
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #475569, #334155) !important;
    border-radius: 4px !important;
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #10b981, #34d399) !important;
}

/* Auth card */
.auth-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    color: #e2e8f0 !important;
    box-shadow: 0 20px 50px rgba(0,0,0,0.5), 0 0 0 1px rgba(16, 185, 129, 0.2) !important;
    border: 1px solid #334155 !important;
    border-radius: 20px !important;
    position: relative !important;
    overflow: hidden !important;
}
.auth-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #10b981 0%, #34d399 50%, #6ee7b7 100%) !important;
}
.auth-title { color: #6ee7b7 !important; }
.auth-subtitle { color: #94a3b8 !important; }
.role-card {
    background: rgba(15, 23, 42, 0.8) !important;
    border-color: #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 14px !important;
    transition: all 0.2s ease !important;
}
.role-card:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(16, 185, 129, 0.2) !important;
    border-color: #10b981 !important;
}
.role-card.selected {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(52, 211, 153, 0.15) 100%) !important;
    border-color: #10b981 !important;
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3) !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    border-radius: 12px !important;
    background: rgba(15, 23, 42, 0.5) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #10b981 !important;
    background: rgba(16, 185, 129, 0.1) !important;
}

/* Decorative elements */
.stMarkdown hr {
    border: none !important;
    height: 2px !important;
    background: linear-gradient(90deg, transparent, rgba(16, 185, 129, 0.4), transparent) !important;
    margin: 1.5rem 0 !important;
}

/* ===== Sidebar nav buttons (dark mode) ===== */
[data-testid="stSidebar"] .stButton > button {
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid #334155 !important;
    color: #cbd5e1 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(16, 185, 129, 0.15) !important;
    border-color: #10b981 !important;
    color: #6ee7b7 !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(52, 211, 153, 0.15) 100%) !important;
    border-color: #10b981 !important;
    border-left: 4px solid #34d399 !important;
    color: #6ee7b7 !important;
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3) !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(52, 211, 153, 0.2) 100%) !important;
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
