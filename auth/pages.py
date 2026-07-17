"""
Auth UI pages - professional login / signup / forgot-password / reset-password.

Each function renders a complete page and returns True on success.

Each page now has a beautiful welcome section at the top (brand logo,
tagline, key features) followed by the form card. This gives visitors
a clear "what is this platform" moment before they sign in.
"""
from __future__ import annotations

import streamlit as st

from auth.service import (
    sign_in,
    sign_up,
    sign_out,
    request_password_reset,
    update_password,
)
from auth.session import is_logged_in, get_current_user, get_current_role
from utils.ui import (
    page_header,
    role_badge,
    show_success_toast,
    show_error_message,
)
from utils.constants import ROLE_OPTIONS, ROLE_DESCRIPTIONS


# -----------------------------------------------------------------------
# SHARED AUTH STYLES (injected once per page render)
# -----------------------------------------------------------------------
_AUTH_CSS = """
<style>
/* Auth page wrapper — centres the card on screen */
.auth-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.5rem 1rem 1.5rem 1rem;
    min-height: 60vh;
}

/* ── Welcome / hero section above the card ──────────────────── */
.auth-hero {
    width: 100%;
    max-width: 480px;
    margin: 0.5rem 0 1rem 0;
    text-align: center;
    animation: fadeInDown 0.4s ease-out;
    /* Make sure the hero never gets clipped by a parent with
       ``overflow: hidden`` (some Streamlit containers do this). */
    overflow: visible;
}
.auth-hero-logo {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: linear-gradient(135deg, #0f3d23 0%, #1a5c2e 50%, #10b981 100%);
    background-size: 200% 200%;
    animation: gradientShift 6s ease infinite;
    padding: 6px 14px 6px 8px;
    border-radius: 50px;
    color: white;
    font-weight: 800;
    font-size: 0.85rem;
    letter-spacing: -0.01em;
    box-shadow: 0 6px 18px rgba(16, 185, 129, 0.3);
    margin-bottom: 10px;
}
.auth-hero-logo-icon {
    width: 26px; height: 26px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.18);
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.9rem;
}
.auth-hero-tagline {
    font-size: 1.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #047857 0%, #10b981 60%, #34d399 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 4px 0;
    line-height: 1.25;
    letter-spacing: -0.02em;
}
.auth-hero-sub {
    color: #64748b;
    font-size: 0.82rem;
    margin: 0 0 10px 0;
    line-height: 1.4;
}

/* Feature pills */
.auth-features {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    justify-content: center;
    margin-bottom: 0;
}
.auth-feature {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #ecfdf5;
    color: #047857;
    border: 1px solid #a7f3d0;
    padding: 3px 8px;
    border-radius: 16px;
    font-size: 0.66rem;
    font-weight: 600;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    white-space: nowrap;
}
.auth-feature:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(16, 185, 129, 0.15);
}

/* ── The card itself ──────────────────────────────────────── */
.auth-card {
    width: 100%;
    max-width: 480px;
    padding: 1.5rem 1.75rem;
    border-radius: 18px;
    background: #ffffff;
    box-shadow: 0 8px 40px rgba(15, 23, 42, 0.09);
    border: 1px solid #e8edf2;
    position: relative;
    overflow: hidden;
    animation: fadeInUp 0.5s ease-out;
}
.auth-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #10b981 0%, #34d399 50%, #6ee7b7 100%);
}

/* Logo / brand mark above title */
.auth-brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1.5rem;
}
.auth-brand-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #10b981;
    display: inline-block;
}
.auth-brand-name {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #94a3b8;
}

/* Title + subtitle */
.auth-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.02em;
    margin: 0 0 0.25rem 0;
    line-height: 1.2;
}
.auth-subtitle {
    color: #64748b;
    font-size: 0.85rem;
    margin: 0 0 1.25rem 0;
    line-height: 1.4;
}

/* Divider with label */
.auth-divider {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 1.25rem 0;
    color: #cbd5e1;
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.auth-divider::before,
.auth-divider::after {
    content: "";
    flex: 1;
    height: 1px;
    background: #e8edf2;
}

/* Footer link row */
.auth-footer {
    text-align: center;
    margin-top: 1.25rem;
    font-size: 0.85rem;
    color: #64748b;
}
.auth-footer a {
    color: #10b981;
    font-weight: 600;
    text-decoration: none;
}
.auth-footer a:hover { text-decoration: underline; }

/* Role selection cards */
.role-card {
    padding: 0.9rem 0.75rem;
    border-radius: 10px;
    border: 2px solid #e2e8f0;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    text-align: center;
    margin-bottom: 0.25rem;
}
.role-card.selected {
    border-color: #10b981;
    background: #ecfdf5;
}
</style>
"""


# The welcome / hero section that sits above every auth page.
# It introduces the platform to visitors who haven't signed in yet.
_AUTH_HERO_HTML = """
<div class="auth-hero">
  <div class="auth-hero-logo">
    <span class="auth-hero-logo-icon">📦</span>
    <span>EthioChain</span>
  </div>
  <div class="auth-hero-tagline">AI Supply Chain Platform</div>
  <div class="auth-hero-sub">
    One smart marketplace for producers, merchants, and customers — with AI forecasts, smart matching, and end-to-end order tracking.
  </div>
  <div class="auth-features">
    <span class="auth-feature">🤖 AI</span>
    <span class="auth-feature">🤝 Matching</span>
    <span class="auth-feature">📦 Tracking</span>
    <span class="auth-feature">⭐ Reviews</span>
    <span class="auth-feature">🔒 Secure</span>
    <span class="auth-feature">📈 Insights</span>
  </div>
</div>
"""


def _inject_auth_css():
    """Inject shared auth styles — safe to call multiple times (browser dedupes)."""
    try:
        st.html(_AUTH_CSS)
    except AttributeError:
        st.markdown(f'<div style="display:none">{_AUTH_CSS}</div>', unsafe_allow_html=True)


def _auth_hero():
    """Render the welcome section that sits above the auth card."""
    try:
        st.html(_AUTH_HERO_HTML)
    except AttributeError:
        st.markdown(_AUTH_HERO_HTML, unsafe_allow_html=True)


def _auth_header(title: str, subtitle: str):
    """Render the in-card brand mark + title + subtitle block."""
    # Note: the main "EthioChain" / welcome section is now in
    # ``_auth_hero()`` above the card. This header is just the
    # card-internal title (e.g. "Sign in to your account").
    st.markdown(
        f"""
        <div class="auth-title">{title}</div>
        <div class="auth-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def _auth_footer(text: str, link_label: str, link_href: str):
    st.markdown(
        f"<div class='auth-footer'>{text} "
        f"<a href='{link_href}'>{link_label}</a></div>",
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------
# LOGIN PAGE
# -----------------------------------------------------------------------
def render_login_page() -> bool:
    """Returns True if login succeeded (caller should rerun)."""
    _inject_auth_css()
    _auth_hero()
    _auth_header(
        "Sign in to your account",
        "Welcome back to the AI Supply Chain Platform",
    )

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input(
            "Email address",
            placeholder="you@example.com",
            key="login_email",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password",
        )

        col1, col2 = st.columns([3, 2])
        with col1:
            submitted = st.form_submit_button(
                "Sign in", use_container_width=True, type="primary"
            )
        with col2:
            st.markdown(
                "<div style='padding-top:0.45rem; text-align:right;'>"
                "<a href='?page=forgot-password' style='color:#10b981; font-size:0.82rem; "
                "font-weight:600; text-decoration:none;'>Forgot password?</a></div>",
                unsafe_allow_html=True,
            )

        if submitted:
            if not email or not password:
                show_error_message("Please enter both email and password.")
            else:
                with st.spinner("Signing in..."):
                    ok, msg = sign_in(email, password)
                if ok:
                    show_success_toast("Welcome back!")
                    return True
                else:
                    show_error_message(msg)

    _auth_footer("Don't have an account?", "Create one", "?page=signup")
    return False


# -----------------------------------------------------------------------
# SIGNUP PAGE
# -----------------------------------------------------------------------
def render_signup_page() -> bool:
    _inject_auth_css()
    _auth_hero()
    _auth_header(
        "Create your account",
        "Join the AI Supply Chain Platform in under a minute",
    )

    # --- Role selection ---
    st.markdown(
        "<div style='font-size:0.72rem; font-weight:700; text-transform:uppercase; "
        "letter-spacing:0.08em; color:#94a3b8; margin-bottom:0.6rem;'>Account type</div>",
        unsafe_allow_html=True,
    )
    selected_role = st.session_state.get("signup_role", "customer")
    role_cols = st.columns(len(ROLE_OPTIONS))
    for i, role in enumerate(ROLE_OPTIONS):
        with role_cols[i]:
            is_selected = role == selected_role
            bg = "#ecfdf5" if is_selected else "#f8fafc"
            border = "#10b981" if is_selected else "#e2e8f0"
            color = "#047857" if is_selected else "#475569"
            weight = "700" if is_selected else "500"
            st.markdown(
                f"<div style='padding:0.75rem 0.5rem; border-radius:10px; border:2px solid {border}; "
                f"background:{bg}; text-align:center; margin-bottom:0.2rem;'>"
                f"<div style='font-weight:{weight}; font-size:0.88rem; color:{color};'>{role.capitalize()}</div>"
                f"<div style='font-size:0.68rem; color:#94a3b8; margin-top:0.2rem; line-height:1.3;'>"
                f"{ROLE_DESCRIPTIONS[role]}</div></div>",
                unsafe_allow_html=True,
            )
            if st.button(
                "✓ Selected" if is_selected else "Select",
                key=f"role_{role}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state["signup_role"] = role
                st.rerun()

    st.markdown(
        "<div style='height:1px; background:#e8edf2; margin:1.25rem 0;'></div>",
        unsafe_allow_html=True,
    )

    with st.form("signup_form", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            full_name = st.text_input("Full name *", placeholder="Jane Doe")
        with col_b:
            email = st.text_input("Email *", placeholder="you@example.com")

        col_c, col_d = st.columns(2)
        with col_c:
            password = st.text_input("Password *", type="password", placeholder="Min 8 characters")
        with col_d:
            confirm = st.text_input("Confirm password *", type="password")

        col_e, col_f = st.columns(2)
        with col_e:
            phone = st.text_input("Phone", placeholder="+1 555-0100")
        with col_f:
            location = st.text_input("Location", placeholder="City, Country")

        company = ""
        if selected_role in ("producer", "merchant"):
            company = st.text_input("Company name", placeholder="Acme Inc.")

        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        submitted = st.form_submit_button(
            "Create account", use_container_width=True, type="primary"
        )

        if submitted:
            if not full_name or not email or not password:
                show_error_message("Please fill in all required fields (*)")
            elif len(password) < 8:
                show_error_message("Password must be at least 8 characters.")
            elif password != confirm:
                show_error_message("Passwords do not match.")
            elif not terms:
                show_error_message("Please accept the Terms of Service to continue.")
            else:
                with st.spinner("Creating your account..."):
                    ok, msg = sign_up(
                        email=email,
                        password=password,
                        full_name=full_name,
                        role=st.session_state.get("signup_role", "customer"),
                        phone=phone,
                        location=location,
                        company=company,
                    )
                if ok:
                    show_success_toast("Account created! Welcome aboard.")
                    return True
                else:
                    show_error_message(msg)

    _auth_footer("Already have an account?", "Sign in", "?page=login")
    return False


# -----------------------------------------------------------------------
# FORGOT PASSWORD PAGE
# -----------------------------------------------------------------------
def render_forgot_password_page() -> bool:
    _inject_auth_css()
    _auth_hero()
    _auth_header(
        "Reset your password",
        "Enter your email and we'll send you a reset link.",
    )

    with st.form("forgot_password_form", clear_on_submit=False):
        email = st.text_input("Email address", placeholder="you@example.com")
        submitted = st.form_submit_button(
            "Send reset link", use_container_width=True, type="primary"
        )

        if submitted:
            if not email:
                show_error_message("Please enter your email address.")
            else:
                with st.spinner("Sending reset link..."):
                    ok, msg = request_password_reset(email)
                if ok:
                    st.success(msg)
                    st.info("Check your inbox (and spam folder) for the reset email.")

    _auth_footer("Remembered your password?", "Sign in", "?page=login")
    return False


# -----------------------------------------------------------------------
# RESET PASSWORD PAGE (landed from email link)
# -----------------------------------------------------------------------
def render_reset_password_page() -> bool:
    _inject_auth_css()
    _auth_hero()
    _auth_header(
        "Set a new password",
        "Choose a strong password for your account.",
    )

    with st.form("reset_password_form", clear_on_submit=False):
        new_password = st.text_input(
            "New password", type="password", placeholder="Min 8 characters"
        )
        confirm = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button(
            "Update password", use_container_width=True, type="primary"
        )

        if submitted:
            if not new_password or not confirm:
                show_error_message("Please fill in both fields.")
            elif len(new_password) < 8:
                show_error_message("Password must be at least 8 characters.")
            elif new_password != confirm:
                show_error_message("Passwords do not match.")
            else:
                with st.spinner("Updating password..."):
                    ok, msg = update_password(new_password)
                if ok:
                    st.success(msg)
                    _auth_footer("Password updated!", "Go to login →", "?page=login")
                else:
                    show_error_message(msg)

    return False


# -----------------------------------------------------------------------
# LOGOUT
# -----------------------------------------------------------------------
def handle_logout():
    sign_out()
    st.rerun()
