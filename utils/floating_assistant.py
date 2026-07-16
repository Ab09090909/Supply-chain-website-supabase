"""
Floating AI Assistant — a chat bubble that sits in the bottom-right
corner of every page and opens into a chat panel.

How it works
------------
1. A small floating button (CSS-positioned) sits in the bottom-right
   corner of the viewport. The button has a pulsing "online" ring
   so it feels alive.

2. The button is a real Streamlit widget (a ``st.button``) that we
   locate with a `.fab-marker` div sibling. The CSS uses
   ``[data-testid="stVerticalBlock"]:has(> .fab-marker)`` to find
   the Streamlit container that holds our button, and turns that
   container into the floating wrapper (``position: fixed``).

3. When the chat is open, we render a second ``st.container()`` that
   contains a `.fab-panel-marker` div, a gradient header (raw HTML),
   and the actual chat widgets (``st.chat_message``,
   ``st.chat_input``, ``st.button``). The CSS uses the marker trick
   again to make this whole container float in the bottom-right
   corner above the button.

4. All AI calls go through ``ai.assistant.chat_with_assistant()`` so
   the floating assistant uses the same backend as the full-page one.

5. If the Groq API key isn't configured, the panel shows a friendly
   warning with setup instructions.

Usage
-----
    from utils.floating_assistant import render_floating_assistant
    render_floating_assistant()  # call once, near the bottom of the page
"""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from utils.ui import _html
from ai.assistant import chat_with_assistant, is_assistant_available


# The CSS that positions the floating button + chat panel.
#
# Streamlit's DOM looks roughly like this for every widget:
#
#   <div data-testid="stVerticalBlock">       <-- Streamlit container
#     <div class="my-marker">...</div>         <-- our marker (hidden)
#     <div data-testid="stButton">             <-- the actual widget
#       <button>...</button>
#     </div>
#   </div>
#
# We use the modern CSS :has() selector to detect any container
# that holds a marker, and turn that container into a fixed-position
# floating wrapper. The marker itself is hidden so the user doesn't
# see it.
_FLOATING_CSS = """
<style>
/* ── Floating button container ──────────────────────────────────────
   Any Streamlit vertical block that contains a `.fab-marker` child
   becomes a fixed-position wrapper in the bottom-right corner. */
[data-testid="stVerticalBlock"]:has(> .fab-marker) {
    padding: 0 !important;
    margin: 0 !important;
    height: 64px !important;
    width: 64px !important;
    overflow: visible !important;
    position: fixed !important;
    bottom: 24px !important;
    right: 24px !important;
    z-index: 999999 !important;
    pointer-events: none !important;
}

/* The marker itself is just used to locate the parent — hide it. */
.fab-marker {
    display: none !important;
}

/* Streamlit wraps the button in [data-testid="stButton"] — pull that
   back to the visible position and make it clickable. */
[data-testid="stVerticalBlock"]:has(> .fab-marker) [data-testid="stButton"] {
    pointer-events: auto !important;
    position: relative !important;
    width: 64px !important;
    height: 64px !important;
    margin: 0 !important;
}

/* Style the actual <button> element */
[data-testid="stVerticalBlock"]:has(> .fab-marker) button {
    width: 64px !important;
    height: 64px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    font-size: 1.7rem !important;
    background: linear-gradient(135deg, #10b981 0%, #34d399 50%, #6ee7b7 100%) !important;
    background-size: 200% 200% !important;
    animation: gradientShift 4s ease infinite !important;
    border: 3px solid rgba(255, 255, 255, 0.9) !important;
    box-shadow: 0 8px 24px rgba(16, 185, 129, 0.45),
                0 0 0 0 rgba(16, 185, 129, 0.4) !important;
    color: white !important;
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.25s ease !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stVerticalBlock"]:has(> .fab-marker) button:hover {
    transform: scale(1.1) translateY(-2px) !important;
    box-shadow: 0 12px 32px rgba(16, 185, 129, 0.6),
                0 0 0 8px rgba(16, 185, 129, 0.2) !important;
}
[data-testid="stVerticalBlock"]:has(> .fab-marker) button:active {
    transform: scale(0.95) !important;
}

/* The pulsing ring — visible decorative element behind the button */
.fab-pulse {
    display: block !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    width: 64px !important;
    height: 64px !important;
    border-radius: 50% !important;
    background: rgba(16, 185, 129, 0.5) !important;
    animation: fab-pulse 2s ease-in-out infinite !important;
    pointer-events: none !important;
    z-index: -1 !important;
}
@keyframes fab-pulse {
    0%   { width: 64px;  height: 64px;  opacity: 0.6; }
    100% { width: 100px; height: 100px; opacity: 0;   }
}

/* ── Floating chat panel container ─────────────────────────────────
   The panel uses the same :has() trick. The container is positioned
   fixed in the bottom-right corner above the button. */
[data-testid="stVerticalBlock"]:has(> .fab-panel-marker) {
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden !important;
    position: fixed !important;
    bottom: 100px !important;
    right: 24px !important;
    z-index: 999998 !important;
    width: 380px !important;
    max-width: calc(100vw - 48px) !important;
    background: #ffffff;
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 16px;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18),
                0 0 0 1px rgba(16, 185, 129, 0.1);
    max-height: 520px;
    display: flex;
    flex-direction: column;
    pointer-events: auto !important;
    animation: fab-slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes fab-slideUp {
    from { opacity: 0; transform: translateY(20px) scale(0.95); }
    to   { opacity: 1; transform: translateY(0)    scale(1);    }
}
@media (prefers-color-scheme: dark) {
    [data-testid="stVerticalBlock"]:has(> .fab-panel-marker) {
        background: #1e293b;
        color: #e2e8f0;
        border-color: rgba(16, 185, 129, 0.4);
    }
}
.fab-panel-marker {
    display: none !important;
}

/* Header bar of the panel (rendered as raw HTML inside the container) */
.fab-panel-header {
    background: linear-gradient(135deg, #0f3d23 0%, #1a5c2e 50%, #10b981 100%);
    background-size: 200% 200%;
    animation: gradientShift 6s ease infinite;
    color: white;
    padding: 14px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
    border-radius: 16px 16px 0 0;
}
.fab-panel-header-icon {
    font-size: 1.6rem;
    line-height: 1;
}
.fab-panel-header-text { flex: 1; min-width: 0; }
.fab-panel-header-text h4 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 700;
    color: white;
    line-height: 1.1;
}
.fab-panel-header-text p {
    margin: 2px 0 0;
    font-size: 0.7rem;
    color: #d1fae5;
    opacity: 0.95;
}
.fab-panel-header-status {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.65rem;
    color: #d1fae5;
    font-weight: 600;
}
.fab-panel-header-status .fab-status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #34d399;
    box-shadow: 0 0 6px #34d399;
    animation: pulse 1.5s ease-in-out infinite;
}

/* Body of the panel — contains the chat messages (overflow scroll) */
[data-testid="stVerticalBlock"]:has(> .fab-panel-marker) [data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 8px 14px !important;
}
[data-testid="stVerticalBlock"]:has(> .fab-panel-marker) .stChatMessage {
    max-width: 100% !important;
}
/* Make sure the messages area is scrollable when there are many */
[data-testid="stVerticalBlock"]:has(> .fab-panel-marker) {
    overflow-y: auto !important;
}

/* Footer area (chat input + buttons) */
[data-testid="stVerticalBlock"]:has(> .fab-panel-marker) .stChatInput {
    margin: 0 !important;
    padding: 8px 12px !important;
    background: white;
    border-top: 1px solid rgba(16, 185, 129, 0.15);
}
@media (prefers-color-scheme: dark) {
    [data-testid="stVerticalBlock"]:has(> .fab-panel-marker) .stChatInput {
        background: #0f172a;
        border-top-color: rgba(16, 185, 129, 0.25);
    }
}

/* Hide on small mobile screens where the panel would cover the page */
@media (max-width: 480px) {
    [data-testid="stVerticalBlock"]:has(> .fab-panel-marker) {
        right: 12px !important;
        left: 12px !important;
        width: auto !important;
        bottom: 90px !important;
    }
}
</style>
"""


def _inject_floating_css() -> None:
    """Inject the floating-assistant CSS once per page."""
    _html(_FLOATING_CSS)


def render_floating_assistant() -> None:
    """Render the floating AI Assistant button + chat panel.

    Call this once per page. The button persists across reruns via
    Streamlit's session_state, so opening/closing the chat is
    instant.
    """
    user = get_current_user()
    if not user:
        return  # Don't show the floating assistant on auth pages

    # Initialise session state
    if "floating_chat_open" not in st.session_state:
        st.session_state["floating_chat_open"] = False
    if "floating_chat_history" not in st.session_state:
        st.session_state["floating_chat_history"] = []

    _inject_floating_css()

    is_open = st.session_state["floating_chat_open"]

    # ── Floating button (bottom-right corner) ────────────────────────────
    with st.container():
        # Marker — used by CSS to locate the container.
        _html('<div class="fab-marker fab-pulse"></div>')
        # The toggle button — labelled with the close icon when open,
        # chat icon when closed.
        if st.button("✕" if is_open else "💬", key="fab_toggle", help="Toggle AI Assistant"):
            st.session_state["floating_chat_open"] = not is_open
            st.rerun()

    # ── Chat panel (only when open) ──────────────────────────────────────
    if is_open:
        _render_floating_panel()


def _render_floating_panel() -> None:
    """Render the actual chat panel — header, messages, input.

    We put the entire panel inside a single ``st.container()`` so the
    CSS ``:has(.fab-panel-marker)`` selector can turn that container
    into a fixed-position floating panel.

    Inside the container:
      * a hidden marker div (for the CSS selector)
      * the header is rendered with raw HTML (gradient + status)
      * the chat messages use ``st.chat_message`` (native)
      * the input uses ``st.chat_input`` (native)
      * the close/clear buttons are real Streamlit buttons
    """
    user = get_current_user()
    if not user:
        return

    with st.container():
        # The marker that lets CSS find this container.
        _html('<div class="fab-panel-marker"></div>')
        # Header
        _html("""
        <div class="fab-panel-header">
            <div class="fab-panel-header-icon">🤖</div>
            <div class="fab-panel-header-text">
                <h4>AI Assistant</h4>
                <p>Ask me anything about the platform</p>
            </div>
            <div class="fab-panel-header-status">
                <span class="fab-status-dot"></span>
                <span>Online</span>
            </div>
        </div>
        """)

        # Availability check
        if not is_assistant_available():
            st.warning("⚠️ AI Assistant is not configured.")
            st.caption(
                "Add `GROQ_API_KEY` to your Streamlit secrets. "
                "Get a free key at [console.groq.com/keys](https://console.groq.com/keys)."
            )
            return

        history = st.session_state.get("floating_chat_history") or []

        # Welcome / empty state
        if not history:
            _html("""
            <div style='text-align:center; padding:24px 12px; color:#94a3b8;'>
                <div style='font-size:2.4rem; margin-bottom:6px;'>👋</div>
                <div style='font-size:0.85rem; font-weight:600; color:#475569; margin-bottom:4px;'>
                    Hi there!
                </div>
                <div style='font-size:0.75rem; line-height:1.4;'>
                    I'm your AI Supply Chain assistant.<br/>
                    Ask me about orders, products, AI features, or anything else.
                </div>
            </div>
            """)

            # Quick suggestion buttons
            suggestions = [
                "How do I place an order?",
                "What does AI Match do?",
                "How accurate are forecasts?",
            ]
            s_cols = st.columns(len(suggestions))
            for i, s in enumerate(suggestions):
                with s_cols[i]:
                    if st.button(s, key=f"fab_sugg_{i}", use_container_width=True):
                        _send_floating_message(s)
                        st.rerun()
        else:
            # Chat history
            for msg in history:
                avatar = "🤖" if msg["role"] == "assistant" else "👤"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

        # Chat input
        user_input = st.chat_input("Ask me anything...", key="fab_chat_input")
        if user_input and user_input.strip():
            _send_floating_message(user_input.strip())
            st.rerun()

        # Buttons row: clear + close
        if history:
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button("🗑️ Clear", key="fab_clear", use_container_width=True):
                    st.session_state["floating_chat_history"] = []
                    st.rerun()
            with bcol2:
                if st.button("✕ Close", key="fab_close", use_container_width=True):
                    st.session_state["floating_chat_open"] = False
                    st.rerun()
        else:
            # Just the close button on first open
            if st.button("✕ Close", key="fab_close", use_container_width=True):
                st.session_state["floating_chat_open"] = False
                st.rerun()


def _send_floating_message(text: str) -> None:
    """Append the user's message, call the assistant, and store the reply.

    The assistant is called synchronously here so the spinner shows up
    on the next render. We use ``st.spinner`` via the caller (it's the
    responsibility of whoever renders the chat input).
    """
    history = st.session_state.get("floating_chat_history") or []
    history.append({"role": "user", "content": text})
    with st.spinner("🤖 Thinking..."):
        try:
            response = chat_with_assistant(text, history)
        except Exception as e:
            response = f"❌ Sorry, I ran into an error: {e}"
    history.append({"role": "assistant", "content": response})
    st.session_state["floating_chat_history"] = history
