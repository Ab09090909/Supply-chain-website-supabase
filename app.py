"""
AI Supply Chain Platform - Main Application Entry Point
========================================================
Handles:
  • Streamlit page config (must be the FIRST st.* call)
  • Auth routing: login / signup / forgot-password / reset-password
  • Role-based dashboards: producer / merchant / customer / admin
  • Session management via st.session_state

Run with:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from auth.session import is_logged_in, get_current_user, get_current_role
from auth.pages import (
    render_login_page,
    render_signup_page,
    render_forgot_password_page,
    render_reset_password_page,
    handle_logout,
)
from utils.ui import sidebar_user_card, role_badge
from utils.constants import ROLE_LABELS
from utils.theme import init_theme, render_theme_toggle, apply_theme_css


# ---------------------------------------------------------------------------
# 1. PAGE CONFIG (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Supply Chain Platform",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# 1b. SUPABASE CONFIG HEALTH CHECK (runs once at startup)
# ---------------------------------------------------------------------------
@st.cache_data
def _check_supabase_config() -> dict:
    """Verify Supabase credentials are reachable. Cached for 60s."""
    from database.connection import _get_config, _get_config_source, _debug_config_status
    url = _get_config("SUPABASE_URL")
    anon = _get_config("SUPABASE_ANON_KEY")
    status = _debug_config_status()
    status["SUPABASE_URL_loaded"] = bool(url)
    status["SUPABASE_ANON_KEY_loaded"] = bool(anon)
    status["SUPABASE_URL_source"] = _get_config_source("SUPABASE_URL")
    status["SUPABASE_ANON_KEY_source"] = _get_config_source("SUPABASE_ANON_KEY")

    # If anon key was loaded under a different alias, expose that fact
    status["anon_key_alias_note"] = ""
    if anon and status["SUPABASE_ANON_KEY_source"]:
        src = status["SUPABASE_ANON_KEY_source"]
        # _get_config_source returns e.g. st.secrets['SUPABASE_KEY']
        if "SUPABASE_ANON_KEY" not in src:
            status["anon_key_alias_note"] = (
                f"Loaded from {src} (you named it differently — that's OK, "
                "but consider renaming to SUPABASE_ANON_KEY for clarity)."
            )

    # Try a real connection test
    if url and anon:
        try:
            from supabase import create_client
            client = create_client(url, anon)
            # Lightweight call: fetch 1 row from profiles (returns [] if empty)
            client.table("profiles").select("id").limit(1).execute()
            status["connection_ok"] = True
            status["connection_error"] = None
        except Exception as e:
            status["connection_ok"] = False
            status["connection_error"] = str(e)[:400]
    else:
        status["connection_ok"] = False
        status["connection_error"] = "Missing URL or anon key"
    return status


def _render_config_warning(status: dict):
    """Show a clear status banner on auth pages if config is broken."""
    if status.get("connection_ok"):
        return  # all good, stay silent

    st.error("⚠️ Supabase is not configured correctly. Auth will fail until this is fixed.")
    with st.expander("🔍 Diagnostic details", expanded=True):
        st.markdown(f"""
| Check | Status |
|-------|--------|
| `.env` file exists at project root | `{'✅' if status['env_file_exists'] else '❌'}` |
| `.streamlit/secrets.toml` exists | `{'✅' if status['secrets_toml_exists'] else '❌'}` |
| `python-dotenv` installed | `{'✅' if status['dotenv_installed'] else '❌ (pip install python-dotenv)'}` |
| `SUPABASE_URL` loaded | `{'✅' if status['SUPABASE_URL_loaded'] else '❌'}` {('from '+status['SUPABASE_URL_source']) if status['SUPABASE_URL_source'] else ''} |
| `SUPABASE_ANON_KEY` loaded | `{'✅' if status['SUPABASE_ANON_KEY_loaded'] else '❌'}` {('from '+status['SUPABASE_ANON_KEY_source']) if status['SUPABASE_ANON_KEY_source'] else ''} |
| Supabase API reachable | `{'✅' if status['connection_ok'] else '❌'}` |
""")
        if status.get("anon_key_alias_note"):
            st.info("ℹ️ " + status["anon_key_alias_note"])

        if status.get("connection_error"):
            st.code(status["connection_error"], language="text")

        st.markdown("""
**How to fix (Streamlit Cloud Secrets panel):**

The exact key names my app looks for are:
```toml
SUPABASE_URL = "https://YOURPROJECT.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOi...your-anon-key..."
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOi...your-service-role-key..."
```

If you only have `SUPABASE_KEY`, that's now accepted as an alias for `SUPABASE_ANON_KEY`.

**Common mistakes:**
1. ❌ Using `SUPABASE_KEY` instead of `SUPABASE_ANON_KEY` — now accepted as alias ✅
2. ❌ Putting the **service_role key** under `SUPABASE_ANON_KEY` — they are DIFFERENT keys. The anon key starts with `eyJhbGciOi...` and has `"role":"anon"` in its payload.
3. ❌ Quotes around the URL — TOML allows it but make sure they're straight `"` not curly `"`.
4. ❌ Putting secrets in a subfolder — `.streamlit/secrets.toml` must be exactly there.

After editing secrets, click **Save** and wait ~1 minute for Streamlit Cloud to propagate, then reboot the app.
""")



# ---------------------------------------------------------------------------
# 2. QUERY-PARAM ROUTER (for auth pages: ?page=signup|forgot-password|...)
# ---------------------------------------------------------------------------
query_page = st.query_params.get("page", "")


def render_auth_page():
    """Route to the correct auth page based on ?page= query param."""
    # Show config warning at top of every auth page if Supabase isn't reachable
    try:
        status = _check_supabase_config()
        _render_config_warning(status)
    except Exception as e:
        st.error(f"Config check failed: {e}")

    if query_page == "signup":
        if render_signup_page():
            st.query_params.clear()
            st.rerun()
    elif query_page == "forgot-password":
        render_forgot_password_page()
    elif query_page == "reset-password":
        render_reset_password_page()
    else:
        # Default = login
        if render_login_page():
            st.query_params.clear()
            st.rerun()


# ---------------------------------------------------------------------------
# 3. ROLE-BASED SIDEBAR NAVIGATION
# ---------------------------------------------------------------------------
def render_sidebar():
    """Render role-appropriate sidebar navigation."""
    user = get_current_user()
    role = get_current_role()

    with st.sidebar:
        st.markdown("### 📦 AI Supply Chain")
        st.caption("Platform v3.0 · Supabase")

        # Theme toggle (light/dark) — always at the top of the sidebar
        render_theme_toggle()
        st.markdown("---")

        if user:
            sidebar_user_card(user)
            st.markdown("---")

            # If a "force_nav" was set (e.g. Contact Producer button),
            # default the radio to that tab and consume the flag.
            force_nav = st.session_state.pop("force_nav", None)

            # Role-specific navigation
            choice = _role_nav(role, force_nav)

            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                handle_logout()
            return choice
    return None


def _role_nav(role: str, force_nav: str | None = None) -> str | None:
    """Returns the selected page key, or None.

    Every role now gets the shared Marketplace, AI Insights, and Notifications tabs.
    Role-specific tabs (inventory, fraud center, etc.) are added on top.

    If `force_nav` is provided (e.g. 'notifications' when user clicks Contact Producer),
    that tab will be pre-selected.
    """
    common_tabs = {
        "marketplace": "🛒 Marketplace",
        "ai_insights": "🤖 AI Insights",
        "notifications": "🔔 Notifications",
        "profile": "👤 Profile",
    }
    if role == "producer":
        opts = ["dashboard", "inventory", "orders"] + list(common_tabs.keys())
        labels = {
            "dashboard": "📊 Dashboard",
            "inventory": "📦 Inventory",
            "orders": "🛒 Orders",
            **common_tabs,
        }
        key = "producer_nav"
    elif role == "merchant":
        opts = ["dashboard", "orders"] + list(common_tabs.keys())
        labels = {
            "dashboard": "📊 Dashboard",
            "orders": "🛍️ My Orders",
            **common_tabs,
        }
        key = "merchant_nav"
    elif role == "customer":
        opts = ["marketplace", "cart", "orders"] + ["ai_insights", "notifications", "profile"]
        labels = {
            "marketplace": "🛒 Marketplace",
            "cart": "🛒 Cart",
            "orders": "📦 My Orders",
            "ai_insights": "🤖 AI Insights",
            "notifications": "🔔 Notifications",
            "profile": "👤 Profile",
        }
        key = "customer_nav"
    elif role == "admin":
        opts = ["dashboard", "users", "fraud"] + list(common_tabs.keys())
        labels = {
            "dashboard": "📊 Dashboard",
            "users": "👥 Users",
            "fraud": "🚨 Fraud Center",
            **common_tabs,
        }
        key = "admin_nav"
    else:
        return None

    # If force_nav is set and is a valid option, override the current selection
    if force_nav and force_nav in opts:
        st.session_state[key] = force_nav

    return st.radio(
        "Navigation",
        options=opts,
        format_func=lambda x: labels[x],
        key=key,
        help="Choose a section to navigate to.",
    )


# ---------------------------------------------------------------------------
# 4. ROLE-BASED MAIN CONTENT
# ---------------------------------------------------------------------------
def render_role_content(choice: str | None):
    role = get_current_role()

    try:
        # ---- Shared tabs (handled first, same for every role) ----
        if choice == "marketplace":
            from pages.common import render_shared_marketplace
            render_shared_marketplace()
            return
        if choice == "ai_insights":
            from pages.common import render_ai_insights
            render_ai_insights()
            return
        if choice == "notifications":
            from pages.common import render_notifications
            render_notifications()
            return

        # ---- Role-specific tabs ----
        if role == "producer":
            from pages.producer import (
                render_producer_dashboard,
                render_producer_inventory,
                render_producer_orders,
                render_producer_profile,
            )
            if choice == "inventory":
                render_producer_inventory()
            elif choice == "orders":
                render_producer_orders()
            elif choice == "profile":
                render_producer_profile()
            else:
                render_producer_dashboard()

        elif role == "merchant":
            from pages.merchant import (
                render_merchant_dashboard,
                render_merchant_orders,
                render_merchant_profile,
            )
            if choice == "orders":
                render_merchant_orders()
            elif choice == "profile":
                render_merchant_profile()
            else:
                render_merchant_dashboard()

        elif role == "customer":
            from pages.customer import (
                render_customer_marketplace,
                render_customer_cart,
                render_customer_orders,
                render_customer_profile,
            )
            if choice == "cart":
                render_customer_cart()
            elif choice == "orders":
                render_customer_orders()
            elif choice == "profile":
                render_customer_profile()
            else:
                # Default for customer = shared marketplace (now with images)
                render_shared_marketplace_safe()

        elif role == "admin":
            from pages.admin import (
                render_admin_dashboard,
                render_admin_users,
                render_admin_fraud,
                render_admin_profile,
            )
            if choice == "users":
                render_admin_users()
            elif choice == "fraud":
                render_admin_fraud()
            elif choice == "profile":
                render_admin_profile()
            else:
                render_admin_dashboard()
    except Exception as e:
        st.error(f"Failed to render page: {e}")


def render_shared_marketplace_safe():
    """Wrapper so the customer default route uses the shared marketplace."""
    from pages.common import render_shared_marketplace
    render_shared_marketplace()


# ---------------------------------------------------------------------------
# 5. MAIN ROUTER
# ---------------------------------------------------------------------------
def main():
    # Initialize session_state defaults
    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None
    if "user" not in st.session_state:
        st.session_state["user"] = None

    # Initialize theme (light/dark)
    init_theme()
    apply_theme_css()

    # If not logged in -> show auth page, no sidebar
    if not is_logged_in():
        # Hide sidebar on auth pages for a cleaner look
        st.markdown(
            """<style>
            [data-testid="stSidebar"] { display: none; }
            [data-testid="stSidebarCollapsedControl"] { display: none; }
            .block-container { padding-top: 2rem; max-width: 800px; }
            </style>""",
            unsafe_allow_html=True,
        )
        render_auth_page()
        return

    # Logged in -> show sidebar + role content
    choice = render_sidebar()

    # If user navigated away from the marketplace, clear the product detail view
    if choice and choice != "marketplace":
        st.session_state.pop("view_product_id", None)

    render_role_content(choice)


if __name__ == "__main__":
    main()
