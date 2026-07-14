"""
Theme toggle — dark/light mode + global animations for the whole app.

v5 fix: Uses st.toggle instead of st.button for reliable state persistence.
The toggle widget natively stores its state in session_state, so the theme
survives reruns without needing st.rerun() hacks.
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

    # st.toggle natively persists state via its widget key
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


def apply_theme_css():
    """Inject CSS for the current theme + global animations."""
    init_theme()
    theme = st.session_state.get("app_theme", "light")

    # Global animations CSS (applies to both themes)
    animations_css = """
    <style>
    /* ===== GLOBAL ANIMATIONS ===== */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    /* Apply fade-in to main content */
    .stApp > div > div > div {
        animation: fadeInUp 0.4s ease-out;
    }

    /* Smooth transitions on interactive elements */
    .stButton > button,
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input,
    [data-testid="stMetric"] {
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    /* Button hover effects */
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.25) !important;
    }

    /* Sidebar slide-in */
    [data-testid="stSidebar"] {
        animation: slideInLeft 0.4s ease-out !important;
    }

    /* Tab transitions */
    .stTabs [data-baseweb="tab-panel"] {
        animation: fadeIn 0.3s ease-out !important;
    }

    /* Image hover zoom */
    .stImage img {
        transition: transform 0.3s ease !important;
        border-radius: 8px !important;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

    /* Link hover */
    a { transition: color 0.2s ease !important; }
    a:hover { text-decoration: underline !important; }
    </style>
    """

    if theme == "dark":
        dark_css = """
        <style>
        /* ===== DARK MODE ===== */
        .stApp, [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
            color: #e2e8f0 !important;
        }
        [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
            background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important;
            color: #e2e8f0 !important;
            border-right: 1px solid #334155 !important;
        }
        /* Cards */
        [data-testid="stVerticalBlock"] > div,
        .stContainer > div {
            background: rgba(30, 41, 59, 0.8) !important;
            color: #e2e8f0 !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
        }
        /* Inputs */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > div {
            background: rgba(15, 23, 42, 0.9) !important;
            color: #e2e8f0 !important;
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
        }
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #10b981 !important;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15) !important;
        }
        /* Data frames */
        .stDataFrame, .stDataFrame table, .stDataFrame th, .stDataFrame td {
            background: rgba(30, 41, 59, 0.9) !important;
            color: #e2e8f0 !important;
        }
        .stDataFrame th {
            background: #334155 !important;
            color: #10b981 !important;
        }
        /* Markdown text */
        .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {
            color: #cbd5e1 !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #f1f5f9 !important;
        }
        /* Auth cards */
        .auth-card {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
            color: #e2e8f0 !important;
            box-shadow: 0 12px 40px rgba(0,0,0,0.5) !important;
            border: 1px solid #334155 !important;
        }
        .auth-title { color: #f1f5f9 !important; }
        .auth-subtitle { color: #94a3b8 !important; }
        .role-card {
            background: rgba(15, 23, 42, 0.8) !important;
            border-color: #334155 !important;
        }
        /* Metrics */
        [data-testid="stMetric"] {
            background: rgba(30, 41, 59, 0.6) !important;
            padding: 1rem !important;
            border-radius: 12px !important;
            border: 1px solid #334155 !important;
        }
        [data-testid="stMetricLabel"] { color: #94a3b8 !important; }
        [data-testid="stMetricValue"] { color: #10b981 !important; }
        /* Expander */
        .stExpander {
            background: rgba(30, 41, 59, 0.6) !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
        }
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 4px !important; }
        .stTabs [data-baseweb="tab"] {
            background: rgba(30, 41, 59, 0.5) !important;
            color: #94a3b8 !important;
            border-radius: 8px 8px 0 0 !important;
            border-bottom: 3px solid transparent !important;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: rgba(16, 185, 129, 0.15) !important;
            color: #10b981 !important;
            border-bottom-color: #10b981 !important;
        }
        /* Scrollbar */
        ::-webkit-scrollbar-thumb { background: #475569 !important; }
        /* Code blocks */
        .stCode {
            background: #0f172a !important;
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
        }
        /* Alerts */
        .stAlert {
            border-radius: 10px !important;
            animation: fadeInUp 0.3s ease-out !important;
        }
        /* Text areas and their labels */
        .stTextArea > div > label,
        .stTextInput > div > label,
        .stNumberInput > div > label,
        .stSelectbox > div > label {
            color: #cbd5e1 !important;
        }
        /* Data editor */
        .stDataFrame [data-testid="stDataFrameResizable"] {
            background: rgba(30, 41, 59, 0.6) !important;
        }
        /* Chat elements */
        [data-testid="stChatMessage"] {
            background: rgba(30, 41, 59, 0.8) !important;
            border: 1px solid #334155 !important;
        }
        /* Spinner */
        .stSpinner > div {
            border-color: #10b981 transparent transparent transparent !important;
        }
        </style>
        """
        st.markdown(animations_css + dark_css, unsafe_allow_html=True)
    else:
        light_css = """
        <style>
        /* ===== LIGHT MODE ===== */
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
        }
        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid #e2e8f0 !important;
            box-shadow: 2px 0 8px rgba(0,0,0,0.03) !important;
        }
        /* Cards */
        [data-testid="stVerticalBlock"] > div,
        .stContainer > div {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        }
        /* Inputs */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > div {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
        }
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #10b981 !important;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.12) !important;
        }
        /* Data frames */
        .stDataFrame th {
            background: #f1f5f9 !important;
            color: #047857 !important;
            font-weight: 600 !important;
        }
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
        /* Alerts */
        .stAlert {
            border-radius: 10px !important;
            animation: fadeInUp 0.3s ease-out !important;
        }
        </style>
        """
        st.markdown(animations_css + light_css, unsafe_allow_html=True)
