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
"""
from __future__ import annotations

import os
from typing import List, Dict, Optional
import streamlit as st


SYSTEM_PROMPT = """You are the AI Assistant for the AI Supply Chain Platform — a Streamlit-based supply chain management system built with Supabase, designed for the Ethiopian agricultural supply chain.

YOUR JOB: Help users understand and use this platform. You ONLY answer questions about this platform.

PLATFORM FEATURES YOU KNOW ABOUT:
1. **Authentication**: Login, Signup (with 4 roles: producer, merchant, customer, admin), Forgot Password, Reset Password — all powered by Supabase Auth.

2. **Marketplace** (🛒): All roles can browse all active products. Each product card shows image, price (in Ethiopian Birr / Br), quality grade, brand, stock, and "Saved by N users" count. Users can Save (favorite), Order (opens product detail), or Contact Producer.

3. **Product Detail Page**: Full product info, producer business card (avatar, contact, verified status, member since), order form with Ethiopian shipping fields, agreement preview, and "Confirm Agreement & Place Order" button. Creates order + agreement + notifies producer.

4. **AI Insights** (🤖): Three sub-tabs available to all roles:
   - Demand Forecast: Linear regression per product, predicts next 30-day demand
   - Price Prediction: Suggests optimal prices (increase/decrease/hold)
   - Recommendations: Collaborative filtering suggests products to buy/stock
   - Models auto-retrain every 5 minutes from latest Supabase data (self-learning)

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
- You do NOT have access to user data — don't pretend to look up orders or accounts.
- If a user reports a bug or error, suggest they check: (1) Supabase credentials in secrets, (2) run the migration SQL files, (3) contact admin.
"""


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

    try:
        from groq import Groq

        client = Groq(api_key=api_key)

        # Build messages: system prompt + chat history + new message
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in chat_history[-10:]:  # keep last 10 messages for context
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        return response.choices[0].message.content or "I couldn't generate a response. Please try again."

    except ImportError:
        return (
            "⚠️ The `groq` package is not installed. Run `pip install groq` "
            "and restart the app."
        )
    except Exception as e:
        err = str(e).lower()
        if "invalid api key" in err or "401" in err:
            return (
                "⚠️ Invalid Groq API key. Please check your GROQ_API_KEY in "
                "Streamlit secrets. Get a valid key at https://console.groq.com/keys"
            )
        if "rate limit" in err or "429" in err:
            return "⏳ Rate limit reached. Please wait a moment and try again."
        return f"⚠️ Assistant error: {e}"
