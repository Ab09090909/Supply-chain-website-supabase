"""
Theme toggle — dark/light mode + global animations for the whole app.

v5 updates:
  • New color palette: emerald + slate (light), deep navy + emerald (dark)
  • Smooth transitions on all interactive elements
  • Fade-in animations on page load
  • Hover effects on cards and buttons
  • Loading shimmer for data loading
"""
from __future__ import annotations

import streamlit as st


def init_theme():
    """Initialize theme state. Call once at app startup."""
    if "theme" not in st.session_state:
        st.session_state["theme"] = "light"


def render_theme_toggle():
    """Render a light/dark toggle in the sidebar."""
    init_theme()
    current = st.session_state["theme"]

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
    """Inject CSS for the current theme + global animations. Call once per page render."""
    init_theme()

    # Global animations CSS (applies to both themes)
    animations_css = """
    <style>
    /* ===== GLOBAL ANIMATIONS ===== */

    /* Fade-in on page load */
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
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.03); }
    }
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }

    /* Apply fade-in to main content blocks */
    .stApp > div > div > div {
        animation: fadeInUp 0.4s ease-out;
    }

    /* Smooth transitions on ALL interactive elements */
    .stButton > button,
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input,
    .stCheckbox,
    .stRadio,
    [data-testid="stMetric"] {
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    /* Button hover effects */
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.25) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* Card hover effects (containers with borders) */
    [data-testid="stVerticalBlock"] > div [data-testid="stHorizontalBlock"] {
        transition: all 0.3s ease !important;
    }

    /* Expander smooth expand */
    .stExpander {
        transition: all 0.3s ease !important;
    }

    /* Sidebar slide-in on load */
    [data-testid="stSidebar"] {
        animation: slideInLeft 0.4s ease-out !important;
    }

    /* Tab transitions */
    .stTabs [data-baseweb="tab-panel"] {
        animation: fadeIn 0.3s ease-out !important;
    }

    /* Toast notification animation */
    [data-testid="stToast"] {
        animation: fadeInUp 0.3s ease-out !important;
    }

    /* Metric value pulse on update */
    [data-testid="stMetricValue"] {
        animation: fadeIn 0.5s ease-out !important;
    }

    /* Image hover zoom */
    .stImage img {
        transition: transform 0.3s ease !important;
        border-radius: 8px !important;
    }

    /* Loading spinner */
    .stSpinner > div {
        animation: spin 1s linear infinite !important;
    }
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

    /* Link hover */
    a {
        transition: color 0.2s ease !important;
    }
    a:hover {
        text-decoration: underline !important;
    }

    /* Form submit button special effect */
    .stFormSubmitButton > button {
        position: relative;
        overflow: hidden;
    }
    .stFormSubmitButton > button::after {
        content: '';
        position: absolute;
        top: 50%; left: 50%;
        width: 0; height: 0;
        border-radius: 50%;
        background: rgba(255,255,255,0.3);
        transform: translate(-50%, -50%);
        transition: width 0.4s, height 0.4s;
    }
    .stFormSubmitButton > button:active::after {
        width: 300px; height: 300px;
    }
    </style>
    """

    if st.session_state["theme"] == "dark":
        dark_css = """
        <style>
        /* ===== DARK MODE — Deep navy + emerald accents ===== */
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
        .stCard, [data-testid="stVerticalBlock"] > div,
        .stContainer > div {
            background: rgba(30, 41, 59, 0.8) !important;
            color: #e2e8f0 !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
            backdrop-filter: blur(10px) !important;
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
            font-weight: 600 !important;
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
            backdrop-filter: blur(20px) !important;
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
        /* Custom scrollbar */
        ::-webkit-scrollbar-thumb { background: #475569 !important; }
        ::-webkit-scrollbar-thumb:hover { background: #64748b !important; }
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
        </style>
        """
        st.markdown(animations_css + dark_css, unsafe_allow_html=True)
    else:
        light_css = """
        <style>
        /* ===== LIGHT MODE — Clean white + emerald accents ===== */
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
        }
        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid #e2e8f0 !important;
            box-shadow: 2px 0 8px rgba(0,0,0,0.03) !important;
        }
        /* Cards get subtle shadow + emerald accent on hover */
        .stCard, [data-testid="stVerticalBlock"] > div,
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
