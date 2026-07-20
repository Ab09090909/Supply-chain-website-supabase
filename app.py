"""
AI Supply Chain Platform - Main Application Entry Point
========================================================
All imports are LAZY (deferred inside functions) so that:
  • A broken import in one module doesn't crash the entire app
  • Pages only load when the user navigates to them
  • A startup file check tells you exactly which files are missing

Run with:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st
import os
import sys
from pathlib import Path


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
# 2. STARTUP FILE CHECK — verify all required files exist
# ---------------------------------------------------------------------------
# These are the minimum files needed for the app to work.
REQUIRED_FILES = [
    "app.py",
    "database/__init__.py",
    "database/connection.py",
    "auth/__init__.py",
    "auth/session.py",
    "auth/service.py",
    "auth/pages.py",
    "auth/verification.py",
    "utils/__init__.py",
    "utils/theme.py",
    "utils/ui.py",
    "utils/constants.py",
    "utils/helpers.py",
    "utils/storage.py",
    "utils/preferences.py",
    "utils/db_health.py",
    "utils/business_card.py",
    "utils/card_image.py",
    "utils/event_tracking/analytics_collector.py",
    "ai/__init__.py",
    "ai/assistant.py",
    "ai/engine.py",
    "ai/matchmaking.py",
    "ai/price_prediction.py",
    "ai/demand_forecast.py",
    "ai/recommendations.py",
    "pages/__init__.py",
    "pages/common/__init__.py",
    "pages/common/marketplace.py",
    "pages/common/ai_insights.py",
    "pages/common/ai_assistant.py",
    "pages/common/notifications.py",
    "pages/common/analytics.py",
    "pages/common/landing.py",
    "pages/common/product_detail.py",
    "pages/common/merchant_requests.py",
    "pages/common/public_card.py",
    "pages/producer/__init__.py",
    "pages/producer/dashboard.py",
    "pages/producer/inventory.py",
    "pages/producer/orders.py",
    "pages/producer/profile.py",
    "pages/producer/merchant_match.py",
    "pages/merchant/__init__.py",
    "pages/merchant/dashboard.py",
    "pages/merchant/orders.py",
    "pages/merchant/profile.py",
    "pages/customer/__init__.py",
    "pages/customer/marketplace.py",
    "pages/customer/cart.py",
    "pages/customer/orders.py",
    "pages/customer/profile.py",
    "pages/customer/dashboard.py",
    "pages/admin/__init__.py",
    "pages/admin/dashboard.py",
    "pages/admin/fraud.py",
    "pages/admin/management.py",
    "pages/admin/profile.py",
    "pages/admin/users.py",
    "requirements.txt",
]


def _check_required_files() -> list:
    """Returns a list of missing files. Empty list = all good."""
    missing = []
    # Find the project root (where app.py lives)
    # On Streamlit Cloud: /mount/src/<repo-name>/
    # On local: current working directory
    candidates = [
        Path(__file__).resolve().parent,  # same dir as app.py
        Path.cwd(),  # current working directory
    ]
    project_root = None
    for c in candidates:
        if (c / "app.py").exists():
            project_root = c
            break
    if project_root is None:
        project_root = Path(__file__).resolve().parent

    for f in REQUIRED_FILES:
        if not (project_root / f).exists():
            missing.append(f)
    return missing


# Run the check
_missing_files = _check_required_files()

if _missing_files:
    st.error("🚨 **Critical: Files are missing from your deployment!**")
    st.markdown(
        "The app cannot work without these files. You probably didn't upload "
        "all files from the zip to your GitHub repo."
    )
    st.markdown(f"**Project root detected:** `{Path(__file__).resolve().parent}`")
    st.markdown(f"**Missing {len(_missing_files)} file(s):**")
    for f in _missing_files:
        st.markdown(f"  - ❌ `{f}`")

    st.markdown("---")
    st.markdown("### 📋 How to fix this")
    st.markdown("""
    1. **Download the latest zip** from your AI assistant
    2. **Unzip it** — you should see ~50 files
    3. **Upload ALL files to your GitHub repo** (not just `app.py`!)
       - You can drag-and-drop all files at once on GitHub's web editor
       - Or use `git add . && git commit -m "Add all files" && git push`
    4. **Verify** by refreshing this page — the missing files list should be empty
    """)
    st.markdown("---")
    st.markdown(f"**Files that DO exist** (for reference):")
    existing = [f for f in REQUIRED_FILES if not (Path(__file__).resolve().parent / f).exists() is False]
    # Actually list what's there
    root = Path(__file__).resolve().parent
    all_files = []
    for ext in ("*.py", "*.txt", "*.toml"):
        all_files.extend(str(p.relative_to(root)) for p in root.rglob(ext) if "__pycache__" not in str(p))
    st.code("\n".join(sorted(all_files)[:50]), language="text")
    st.stop()  # Stop execution — don't try to load anything else


# ---------------------------------------------------------------------------
# 3. THEME (imported early, but wrapped in try/except)
# ---------------------------------------------------------------------------
try:
    from utils.theme import init_theme, render_theme_toggle, apply_theme_css
except Exception as _theme_err:
    init_theme = lambda: None
    render_theme_toggle = lambda: None
    apply_theme_css = lambda: None
    st.warning(f"Theme module failed to load: {_theme_err}")

# Apply theme CSS immediately
try:
    init_theme()
    apply_theme_css()
except Exception:
    pass


# ---------------------------------------------------------------------------
# 4. SESSION HELPERS (lazy import)
# ---------------------------------------------------------------------------
def _get_auth_helpers():
    """Lazy import of auth session helpers."""
    try:
        from auth.session import is_logged_in, get_current_user, get_current_role
        return is_logged_in, get_current_user, get_current_role
    except Exception as e:
        st.error(f"Failed to load auth module: {e}")
        return None, None, None


def _get_auth_pages():
    """Lazy import of auth page renderers."""
    try:
        from auth.pages import (
            render_login_page,
            render_signup_page,
            render_forgot_password_page,
            render_reset_password_page,
            handle_logout,
        )
        return render_login_page, render_signup_page, render_forgot_password_page, render_reset_password_page, handle_logout
    except Exception as e:
        st.error(f"Failed to load auth pages: {e}")
        return None, None, None, None, None


def _get_verification_helpers():
    """Lazy import of verification helpers."""
    try:
        from auth.verification import is_user_verified, get_verification_status, render_verification_page
        return is_user_verified, get_verification_status, render_verification_page
    except Exception:
        return (lambda: True), (lambda: "verified"), (lambda: None)


def _get_validate_config():
    try:
        from database.connection import validate_config
        return validate_config
    except Exception:
        return None


def _render_app_url_debug() -> None:
    """Admin-only: show the detected app URL + env vars.

    Useful when debugging custom domain setups — admins can confirm
    the app is reading the right ``APP_URL`` / ``RENDER_EXTERNAL_URL``
    so QR codes, password-reset links, etc. point to the right place.
    """
    try:
        is_logged_in, get_current_user, get_current_role = _get_auth_helpers()
        if not all([is_logged_in, get_current_user, get_current_role]):
            return
        if (get_current_role() or "").lower() != "admin":
            return
    except Exception:
        return

    try:
        from utils.app_url import get_app_url
        detected = get_app_url()
    except Exception as e:
        detected = f"<error: {e}>"

    with st.sidebar:
        with st.expander("🌐 App URL (debug)", expanded=False):
            st.markdown(f"**Detected:** `{detected}`")
            st.caption("Used in QR codes, password-reset emails, public card links.")
            st.markdown("**Env vars read (in order):**")
            st.code(
                "APP_URL={APP_URL}\n"
                "RENDER_EXTERNAL_URL={RENDER_EXTERNAL_URL}\n"
                "STREAMLIT_RUNTIME_ENV={STREAMLIT_RUNTIME_ENV}\n"
                "st.secrets[APP_URL]={SECRETS}".format(
                    APP_URL=os.environ.get("APP_URL", "<not set>"),
                    RENDER_EXTERNAL_URL=os.environ.get("RENDER_EXTERNAL_URL", "<not set>"),
                    STREAMLIT_RUNTIME_ENV=os.environ.get("STREAMLIT_RUNTIME_ENV", "<not set>"),
                    SECRETS="<try/except>",
                ),
                language="bash",
            )
            st.markdown(
                "💡 On Render, set `APP_URL=https://yourdomain.com` in the "
                "Environment tab to use a custom domain."
            )


# ---------------------------------------------------------------------------
# 5. SUPABASE CONFIG HEALTH CHECK
# ---------------------------------------------------------------------------
@st.cache_data
def _check_supabase_config() -> dict:
    """Verify Supabase credentials are reachable. Cached."""
    # Step 1: Check if supabase package is installed
    try:
        import supabase  # noqa: F401
    except ImportError:
        return {
            "connection_ok": False,
            "connection_error": (
                "The `supabase` Python package is not installed. "
                "On Streamlit Cloud: go to Settings → Requirements and make sure "
                "`requirements.txt` is being used. Or add a `packages.txt` file. "
                "Locally: run `pip install -r requirements.txt`."
            ),
            "SUPABASE_URL_loaded": False,
            "SUPABASE_ANON_KEY_loaded": False,
        }

    # Step 2: Try to import database.connection
    try:
        from database.connection import _get_config, _debug_config_status
    except Exception as e:
        return {
            "connection_ok": False,
            "connection_error": f"database.connection module failed to load: {e}",
            "SUPABASE_URL_loaded": False,
            "SUPABASE_ANON_KEY_loaded": False,
        }

    # Step 3: Read config
    try:
        url = _get_config("SUPABASE_URL")
        anon = _get_config("SUPABASE_ANON_KEY")
        status = _debug_config_status()
        status["SUPABASE_URL_loaded"] = bool(url)
        status["SUPABASE_ANON_KEY_loaded"] = bool(anon)
    except Exception as e:
        return {"connection_ok": False, "connection_error": str(e)}

    # Step 4: Try a real connection
    if url and anon:
        try:
            from supabase import create_client
            client = create_client(url, anon)
            client.table("profiles").select("id").limit(1).execute()
            status["connection_ok"] = True
            status["connection_error"] = None
        except Exception as e:
            status["connection_ok"] = False
            status["connection_error"] = str(e)[:400]
    else:
        status["connection_ok"] = False
        status["connection_error"] = "Missing SUPABASE_URL or SUPABASE_ANON_KEY in secrets."
    return status


def _render_config_warning(status: dict):
    """Show a config warning banner on auth pages if config is broken."""
    if status.get("connection_ok"):
        return

    st.error("⚠️ Supabase is not configured correctly. Auth will fail until this is fixed.")
    with st.expander("🔍 Diagnostic details", expanded=True):
        st.markdown(f"""
| Check | Status |
|-------|--------|
| `SUPABASE_URL` loaded | `{'✅' if status.get('SUPABASE_URL_loaded') else '❌'}` |
| `SUPABASE_ANON_KEY` loaded | `{'✅' if status.get('SUPABASE_ANON_KEY_loaded') else '❌'}` |
| Supabase API reachable | `{'✅' if status.get('connection_ok') else '❌'}` |
""")
        if status.get("connection_error"):
            st.code(status["connection_error"], language="text")

        st.markdown("""
**How to fix:**
1. Make sure `.streamlit/secrets.toml` (Streamlit Cloud) or `.env` has:
   ```
   SUPABASE_URL=https://YOURPROJECT.supabase.co
   SUPABASE_ANON_KEY=eyJ...your-anon-key...
   SUPABASE_SERVICE_ROLE_KEY=eyJ...your-service-role-key...
   GROQ_API_KEY=gsk_...your-groq-key...
   ```
2. `SUPABASE_SERVICE_ROLE_KEY` must start with `eyJ` (NOT `gsk_`)
3. `GROQ_API_KEY` must start with `gsk_` (NOT `eyJ`)
4. Restart the app after editing secrets.
""")


# ---------------------------------------------------------------------------
# 6. QUERY-PARAM ROUTER (for auth pages)
# ---------------------------------------------------------------------------
query_page = st.query_params.get("page", "")


def render_auth_page():
    """Route to the correct auth page based on ?page= query param."""
    try:
        status = _check_supabase_config()
        _render_config_warning(status)
    except Exception:
        pass

    render_login, render_signup, render_forgot, render_reset, _ = _get_auth_pages()
    if render_login is None:
        st.error("Auth pages could not be loaded.")
        return

    if query_page == "signup":
        if render_signup():
            st.query_params.clear()
            # After signup, the user is automatically signed in. New users
            # should be sent to their profile page where the verification
            # prompt lives, so they're asked to verify right away.
            st.session_state["force_nav"] = "profile"
            st.rerun()
    elif query_page == "forgot-password":
        render_forgot()
    elif query_page == "reset-password":
        render_reset()
    else:
        if render_login():
            st.query_params.clear()
            st.rerun()


# ---------------------------------------------------------------------------
# 7. SIDEBAR
# ---------------------------------------------------------------------------
def render_sidebar():
    """Render role-appropriate sidebar navigation."""
    is_logged_in, get_current_user, get_current_role = _get_auth_helpers()
    if not all([is_logged_in, get_current_user, get_current_role]):
        return None

    user = get_current_user()
    role = get_current_role()

    with st.sidebar:
        st.markdown("### 📦 AI Supply Chain")
        st.caption("Platform v5.0 · Supabase")

        try:
            render_theme_toggle()
            st.markdown("---")
        except Exception:
            pass

        validate_config = _get_validate_config()
        if validate_config is not None:
            try:
                config_check = validate_config()
                if not config_check["is_clean"]:
                    with st.expander("⚠️ Config Issues Found", expanded=False):
                        for issue in config_check["issues"]:
                            st.markdown(issue)
                        st.markdown("---")
                        st.markdown("**Where to get the right keys:**")
                        st.markdown("• **Supabase keys** → Dashboard → Project Settings → API")
                        st.markdown("• **Groq key** → https://console.groq.com/keys")
            except Exception:
                pass

        if user:
            try:
                from utils.ui import sidebar_user_card
                sidebar_user_card(user)
                st.markdown("---")
            except Exception:
                pass

            force_nav = st.session_state.pop("force_nav", None)
            choice = _role_nav(role, force_nav)

            st.markdown("---")
            _, _, _, _, handle_logout = _get_auth_pages()
            if handle_logout and st.button("🚪 Logout", use_container_width=True):
                handle_logout()
            return choice
    return None


def _role_nav(role: str, force_nav: str | None = None) -> str | None:
    """Returns the selected page key.

    Renders a beautiful custom navigation menu in the sidebar using
    styled buttons. The selected button gets a green left border +
    emerald background tint + bolder text. Hover lifts the card and
    adds a subtle shadow.
    """
    common_tabs = {
        "marketplace": ("🛒", "Marketplace"),
        "ai_insights": ("🤖", "AI Insights"),
        "assistant":   ("💬", "AI Assistant"),
        "notifications": ("🔔", "Notifications"),
        "analytics":   ("📊", "Live Analytics"),
        "profile":     ("👤", "Profile"),
    }
    if role == "producer":
        opts = ["dashboard", "inventory", "orders", "merchant_match"] + list(common_tabs.keys())
        tabs = {
            "dashboard":      ("📊", "Dashboard"),
            "inventory":      ("📦", "Inventory"),
            "orders":         ("🛒", "Orders"),
            "merchant_match": ("🤝", "Merchant Match"),
            **common_tabs,
        }
        key = "producer_nav"
    elif role == "merchant":
        opts = ["dashboard", "orders", "merchant_requests"] + list(common_tabs.keys())
        tabs = {
            "dashboard":         ("📊", "Dashboard"),
            "orders":            ("🛍️", "My Orders"),
            "merchant_requests": ("📨", "Match Requests"),
            **common_tabs,
        }
        key = "merchant_nav"
    elif role == "customer":
        opts = ["dashboard", "marketplace", "cart", "orders", "ai_insights", "assistant", "notifications", "profile"]
        tabs = {
            "dashboard":     ("📊", "Dashboard"),
            "marketplace":   ("🛒", "Marketplace"),
            "cart":          ("🛒", "Cart"),
            "orders":        ("📦", "My Orders"),
            "ai_insights":   ("🤖", "AI Insights"),
            "assistant":     ("💬", "AI Assistant"),
            "notifications": ("🔔", "Notifications"),
            "profile":       ("👤", "Profile"),
        }
        key = "customer_nav"
    elif role == "admin":
        opts = ["dashboard", "management", "fraud"] + list(common_tabs.keys())
        tabs = {
            "dashboard":   ("📊", "Dashboard"),
            "management":  ("⚙️", "Management"),
            "fraud":       ("🚨", "Fraud Center"),
            **common_tabs,
        }
        key = "admin_nav"
    else:
        return None

    # Make sure the current session value is in opts (defensive)
    current = st.session_state.get(key)
    if current not in opts:
        current = opts[0]
        st.session_state[key] = current

    # Header label
    st.markdown(
        """
        <div style='
            display:flex; align-items:center; gap:6px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #047857;
            margin: 1.25rem 0 0.5rem 0;
            padding-left: 4px;
        '>
            <span style='
                display:inline-block; width:18px; height:18px; line-height:18px;
                text-align:center;
                background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
                border-radius: 5px;
                font-size: 0.65rem;
                box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
            '>🧭</span>
            Navigation
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render each nav item as a clickable "card". The selected one
    # is highlighted with a green left border + emerald background.
    for opt in opts:
        emoji, label = tabs[opt]
        is_selected = opt == st.session_state.get(key)

        # Use a Streamlit button but style it to look like a nav card.
        # The button label is the emoji + label. We use type="primary"
        # for the selected one and "secondary" for the others to
        # get different visual treatments.
        if st.button(
            f"{emoji}  {label}",
            key=f"nav_{role}_{opt}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state[key] = opt
            st.rerun()

    return st.session_state.get(key)


# ---------------------------------------------------------------------------
# 8. ROLE-BASED CONTENT (all imports are lazy)
# ---------------------------------------------------------------------------
def render_role_content(choice: str | None):
    """Render the page for the selected nav choice. All imports are lazy."""
    is_logged_in, get_current_user, get_current_role = _get_auth_helpers()
    if not all([is_logged_in, get_current_user, get_current_role]):
        st.error("Session helpers not available.")
        return

    role = get_current_role()
    is_user_verified_fn, _, _ = _get_verification_helpers()

    try:
        # Default to True (allow access) if anything goes wrong
        verified = True
        if is_user_verified_fn:
            try:
                verified = is_user_verified_fn()
            except Exception:
                verified = True  # if check fails, allow access (graceful)

        # For brand-new signups (must_verify flag), show a banner at the
        # top of every page so the user can't miss the verification step.
        if not verified and st.session_state.get("must_verify") and choice != "profile":
            st.info(
                "🔐 **Welcome! Please verify your account** to unlock ordering, "
                "messaging, and AI features."
            )
            if st.button("🔐 Verify My Account", type="primary", key="banner_verify"):
                st.session_state["force_nav"] = "profile"
                st.rerun()
            st.markdown("---")

        # If user just signed up AND the dashboard is the default page,
        # auto-route them to the profile (where the verification form lives).
        # This is the bulletproof fix: even if force_nav didn't take, we
        # check the must_verify flag here.
        #
        # IMPORTANT: only do this for non-admin users. Admins don't need
        # to verify, and forcing them to the profile page would trap them
        # there (the admin profile doesn't show a verification form, so
        # the must_verify flag would never get cleared, and they'd be
        # stuck in a redirect loop).
        if (
            st.session_state.get("must_verify")
            and choice == "dashboard"
            and role != "admin"
        ):
            st.session_state["force_nav"] = "profile"
            st.rerun()

        if not verified and choice not in ("marketplace", "profile"):
            _render_verification_gate()
            return

        if choice == "marketplace":
            from pages.common.marketplace import render_shared_marketplace
            render_shared_marketplace()
            if not verified:
                st.markdown("---")
                st.warning("⚠️ Verify your account to unlock ordering, messaging, and AI features.")
                if st.button("🔐 Verify My Account", type="primary", use_container_width=True):
                    st.session_state["force_nav"] = "profile"
                    st.rerun()
            return

        if choice == "ai_insights":
            from pages.common.ai_insights import render_ai_insights
            render_ai_insights()
            return

        if choice == "assistant":
            from pages.common.ai_assistant import render_ai_assistant
            render_ai_assistant()
            return

        if choice == "notifications":
            from pages.common.notifications import render_notifications
            render_notifications()
            return

        if choice == "analytics":
            from pages.common.analytics import render_analytics_dashboard
            render_analytics_dashboard()
            return

        if choice == "merchant_requests":
            from pages.common.merchant_requests import render_merchant_requests
            render_merchant_requests()
            return

        if role == "producer":
            if choice == "inventory":
                from pages.producer.inventory import render_producer_inventory
                render_producer_inventory()
            elif choice == "orders":
                from pages.producer.orders import render_producer_orders
                render_producer_orders()
            elif choice == "merchant_match":
                from pages.producer.merchant_match import render_producer_merchant_match
                render_producer_merchant_match()
            elif choice == "profile":
                from pages.producer.profile import render_producer_profile
                render_producer_profile()
                if not verified:
                    st.markdown("---")
                    _, _, render_verification_page = _get_verification_helpers()
                    if render_verification_page:
                        render_verification_page()
            else:
                from pages.producer.dashboard import render_producer_dashboard
                render_producer_dashboard()

        elif role == "merchant":
            if choice == "orders":
                from pages.merchant.orders import render_merchant_orders
                render_merchant_orders()
            elif choice == "merchant_requests":
                from pages.common.merchant_requests import render_merchant_requests
                render_merchant_requests()
            elif choice == "profile":
                from pages.merchant.profile import render_merchant_profile
                render_merchant_profile()
                if not verified:
                    st.markdown("---")
                    _, _, render_verification_page = _get_verification_helpers()
                    if render_verification_page:
                        render_verification_page()
            else:
                from pages.merchant.dashboard import render_merchant_dashboard
                render_merchant_dashboard()

        elif role == "customer":
            if choice == "dashboard":
                from pages.customer.dashboard import render_customer_dashboard
                render_customer_dashboard()
            elif choice == "cart":
                from pages.customer.cart import render_customer_cart
                render_customer_cart()
            elif choice == "orders":
                from pages.customer.orders import render_customer_orders
                render_customer_orders()
            elif choice == "profile":
                from pages.customer.profile import render_customer_profile
                render_customer_profile()
                if not verified:
                    st.markdown("---")
                    _, _, render_verification_page = _get_verification_helpers()
                    if render_verification_page:
                        render_verification_page()
            else:
                from pages.common.marketplace import render_shared_marketplace
                render_shared_marketplace()
                if not verified:
                    st.markdown("---")
                    st.warning("⚠️ Verify your account to unlock ordering.")
                    if st.button("🔐 Verify My Account", type="primary", use_container_width=True):
                        st.session_state["force_nav"] = "profile"
                        st.rerun()

        elif role == "admin":
            if choice == "management":
                from pages.admin.management import render_admin_management
                render_admin_management()
            elif choice == "fraud":
                from pages.admin.fraud import render_admin_fraud
                render_admin_fraud()
            elif choice == "profile":
                from pages.admin.profile import render_admin_profile
                render_admin_profile()
            else:
                from pages.admin.dashboard import render_admin_dashboard
                render_admin_dashboard()

    except Exception as e:
        st.error(f"Failed to render page: {e}")
        with st.expander("🔧 Error details"):
            import traceback
            st.code(traceback.format_exc())


def _render_verification_gate():
    """Show the verification page when an unverified user tries to access a restricted page."""
    st.warning("🔒 **Verification Required**")
    st.markdown(
        "You need to verify your identity before you can access this page. "
        "Please upload your national ID, driver's license, or business license below."
    )
    st.markdown("---")
    _, _, render_verification_page = _get_verification_helpers()
    if render_verification_page:
        render_verification_page()
    st.markdown("---")
    st.info("💡 While you wait for verification, you can still browse the **Marketplace**.")


# ---------------------------------------------------------------------------
# 9. MAIN ROUTER
# ---------------------------------------------------------------------------
def main():
    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None
    if "user" not in st.session_state:
        st.session_state["user"] = None

    # Safety net: if the user is an admin, they should never have the
    # must_verify flag set (admins don't need to verify). This handles
    # the case where a session was created before this fix was deployed
    # and the flag is stuck on.
    try:
        user_obj = st.session_state.get("user") or {}
        if (user_obj.get("role") or "").lower() == "admin":
            st.session_state.pop("must_verify", None)
    except Exception:
        pass

    try:
        init_theme()
        apply_theme_css()
    except Exception:
        pass

    is_logged_in_fn, _, _ = _get_auth_helpers()
    # Call the function to check if user is actually logged in
    logged_in = False
    if is_logged_in_fn:
        try:
            logged_in = is_logged_in_fn()
        except Exception:
            logged_in = False

    if not logged_in:
        # Check for a public business card URL first (?card=<id>)
        # This is a public page — no login required.
        card_id = st.query_params.get("card", "")
        if card_id:
            try:
                from pages.common.public_card import render_public_card_page
                render_public_card_page(card_id)
                return
            except Exception as e:
                st.error(f"Failed to load public card: {e}")
                return

        # Not logged in → show the **modern marketing landing page** ABOVE
        # the auth form. Visitors see the value prop + features + benefits
        # before being asked to sign in (like Stripe / Linear / Vercel).
        #
        # The auth form still lives in the right column so the page is
        # scannable — marketing on the left, action on the right.

        # Inject the Inter font and full-bleed layout
        st.markdown(
            """<style>
            [data-testid="stSidebar"] { display: none; }
            [data-testid="stSidebarCollapsedControl"] { display: none; }
            .block-container { padding-top: 1rem !important; max-width: 1200px !important; }
            /* Hide the scroll-to-top iframe — it's invisible by design */
            iframe[title="st_scroll_helper"] { display: none !important; }
            </style>""",
            unsafe_allow_html=True,
        )

        # Render the marketing landing page first (it includes its own
        # scroll-to-top via the page_header animation + the scroll JS below)
        try:
            from pages.common.landing import render_landing_page
            render_landing_page()
        except Exception as e:
            st.warning(f"Landing page failed to load: {e}")

        # Visual divider before the auth form
        st.markdown(
            """<div style='text-align:center;margin:2rem 0 1.5rem 0;'>
                <div style='display:inline-flex;align-items:center;gap:14px;'>
                    <div style='width:60px;height:1px;background:linear-gradient(90deg,transparent,#cbd5e1,transparent);'></div>
                    <div style='font-size:0.78rem;font-weight:700;letter-spacing:0.16em;
                                text-transform:uppercase;color:#94a3b8;'>Or jump right in</div>
                    <div style='width:60px;height:1px;background:linear-gradient(90deg,transparent,#cbd5e1,transparent);'></div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        # Render the auth form (login / signup / forgot / reset) inside
        # a constrained max-width so it doesn't stretch full-width
        st.markdown(
            """<style>
            .block-container { max-width: 540px !important; }
            </style>""",
            unsafe_allow_html=True,
        )

        # Scroll-to-top iframe
        try:
            import streamlit.components.v1 as components
            components.html(
                """<script>
                (function() {
                    const scrollToTop = () => {
                        try {
                            window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
                            const main = document.querySelector('section.main');
                            if (main) main.scrollTop = 0;
                        } catch (e) {}
                    };
                    scrollToTop();
                    const observer = new MutationObserver(() => {
                        clearTimeout(window.__stScrollT);
                        window.__stScrollT = setTimeout(scrollToTop, 50);
                    });
                    if (document.body) {
                        observer.observe(document.body, { childList: true, subtree: true });
                    }
                    setTimeout(scrollToTop, 100);
                    setTimeout(scrollToTop, 500);
                })();
                </script>""",
                height=0,
                width=0,
            )
        except Exception:
            pass
        render_auth_page()
        return

    # Logged in → show sidebar + role content
    # If the last Supabase call returned a 401 with "JWT expired", show
    # a one-time banner that tells the user to log in again, and clear
    # the session so they're forced to the login page on next rerun.
    from auth.session import has_expired_jwt_error, clear_jwt_expired, clear_session
    if has_expired_jwt_error():
        st.warning(
            "🔒 **Your session has expired.** Please log in again to continue. "
            "Anything you didn't save will be lost."
        )
        # Don't clear the session immediately — let the user see the
        # warning, click the logout button, and explicitly leave.
        # Just clear the expired flag so the banner doesn't repeat.
        clear_jwt_expired()

    choice = render_sidebar()
    # Admin-only debug panel for the detected app URL (useful when
    # configuring a custom domain — shows the URL the app thinks it's
    # running at, plus which env vars are set).
    try:
        _render_app_url_debug()
    except Exception:
        pass
    if choice and choice != "marketplace":
        st.session_state.pop("view_product_id", None)
    render_role_content(choice)


if __name__ == "__main__":
    main()
