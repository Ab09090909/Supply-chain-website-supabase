"""
AI Assistant chat page — powered by Groq API.

A floating chat interface where users can ask questions about the platform.
The assistant ONLY answers questions about this platform's features.
"""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user, get_current_role
from utils.ui import page_header
from ai.assistant import chat_with_assistant, is_assistant_available


def render_ai_assistant():
    page_header("💬 AI Assistant", "Ask me anything about the AI Supply Chain Platform")

    user = get_current_user()
    if not user:
        return

    # --- Availability check ---
    if not is_assistant_available():
        st.warning("⚠️ AI Assistant is not configured yet.")
        st.info(
            "**To enable the AI Assistant:**\n\n"
            "1. Get a FREE API key from [Groq Console](https://console.groq.com/keys)\n"
            "2. Add it to your Streamlit secrets:\n"
            "```\n"
            "GROQ_API_KEY = \"gsk_your_key_here\"\n"
            "```\n"
            "3. Restart the app.\n\n"
            "The Groq API is free and fast — perfect for this assistant."
        )
        return

    # --- Intro ---
    st.info(
        "👋 Hi! I'm your AI Supply Chain Platform assistant. I can help you with:\n"
        "- 🛒 How to use the marketplace\n"
        "- 📦 How to add products and manage inventory\n"
        "- 🤖 How AI predictions and recommendations work\n"
        "- 🤝 How merchant matching works\n"
        "- 🔔 Notifications and messaging\n"
        "- ⚙️ Setting up your preferences\n"
        "- 💰 Orders, agreements, and payments\n\n"
        "**I only answer questions about this platform.** Ask me anything!"
    )

    # --- Chat history in session_state ---
    if "assistant_chat" not in st.session_state:
        st.session_state["assistant_chat"] = []

    # --- Display chat history ---
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state["assistant_chat"]:
            if msg["role"] == "user":
                _render_user_bubble(msg["content"])
            else:
                _render_assistant_bubble(msg["content"])

    # --- Quick suggestion buttons ---
    if not st.session_state["assistant_chat"]:
        st.markdown("##### 💡 Try asking:")
        suggestions = [
            "How do I place an order?",
            "What does the AI Merchant Match feature do?",
            "How do demand forecasts work?",
            "How do I set up my preferences?",
            "What units can I use for products?",
            "How do I contact a producer?",
        ]
        cols = st.columns(3)
        for i, s in enumerate(suggestions):
            with cols[i % 3]:
                if st.button(s, key=f"sugg_{i}", use_container_width=True):
                    st.session_state["assistant_chat"].append({"role": "user", "content": s})
                    _process_and_respond()
                    st.rerun()

    # --- Input form ---
    st.markdown("---")
    with st.form("assistant_chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_area(
                "Your question",
                placeholder="Ask me about the platform...",
                height=80,
                label_visibility="collapsed",
                key="assistant_input",
            )
        with col2:
            submitted = st.form_submit_button("Send 📤", type="primary", use_container_width=True)

        if submitted and user_input.strip():
            st.session_state["assistant_chat"].append({"role": "user", "content": user_input.strip()})
            _process_and_respond()
            st.rerun()

    # --- Clear chat button ---
    if st.session_state["assistant_chat"]:
        if st.button("🗑️ Clear chat history"):
            st.session_state["assistant_chat"] = []
            st.rerun()


def _process_and_respond():
    """Send the last user message to Groq and store the response."""
    last_msg = st.session_state["assistant_chat"][-1]["content"]
    with st.spinner("🤖 Thinking..."):
        response = chat_with_assistant(last_msg, st.session_state["assistant_chat"])
    st.session_state["assistant_chat"].append({"role": "assistant", "content": response})


def _render_user_bubble(text: str):
    """Render a user message bubble (right-aligned, green)."""
    st.markdown(
        f"""
        <div style='display:flex; justify-content:flex-end; margin:0.5rem 0;'>
            <div style='background:#10b981; color:white; padding:0.75rem 1rem;
                        border-radius:12px 12px 4px 12px; max-width:70%;
                        box-shadow:0 1px 3px rgba(0,0,0,0.1);'>
                {text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_assistant_bubble(text: str):
    """Render an assistant message bubble (left-aligned, white with border)."""
    # Convert markdown-style bold to HTML using regex
    import re
    formatted = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Simple paragraph handling
    formatted = formatted.replace("\n\n", "</p><p>")
    formatted = f"<p>{formatted}</p>"

    st.markdown(
        f"""
        <div style='display:flex; justify-content:flex-start; margin:0.5rem 0;'>
            <div style='background:#f8fafc; color:#0f172a; padding:0.75rem 1rem;
                        border-radius:12px 12px 12px 4px; max-width:80%;
                        border:1px solid #e2e8f0; box-shadow:0 1px 3px rgba(0,0,0,0.04);'>
                <div style='font-size:0.75rem; color:#10b981; font-weight:600;
                            margin-bottom:0.25rem;'>🤖 AI Assistant</div>
                {formatted}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
