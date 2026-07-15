"""
AI Assistant chat page — powered by Groq API.

Pure native Streamlit: st.chat_message + st.chat_input. No HTML, no
unsafe_allow_html, no custom CSS bubble divs. The bubbles render with
Streamlit's built-in chat styling (which is consistent, accessible,
and supports markdown out of the box).
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
            "```\n\n"
            "The Groq API is free and fast — perfect for this assistant."
        )
        return

    # --- Intro ---
    st.info(
        "👋 Hi! I'm your AI Supply Chain Platform assistant. I can help you with:\n"
        "- 🛒 How to use the marketplace\n"
        "- 📦 How to add products and manage inventory\n"
        "- 🤖 How AI predictions and recommendations work (and how accurate they are)\n"
        "- 🤝 How merchant matching works\n"
        "- 🔔 Notifications and messaging\n"
        "- ⚙️ Setting up your preferences\n"
        "- 💰 Orders, agreements, and payments\n\n"
        "**I only answer questions about this platform.** Ask me anything!"
    )

    # --- Chat history in session_state ---
    if "assistant_chat" not in st.session_state:
        st.session_state["assistant_chat"] = []

    # --- Display chat history using native st.chat_message ---
    for msg in st.session_state["assistant_chat"]:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else None):
            st.markdown(msg["content"])

    # --- Quick suggestion buttons (only before first message) ---
    if not st.session_state["assistant_chat"]:
        st.markdown("##### 💡 Try asking:")
        suggestions = [
            "How do I place an order?",
            "What does the AI Merchant Match feature do?",
            "How accurate are the AI demand forecasts?",
            "How does the AI learn over time?",
            "How do I set up my preferences?",
            "What units can I use for products?",
        ]
        cols = st.columns(3)
        for i, s in enumerate(suggestions):
            with cols[i % 3]:
                if st.button(s, key=f"sugg_{i}", use_container_width=True):
                    st.session_state["assistant_chat"].append({"role": "user", "content": s})
                    _process_and_respond()
                    st.rerun()

    # --- Native chat input (replaces the old st.form + st.text_area) ---
    user_input = st.chat_input("Ask me about the platform...")
    if user_input and user_input.strip():
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
