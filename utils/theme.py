"""
Theme toggle — dark/light mode switcher for the whole app.

Streamlit doesn't natively support runtime theme switching, so we inject
CSS based on a session_state flag. The toggle is rendered in the sidebar.
"""
from __future__ import annotations

import streamlit as st


def init_theme():
    """Initialize theme state. Call once at app startup."""
    if "theme" not in st.session_state:
        # Default: light (matches original green theme)
        st.session_state["theme"] = "light"


def render_theme_toggle():
    """Render a light/dark toggle in the sidebar."""
    init_theme()
    current = st.session_state["theme"]

    # Use a styled radio that looks like a toggle
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("☀️ Light", use_container_width=True,
                     type="primary" if current == "light" else "secondary",
                     key="theme_light_btn"):
            if current != "light":
                st.session_state["theme"] = "light"
                st.rerun()
    with col2:
        if st.button("🌙 Dark", use_container_width=True,
                     type="primary" if current == "dark" else "secondary",
                     key="theme_dark_btn"):
            if current != "dark":
                st.session_state["theme"] = "dark"
                st.rerun()


def apply_theme_css():
    """Inject CSS for the current theme. Call this once per page render."""
    init_theme()
    if st.session_state["theme"] == "dark":
        st.markdown(
            """
            <style>
            /* Dark mode — applied to the main app container */
            .stApp, [data-testid="stAppViewContainer"] {
                background-color: #0f172a !important;
                color: #e2e8f0 !important;
            }
            [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
                background-color: #1e293b !important;
                color: #e2e8f0 !important;
            }
            /* Cards / containers */
            .stCard, [data-testid="stVerticalBlock"] > div,
            .stContainer > div {
                background-color: #1e293b !important;
                color: #e2e8f0 !important;
                border-color: #334155 !important;
            }
            /* Inputs */
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea,
            .stNumberInput > div > div > input,
            .stSelectbox > div > div > div {
                background-color: #0f172a !important;
                color: #e2e8f0 !important;
                border-color: #334155 !important;
            }
            /* Data frames */
            .stDataFrame, .stDataFrame table, .stDataFrame th, .stDataFrame td {
                background-color: #1e293b !important;
                color: #e2e8f0 !important;
            }
            /* Markdown text */
            .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {
                color: #e2e8f0 !important;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #f1f5f9 !important;
            }
            /* Auth cards (custom CSS class used in auth/pages.py) */
            .auth-card {
                background: #1e293b !important;
                color: #e2e8f0 !important;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
                border: 1px solid #334155 !important;
            }
            .auth-title { color: #f1f5f9 !important; }
            .auth-subtitle { color: #94a3b8 !important; }
            .role-card {
                background: #0f172a !important;
                border-color: #334155 !important;
            }
            /* Metric cards */
            [data-testid="stMetric"] {
                background-color: #1e293b !important;
                padding: 1rem !important;
                border-radius: 8px !important;
                border: 1px solid #334155 !important;
            }
            [data-testid="stMetricLabel"] { color: #94a3b8 !important; }
            [data-testid="stMetricValue"] { color: #f1f5f9 !important; }
            /* Expander */
            .stExpander {
                background-color: #1e293b !important;
                border-color: #334155 !important;
            }
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] { background-color: transparent !important; }
            .stTabs [data-baseweb="tab"] {
                background-color: #1e293b !important;
                color: #e2e8f0 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Light mode — minimal overrides (default Streamlit light theme)
        st.markdown(
            """
            <style>
            /* Light mode — clean defaults */
            .stApp { background-color: #ffffff !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
