"""
AI Assistant powered by Groq API.

A chat assistant that ONLY answers questions about this AI Supply Chain Platform.
It does NOT answer general knowledge questions — only platform-related queries.

System prompt is strictly scoped to:
  • Platform features (marketplace, products, orders, agreements)
  • User roles (producer, merchant, customer, admin)
  • AI features (demand forecast, price prediction, recommendations, matchmaking)
  • Notifications, messaging, preferences
  • Account management (login, signup, password reset)
  • Ethiopian supply chain context

Self-learning (v6): the system prompt is augmented with LIVE platform stats
(orders, products, demand accuracy %, price accuracy %) fetched from the
MLEngine summary, so the assistant can answer questions like "how accurate
are the demand forecasts?" with real numbers.

Admin-only context: the live context block is only injected for users
whose role is "admin". Producers, merchants, and customers get the base
system prompt without the internal ML metrics — those are operational
diagnostics, not user-facing features.
"""
from __future__ import annotations

import os
from typing import List, Dict, Optional
import streamlit as st


SYSTEM_PROMPT_BASE = """You are the AI Assistant for the AI Supply Chain Platform — a Streamlit-based supply chain management system built with Supabase, designed for the Ethiopian agricultural supply chain.

YOUR JOB: Help users understand and use this platform. You ONLY answer questions about this platform.

PLATFORM FEATURES YOU KNOW ABOUT:
1. **Authentication**: Login, Signup (with 4 roles: producer, merchant, customer, admin), Forgot Password, Reset Password — all powered by Supabase Auth.

2. **Marketplace** (🛒): All roles can browse all active products. Each product card shows image, price (in Ethiopian Birr / Br), quality grade, brand, stock, and "Saved by N users" count. Users can Save (favorite), Order (opens product detail), or Contact Producer.

3. **Product Detail Page**: Full product info, producer business card (avatar, contact, verified status, member since), order form with Ethiopian shipping fields, agreement preview, and "Confirm Agreement & Place Order" button. Creates order + agreement + notifies producer.

4. **AI Insights** (🤖): Three sub-tabs available to all roles:
   - Demand Forecast: Gradient Boosting (or linear regression fallback) per product, predicts next 30-day demand, with a chart of actuals vs fitted vs forecast
   - Price Prediction: Random Forest (or linear regression fallback) suggests optimal prices (increase/decrease/hold), with a per-product accuracy chart
   - Recommendations: Collaborative filtering suggests products to buy/stock
   - Per-product accuracy is shown for the user's own products; the platform-wide internal stats (training counts, self-learning loop) are visible only to admins on the admin dashboard.

5. **AI Merchant Match** (🤝, producers only): AI finds best merchant matches based on category overlap, quality grades, brands, price range, payment terms, location, and order history. Shows match percentage. Producer can send agreement requests; merchant can confirm or cancel.

6. **Notifications** (🔔): System + admin broadcasts. Direct messaging between users. Admin can broadcast to all users.

7. **Profile**: Avatar upload, personal info, and Preferences form (preferred categories, product names, quality grades, brands, models, classes, levels, payment terms, dietary restrictions, notifications).

8. **Producer Inventory**: Add products with image, SKU, name, category, price (Br), stock, unit (Ethiopian + international: quintal, sack, bag, kg, litre, dozen, etc.), quality grade, brand, model, origin, certifications, production/expiry dates.

9. **Admin**: Dashboard with platform stats, User Management (activate/deactivate), Fraud Detection Center (review AI fraud alerts).

CURRENCY: All prices are in Ethiopian Birr (Br / ETB). VAT is 15%.

UNITS: Ethiopian standards (quintal = 100kg, sack 50/100kg, bag 60kg for coffee) plus international (kg, g, ton, litre, ml, gallon, dozen, etc.).

STRICT RULES:
- ONLY answer questions about THIS platform's features, how to use them, and what they do.
- If asked about something unrelated (general knowledge, coding, other apps, news, etc.), politely say: "I can only answer questions about the AI Supply Chain Platform. Ask me about the marketplace, orders, AI features, or any other platform feature!"
- Be concise and helpful. Use bullet points when listing features.
- You do NOT have access to user-specific data — don't pretend to look up individual orders or accounts.
- You CAN quote aggregate platform stats when they are provided in the live-context block below.
- If a user reports a bug or error, suggest they check: (1) Supabase credentials in secrets, (2) run the migration SQL files (schema.sql through migration_v6.sql), (3) contact admin.
"""


def _build_live_context_block() -> str:
    """Pull live platform stats from the MLEngine summary and format them
    as a context block appended to the system prompt. If ML libraries or
    DB aren't available, returns an empty string.

    Only included for users whose role is "admin". Producers, merchants,
    and customers do not get the internal ML metrics — those are
    operational diagnostics, not user-facing features.
    """
    # Role gate: live context is admin-only
    try:
        user = st.session_state.get("user") or {}
        if user.get("role") != "admin":
            return ""
    except Exception:
        return ""

    try:
        from ai.engine import get_training_summary
        summary = get_training_summary()
    except Exception:
        return ""

    if not summary.get("ml_available"):
        return ""

    def fmt_pct(v):
        return f"{v:.1f}%" if isinstance(v, (int, float)) else "not enough data yet"

    lines = [
        "\n\n--- LIVE PLATFORM CONTEXT (admin-only, refreshed every 5 min) ---",
        f"Orders placed on platform: {summary.get('orders_count', 0)}",
        f"Order line items: {summary.get('order_items_count', 0)}",
        f"Active products: {summary.get('products_count', 0)}",
        f"Registered users: {summary.get('users_count', 0)}",
        f"Demand models trained: {summary.get('demand_models_trained', 0)}",
        f"Price model trained: {'yes' if summary.get('price_model_trained') else 'no'}",
        f"Recommender trained: {'yes' if summary.get('recommender_trained') else 'no'}",
        f"Total predictions logged: {summary.get('total_predictions_logged', 0)}",
        f"Predictions scored against actuals: {summary.get('scored_predictions', 0)}",
        f"Demand forecast accuracy: {fmt_pct(summary.get('demand_accuracy_pct'))}",
        f"Price prediction accuracy: {fmt_pct(summary.get('price_accuracy_pct'))}",
        f"Model version: {summary.get('model_version', 'unknown')}",
        "When an admin asks about AI accuracy, quote these numbers. They reflect real platform data, not guesses.",
    ]
    return "\n".join(lines)


def _get_system_prompt() -> str:
    """Return the base system prompt + the live context block."""
    return SYSTEM_PROMPT_BASE + _build_live_context_block()


def _get_groq_api_key() -> Optional[str]:
    """Get Groq API key from environment or Streamlit secrets."""
    # Try env first
    key = os.environ.get("GROQ_API_KEY")
    if key and not key.startswith("your-"):
        return key
    # Try Streamlit secrets
    try:
        key = st.secrets.get("GROQ_API_KEY")
        if key and not str(key).startswith("your-"):
            return str(key)
    except Exception:
        pass
    # Try aliases
    for alias in ("GROQ_KEY", "GROQ_TOKEN"):
        key = os.environ.get(alias)
        if key and not key.startswith("your-"):
            return key
        try:
            key = st.secrets.get(alias)
            if key and not str(key).startswith("your-"):
                return str(key)
        except Exception:
            pass
    return None


def is_assistant_available() -> bool:
    """Check if the Groq API key is configured."""
    return _get_groq_api_key() is not None


def chat_with_assistant(user_message: str, chat_history: List[Dict[str, str]]) -> str:
    """Send a message to the Groq-powered assistant and get a response.

    Args:
        user_message: The user's question
        chat_history: List of {"role": "user"|"assistant", "content": "..."} dicts

    Returns:
        The assistant's response text.
    """
    api_key = _get_groq_api_key()
    if not api_key:
        return (
            "⚠️ The AI Assistant is not configured. Please set the `GROQ_API_KEY` "
            "in your Streamlit secrets or .env file. Get a free API key at "
            "https://console.groq.com/keys"
        )

    # Validate the key format (Groq keys start with 'gsk_')
    if not api_key.startswith("gsk_"):
        return (
            "⚠️ Your GROQ_API_KEY doesn't look right — Groq API keys start with `gsk_`.\n\n"
            "It looks like you may have put a Supabase key (which starts with `eyJ`) in the "
            "GROQ_API_KEY slot. Get a valid Groq key at https://console.groq.com/keys"
        )

    try:
        from groq import Groq
    except ImportError:
        # Fallback: use requests to call Groq API directly (no package needed)
        return _chat_with_groq_via_requests(api_key, user_message, chat_history)

    # Build messages: system prompt + chat history + new message
    system_prompt = _get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-10:]:  # keep last 10 messages for context
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    # Try these models in order — fall back to smaller/faster ones on rate limit
    models_to_try = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]

    import time
    last_error = None

    for model_name in models_to_try:
        try:
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            return response.choices[0].message.content or "I couldn't generate a response. Please try again."
        except Exception as e:
            last_error = e
            err = str(e).lower()
            # On rate limit, wait briefly and try the next (smaller) model
            if "rate limit" in err or "429" in err or "rate_limit" in err:
                time.sleep(1.5)
                continue
            # On invalid key, don't retry — just return the error
            if "invalid api key" in err or "401" in err:
                return (
                    "⚠️ Invalid Groq API key. Please check your GROQ_API_KEY in "
                    "Streamlit secrets. Get a valid key at https://console.groq.com/keys"
                )
            # On other errors, try the next model
            continue

    # All models failed
    err = str(last_error) if last_error else "unknown error"
    err_lower = err.lower()
    if "rate limit" in err_lower or "429" in err_lower:
        return (
            "⏳ Groq rate limit reached on all models. The free tier has limits:\n\n"
            "- **Requests per minute**: ~30\n"
            "- **Tokens per minute**: ~6000\n\n"
            "**Options:**\n"
            "1. Wait 1-2 minutes and try again\n"
            "2. Upgrade to Groq's paid tier at console.groq.com/billing\n"
            "3. Use a different LLM provider (OpenAI, Anthropic)\n\n"
            "The rate limit resets automatically — your message was NOT lost."
        )
    return f"⚠️ Assistant error: {err}"


def _chat_with_groq_via_requests(api_key: str, user_message: str, chat_history: list) -> str:
    """Call Groq API using requests (no groq package needed)."""
    import requests

    system_prompt = _get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    import time

    for model_name in models_to_try:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                },
                timeout=30,
            )
            if r.status_code == 429:
                time.sleep(1.5)
                continue
            if r.status_code >= 400:
                err = r.text
                if "invalid api key" in err.lower() or r.status_code == 401:
                    return "⚠️ Invalid Groq API key. Check your GROQ_API_KEY in secrets."
                continue
            data = r.json()
            return data["choices"][0]["message"]["content"] or "I couldn't generate a response."
        except Exception:
            continue

    return "⏳ Groq rate limit reached. Wait a moment and try again."
