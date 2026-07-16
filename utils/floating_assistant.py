"""
Floating AI Assistant — a chat bubble that floats in the bottom-right
corner of every page and opens into a chat panel.

How it works
------------
The button + chat panel are both rendered inside a single
``st.components.v1.html()`` component. Because the component lives
in its own iframe-like wrapper outside Streamlit's flex layout,
the ``position: fixed`` CSS works correctly — the button always
stays glued to the bottom-right corner of the viewport regardless
of page scroll or surrounding content.

The component is fully self-contained:
  * It tracks its own open/closed state in localStorage
  * The button has hover effects, a pulsing ring, and an animated
    gradient background
  * The panel slides up smoothly when opened
  * The chat UI is rendered with vanilla HTML/CSS so we have full
    control over styling
  * When the user sends a message, the JS posts it to Streamlit
    via the standard component value mechanism
  * Python reads the message, calls the AI, and pushes the response
    back to the component on the next render

This is a two-way binding: the JS component requests an AI response,
Streamlit provides it, and the component renders it.

Why not just use a regular Streamlit button with CSS?

  Streamlit wraps every widget in flex containers. Even with
  ``position: fixed``, those flex containers can apply transforms or
  have overflow constraints that make the button move with the page.
  Using ``st.components.v1.html()`` puts the button in its own
  container that lives outside Streamlit's flex layout, so
  ``position: fixed`` works correctly.
"""
from __future__ import annotations

import json
import streamlit as st
import streamlit.components.v1 as components

from auth.session import get_current_user
from ai.assistant import chat_with_assistant, is_assistant_available


# The HTML/CSS/JS for the floating button + chat panel. It is a
# self-contained widget that:
#   1. Always shows the floating button in the bottom-right corner
#   2. Opens a chat panel when the button is clicked
#   3. Tracks its own open/closed state
#   4. When the user sends a message, posts it to Streamlit
#   5. When Streamlit responds with an AI message, renders it
_FAB_AND_PANEL_HTML = """
<style>
  /* ─── Floating button (always visible) ─────────────────────── */
  .fab-root {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 999999;
    width: 64px; height: 64px;
    pointer-events: none;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  .fab-pulse {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 64px; height: 64px;
    border-radius: 50%;
    background: rgba(16, 185, 129, 0.5);
    animation: fabPulse 2s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
  }
  @keyframes fabPulse {
    0%   { width: 64px;  height: 64px;  opacity: 0.6; }
    100% { width: 100px; height: 100px; opacity: 0;   }
  }
  .fab-button {
    position: absolute;
    top: 0; left: 0;
    width: 64px; height: 64px;
    border-radius: 50%;
    border: 3px solid rgba(255, 255, 255, 0.9);
    background: linear-gradient(135deg, #10b981 0%, #34d399 50%, #6ee7b7 100%);
    background-size: 200% 200%;
    animation: fabGradShift 4s ease infinite;
    color: white;
    font-size: 1.7rem;
    cursor: pointer;
    pointer-events: auto;
    box-shadow: 0 8px 24px rgba(16, 185, 129, 0.45);
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.25s ease;
    display: flex; align-items: center; justify-content: center;
    z-index: 1;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
  }
  .fab-button:hover {
    transform: scale(1.1) translateY(-2px);
    box-shadow: 0 12px 32px rgba(16, 185, 129, 0.6),
                0 0 0 8px rgba(16, 185, 129, 0.2);
  }
  .fab-button:active { transform: scale(0.95); }
  .fab-button.is-open {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 50%, #b91c1c 100%);
    animation: none;
  }
  @keyframes fabGradShift {
    0%   { background-position: 0% 50%;   }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%;   }
  }

  /* ─── Chat panel (slides up when open) ────────────────────── */
  .fab-panel {
    position: fixed;
    bottom: 100px;
    right: 24px;
    z-index: 999998;
    width: 380px;
    max-width: calc(100vw - 48px);
    height: 520px;
    max-height: calc(100vh - 140px);
    background: #ffffff;
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 16px;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18),
                0 0 0 1px rgba(16, 185, 129, 0.1);
    overflow: hidden;
    display: none;
    flex-direction: column;
    pointer-events: auto;
    animation: fabSlideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  .fab-panel.is-open { display: flex; }
  @keyframes fabSlideUp {
    from { opacity: 0; transform: translateY(20px) scale(0.95); }
    to   { opacity: 1; transform: translateY(0)    scale(1);    }
  }
  @media (prefers-color-scheme: dark) {
    .fab-panel { background: #1e293b; color: #e2e8f0; }
  }

  /* Header */
  .fab-header {
    background: linear-gradient(135deg, #0f3d23 0%, #1a5c2e 50%, #10b981 100%);
    background-size: 200% 200%;
    animation: fabGradShift 6s ease infinite;
    color: white;
    padding: 14px 16px;
    display: flex; align-items: center; gap: 10px;
    flex-shrink: 0;
  }
  .fab-header-icon { font-size: 1.6rem; line-height: 1; }
  .fab-header-text { flex: 1; min-width: 0; }
  .fab-header-text h4 {
    margin: 0; font-size: 0.95rem; font-weight: 700;
    color: white; line-height: 1.1;
  }
  .fab-header-text p {
    margin: 2px 0 0; font-size: 0.7rem;
    color: #d1fae5; opacity: 0.95;
  }
  .fab-header-status {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.65rem; color: #d1fae5; font-weight: 600;
  }
  .fab-status-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #34d399;
    box-shadow: 0 0 6px #34d399;
    animation: fabPulseSoft 1.5s ease-in-out infinite;
  }
  @keyframes fabPulseSoft {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.4; }
  }

  /* Body — messages */
  .fab-body {
    flex: 1; overflow-y: auto;
    padding: 12px 14px;
    background: rgba(248, 250, 252, 0.6);
    display: flex; flex-direction: column; gap: 8px;
  }
  @media (prefers-color-scheme: dark) {
    .fab-body { background: rgba(15, 23, 42, 0.6); }
  }
  .fab-msg {
    max-width: 85%;
    padding: 8px 12px;
    border-radius: 14px;
    font-size: 0.82rem;
    line-height: 1.4;
    word-wrap: break-word;
    animation: fabMsgIn 0.25s ease-out;
  }
  @keyframes fabMsgIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0);   }
  }
  .fab-msg.user {
    align-self: flex-end;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    border-bottom-right-radius: 4px;
  }
  .fab-msg.assistant {
    align-self: flex-start;
    background: white;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-bottom-left-radius: 4px;
  }
  @media (prefers-color-scheme: dark) {
    .fab-msg.assistant { background: #334155; color: #e2e8f0; border-color: #475569; }
  }
  .fab-msg.assistant.loading {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.3);
    color: #047857;
  }
  .fab-msg.assistant.loading::after {
    content: '● ● ●';
    animation: fabDotPulse 1.2s ease-in-out infinite;
    letter-spacing: 4px;
    font-size: 0.7rem;
  }
  @keyframes fabDotPulse {
    0%, 100% { opacity: 0.3; }
    50%      { opacity: 1; }
  }

  /* Empty state */
  .fab-empty {
    text-align: center; padding: 24px 12px; color: #94a3b8;
  }
  .fab-empty-icon { font-size: 2.4rem; margin-bottom: 6px; }
  .fab-empty-title {
    font-size: 0.85rem; font-weight: 600; color: #475569;
    margin-bottom: 4px;
  }
  @media (prefers-color-scheme: dark) {
    .fab-empty-title { color: #cbd5e1; }
  }
  .fab-empty-body { font-size: 0.75rem; line-height: 1.4; }

  /* Suggestion buttons */
  .fab-suggestions {
    display: flex; flex-direction: column; gap: 6px;
    margin-top: 14px; padding: 0 6px;
  }
  .fab-suggestion {
    background: white;
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #047857;
    padding: 8px 12px;
    border-radius: 10px;
    font-size: 0.78rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
    font-family: inherit;
  }
  .fab-suggestion:hover {
    background: #ecfdf5;
    border-color: #10b981;
    transform: translateY(-1px);
  }
  @media (prefers-color-scheme: dark) {
    .fab-suggestion { background: #334155; color: #6ee7b7; border-color: rgba(16, 185, 129, 0.4); }
    .fab-suggestion:hover { background: rgba(16, 185, 129, 0.2); }
  }

  /* Footer — input */
  .fab-footer {
    padding: 10px 12px;
    background: white;
    border-top: 1px solid rgba(16, 185, 129, 0.15);
    flex-shrink: 0;
  }
  @media (prefers-color-scheme: dark) {
    .fab-footer { background: #0f172a; border-top-color: rgba(16, 185, 129, 0.25); }
  }
  .fab-input-row {
    display: flex; gap: 6px; align-items: center;
  }
  .fab-input {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 10px;
    font-size: 0.82rem;
    outline: none;
    background: white;
    color: #0f172a;
    transition: border-color 0.2s ease;
    font-family: inherit;
  }
  .fab-input:focus { border-color: #10b981; }
  @media (prefers-color-scheme: dark) {
    .fab-input { background: #1e293b; color: #e2e8f0; border-color: rgba(16, 185, 129, 0.4); }
  }
  .fab-send {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    border: none;
    border-radius: 10px;
    width: 36px; height: 36px;
    cursor: pointer;
    font-size: 1rem;
    display: flex; align-items: center; justify-content: center;
    transition: transform 0.2s ease;
  }
  .fab-send:hover { transform: scale(1.05); }
  .fab-send:active { transform: scale(0.95); }
  .fab-send:disabled { opacity: 0.5; cursor: not-allowed; }
  .fab-actions {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 6px;
  }
  .fab-link {
    color: #64748b; background: none; border: none;
    cursor: pointer; padding: 2px 4px;
    font-size: 0.7rem; font-family: inherit;
  }
  .fab-link:hover { color: #10b981; }
  .fab-powered { color: #cbd5e1; font-size: 0.7rem; }

  /* Hide on small mobile */
  @media (max-width: 480px) {
    .fab-panel {
      right: 12px !important;
      left: 12px !important;
      width: auto !important;
      bottom: 90px !important;
    }
  }
</style>

<div class="fab-root" id="fab-root">
  <div class="fab-pulse"></div>
  <div class="fab-button" id="fab-button" title="Toggle AI Assistant">💬</div>
</div>

<div class="fab-panel" id="fab-panel">
  <div class="fab-header">
    <div class="fab-header-icon">🤖</div>
    <div class="fab-header-text">
      <h4>AI Assistant</h4>
      <p>Ask me anything about the platform</p>
    </div>
    <div class="fab-header-status">
      <span class="fab-status-dot"></span>
      <span>Online</span>
    </div>
  </div>
  <div class="fab-body" id="fab-body"></div>
  <div class="fab-footer">
    <div class="fab-input-row">
      <input type="text" class="fab-input" id="fab-input"
             placeholder="Ask me anything..." maxlength="500" />
      <button class="fab-send" id="fab-send" title="Send">➤</button>
    </div>
    <div class="fab-actions">
      <button class="fab-link" id="fab-clear">🗑️ Clear</button>
      <span class="fab-powered">Powered by Groq</span>
    </div>
  </div>
</div>

<script>
(function() {
  const STORAGE_KEY = 'fab_chat_state';
  const STORAGE_HIST_KEY = 'fab_chat_history';
  const STORAGE_PENDING_KEY = 'fab_chat_pending';
  const btn    = document.getElementById('fab-button');
  const panel  = document.getElementById('fab-panel');
  const body   = document.getElementById('fab-body');
  const input  = document.getElementById('fab-input');
  const send   = document.getElementById('fab-send');
  const clearB = document.getElementById('fab-clear');

  // --- Persistent state ---
  // open:        is the panel visible?
  // hist:        chat history
  // pendingMsg:  a message waiting to be sent to Python (set when the
  //              user sends a message but the Streamlit rerun hasn't
  //              happened yet)
  // pendingId:   unique id of the pending message (so we can replace
  //              the loading bubble with the real response)
  function loadBool(key, def) {
    try { const v = localStorage.getItem(key); return v === null ? def : v === '1'; }
    catch (e) { return def; }
  }
  function saveBool(key, val) {
    try { localStorage.setItem(key, val ? '1' : '0'); } catch (e) {}
  }
  function loadJSON(key, def) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : def; }
    catch (e) { return def; }
  }
  function saveJSON(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) {}
  }

  let isOpen = loadBool(STORAGE_KEY, false);
  let history = loadJSON(STORAGE_HIST_KEY, []);
  let pendingId = null;  // id of the currently-loading message

  function render() {
    btn.textContent = isOpen ? '✕' : '💬';
    btn.classList.toggle('is-open', isOpen);
    panel.classList.toggle('is-open', isOpen);

    body.innerHTML = '';
    if (history.length === 0) {
      body.innerHTML = `
        <div class="fab-empty">
          <div class="fab-empty-icon">👋</div>
          <div class="fab-empty-title">Hi there!</div>
          <div class="fab-empty-body">
            I'm your AI Supply Chain assistant.<br/>
            Ask me about orders, products, AI features, or anything else.
          </div>
          <div class="fab-suggestions">
            <button class="fab-suggestion" data-q="How do I place an order?">
              🛒 How do I place an order?
            </button>
            <button class="fab-suggestion" data-q="What does AI Merchant Match do?">
              🤝 What does AI Match do?
            </button>
            <button class="fab-suggestion" data-q="How accurate are the AI demand forecasts?">
              📈 How accurate are forecasts?
            </button>
          </div>
        </div>
      `;
      body.querySelectorAll('.fab-suggestion').forEach(b => {
        b.addEventListener('click', function() {
          sendMessage(b.getAttribute('data-q'));
        });
      });
    } else {
      history.forEach(m => {
        const div = document.createElement('div');
        div.className = 'fab-msg ' + m.role + (m.loading ? ' loading' : '');
        div.dataset.id = m.id || '';
        div.textContent = m.content || '';
        body.appendChild(div);
      });
      body.scrollTop = body.scrollHeight;
    }
  }

  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function sendMessage(text) {
    if (!text || !text.trim()) return;
    text = text.trim();

    // Add user message
    history.push({ id: uid(), role: 'user', content: text });
    // Add a loading assistant message
    const id = uid();
    pendingId = id;
    history.push({ id: id, role: 'assistant', content: '', loading: true });
    saveJSON(STORAGE_HIST_KEY, history);
    render();

    input.disabled = true;
    send.disabled = true;

    // Tell Streamlit about the new message via the component value
    // mechanism. The Streamlit side reads this on the next rerun.
    if (window.parent && window.parent.Streamlit) {
      try {
        window.parent.Streamlit.setComponentValue({
          type: 'send',
          message: text,
          msgId: id,
          ts: Date.now()
        });
      } catch (e) {
        // Fallback: postMessage
        window.parent.postMessage({
          type: 'streamlit:setComponentValue',
          value: { type: 'send', message: text, msgId: id, ts: Date.now() }
        }, '*');
      }
    } else {
      // No Streamlit parent (shouldn't happen in production) —
      // simulate a response after a moment.
      setTimeout(function() {
        receiveResponse(id, '⚠️ AI Assistant is not available in this context.');
      }, 1000);
    }
  }

  function receiveResponse(msgId, content) {
    const idx = history.findIndex(m => m.id === msgId);
    if (idx >= 0) {
      history[idx] = { id: msgId, role: 'assistant', content: content };
    } else {
      history.push({ id: msgId, role: 'assistant', content: content });
    }
    pendingId = null;
    saveJSON(STORAGE_HIST_KEY, history);
    render();
    input.disabled = false;
    send.disabled = false;
    input.focus();
  }

  // Listen for responses posted from Streamlit
  window.addEventListener('message', function(event) {
    const data = event.data || {};
    if (data.type === 'streamlit:setFrameHeight' || data.type === 'streamlit:rerun') return;
    let v = data.value || data;
    if (v && v.type === 'response' && typeof v.content === 'string' && v.msgId) {
      receiveResponse(v.msgId, v.content);
    }
  });

  // --- Event wiring ---
  btn.addEventListener('click', function() {
    isOpen = !isOpen;
    saveBool(STORAGE_KEY, isOpen);
    render();
    if (isOpen) {
      setTimeout(function() { input.focus(); }, 100);
    }
  });
  send.addEventListener('click', function() {
    sendMessage(input.value);
    input.value = '';
  });
  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input.value);
      input.value = '';
    }
  });
  clearB.addEventListener('click', function() {
    if (history.length === 0) return;
    if (confirm('Clear chat history?')) {
      history = [];
      pendingId = null;
      saveJSON(STORAGE_HIST_KEY, history);
      render();
    }
  });

  render();
})();
</script>
"""


def render_floating_assistant() -> None:
    """Render the floating AI Assistant button + chat panel.

    The button + panel are both rendered inside a single
    ``st.components.v1.html()`` component. This puts them outside
    Streamlit's flex layout, so ``position: fixed`` works correctly
    and the button always stays in the bottom-right corner of the
    viewport regardless of page scroll.

    Two-way communication:
      * JS → Python: when the user sends a message, the JS calls
        ``Streamlit.setComponentValue({type: 'send', ...})`` which
        Python reads as the return value of ``components.html()``.
      * Python → JS: after generating the AI response, Python renders
        a tiny follow-up component that posts a ``{type: 'response',
        msgId, content}`` message back to the original component.
    """
    user = get_current_user()
    if not user:
        return  # Don't show the floating assistant on auth pages

    # Render the floating button + chat panel. The component's
    # return value is the dict that the JS most recently set via
    # ``Streamlit.setComponentValue``.
    component_value = components.html(
        _FAB_AND_PANEL_HTML,
        height=0,
        scrolling=False,
    )

    if not component_value or not isinstance(component_value, dict):
        return

    event_type = component_value.get("type")

    if event_type != "send":
        return

    message = (component_value.get("message") or "").strip()
    msg_id = component_value.get("msgId")
    if not message or not msg_id:
        return

    # Generate the AI response
    if is_assistant_available():
        try:
            # We don't show a spinner in the Streamlit UI because the
            # JS component already shows a "loading" dot animation
            # while waiting. The user sees a fast, native experience.
            # We do still wrap in spinner for accessibility / clarity.
            with st.spinner("🤖 Thinking..."):
                # Use a fresh history here — the JS keeps the
                # full history in localStorage, so we just pass
                # the user's message to the AI as a single turn.
                response = chat_with_assistant(message, [{"role": "user", "content": message}])
        except Exception as e:
            response = f"❌ Sorry, I ran into an error: {e}"
    else:
        response = (
            "⚠️ **AI Assistant is not configured.**\n\n"
            "Add `GROQ_API_KEY` to your Streamlit secrets to enable the assistant. "
            "Get a free key at [console.groq.com/keys](https://console.groq.com/keys)."
        )

    # Push the response back to the floating component via a
    # follow-up postMessage. We render a tiny invisible component
    # whose only job is to fire the postMessage event.
    safe_content = json.dumps(response)
    components.html(
        f"""
        <script>
          (function() {{
            try {{
              window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: {{
                  type: 'response',
                  msgId: {json.dumps(msg_id)},
                  content: {safe_content}
                }}
              }}, '*');
            }} catch (e) {{ console.error('FAB response post failed:', e); }}
          }})();
        </script>
        """,
        height=0,
        scrolling=False,
    )
