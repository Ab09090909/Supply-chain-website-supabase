"""
Auth UI pages - professional login / signup / forgot-password / reset-password.

Each function renders a complete page and returns True on success.
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


# ---------------------------------------------------------------------------
# LOGIN PAGE
# ---------------------------------------------------------------------------
def render_login_page() -> bool:
    """Returns True if login succeeded (caller should rerun)."""
    st.markdown(
        """
        <style>
        .auth-card {
            max-width: 460px;
            margin: 2rem auto;
            padding: 2.5rem;
            border-radius: 16px;
            background: #ffffff;
            box-shadow: 0 8px 32px rgba(15, 23, 42, 0.08);
            border: 1px solid #e2e8f0;
        }
        .auth-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.25rem;
        }
        .auth-subtitle {
            color: #64748b;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">Sign in to your account</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-subtitle">Welcome back to the AI Supply Chain Platform</div>',
        unsafe_allow_html=True,
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

        col1, col2 = st.columns([1, 1])
        with col1:
            submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")
        with col2:
            st.markdown(
                "<div style='padding-top: 0.4rem; font-size: 0.85rem;'>"
                "<a href='?page=forgot-password' style='color:#10b981;text-decoration:none;'>"
                "Forgot password?</a></div>",
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

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#64748b; font-size:0.9rem;'>"
        "Don't have an account? "
        "<a href='?page=signup' style='color:#10b981;font-weight:600;text-decoration:none;'>"
        "Create one</a></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return False


# ---------------------------------------------------------------------------
# SIGNUP PAGE
# ---------------------------------------------------------------------------
def render_signup_page() -> bool:
    st.markdown(
        """
        <style>
        .auth-card {
            max-width: 520px;
            margin: 1.5rem auto;
            padding: 2.5rem;
            border-radius: 16px;
            background: #ffffff;
            box-shadow: 0 8px 32px rgba(15, 23, 42, 0.08);
            border: 1px solid #e2e8f0;
        }
        .auth-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.25rem;
        }
        .auth-subtitle {
            color: #64748b;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }
        .role-card {
            padding: 1rem;
            border-radius: 10px;
            border: 2px solid #e2e8f0;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">Create your account</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-subtitle">Join the AI Supply Chain Platform in under a minute</div>',
        unsafe_allow_html=True,
    )

    # --- Role selection (cards) ---
    st.markdown("##### Choose your account type")
    role_cols = st.columns(4)
    selected_role = st.session_state.get("signup_role", "customer")
    for i, role in enumerate(ROLE_OPTIONS):
        with role_cols[i]:
            is_selected = role == selected_role
            label = role.capitalize()
            desc = ROLE_DESCRIPTIONS[role]
            bg = "#ecfdf5" if is_selected else "#ffffff"
            border = "#10b981" if is_selected else "#e2e8f0"
            weight = "700" if is_selected else "500"
            color = "#047857" if is_selected else "#0f172a"
            st.markdown(
                f"""
                <div class='role-card' style='background:{bg}; border-color:{border};'>
                    <div style='font-weight:{weight}; color:{color}; font-size:1rem;'>{label}</div>
                    <div style='font-size:0.75rem; color:#64748b; margin-top:0.25rem;'>{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(label, key=f"role_{role}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                st.session_state["signup_role"] = role
                st.rerun()

    st.markdown("---")

    with st.form("signup_form", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            full_name = st.text_input("Full name / Company name *", placeholder="Jane Doe")
        with col_b:
            email = st.text_input("Email address *", placeholder="you@example.com")

        col_c, col_d = st.columns(2)
        with col_c:
            password = st.text_input("Password *", type="password", placeholder="Min 8 characters")
        with col_d:
            confirm = st.text_input("Confirm password *", type="password")

        col_e, col_f = st.columns(2)
        with col_e:
            phone = st.text_input("Phone (optional)", placeholder="+1 555-0100")
        with col_f:
            location = st.text_input("Location (optional)", placeholder="City, Country")

        company = ""
        if selected_role in ("producer", "merchant"):
            company = st.text_input("Company name (optional)", placeholder="Acme Inc.")

        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        submitted = st.form_submit_button("Create account", use_container_width=True, type="primary")

        if submitted:
            # Validation
            if not full_name or not email or not password:
                show_error_message("Please fill in all required fields (*)")
            elif len(password) < 8:
                show_error_message("Password must be at least 8 characters long.")
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

    st.markdown("</div>", unsafe_allow_html=True)
    return False


# ---------------------------------------------------------------------------
# FORGOT PASSWORD PAGE
# ---------------------------------------------------------------------------
def render_forgot_password_page() -> bool:
    st.markdown(
        """
        <style>
        .auth-card {
            max-width: 460px;
            margin: 2rem auto;
            padding: 2.5rem;
            border-radius: 16px;
            background: #ffffff;
            box-shadow: 0 8px 32px rgba(15, 23, 42, 0.08);
            border: 1px solid #e2e8f0;
        }
        .auth-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.25rem;
        }
        .auth-subtitle {
            color: #64748b;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">Reset your password</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-subtitle">Enter your email and we\'ll send you a reset link.</div>',
        unsafe_allow_html=True,
    )

    with st.form("forgot_password_form", clear_on_submit=False):
        email = st.text_input("Email address", placeholder="you@example.com")
        submitted = st.form_submit_button("Send reset link", use_container_width=True, type="primary")

        if submitted:
            if not email:
                show_error_message("Please enter your email address.")
            else:
                with st.spinner("Sending reset link..."):
                    ok, msg = request_password_reset(email)
                if ok:
                    st.success(msg)
                    st.info("Check your inbox (and spam folder) for an email from Supabase.")
                    st.markdown(
                        "<div style='text-align:center; margin-top:1rem;'>"
                        "<a href='?page=login' style='color:#10b981;font-weight:600;'>"
                        "Back to login</a></div>",
                        unsafe_allow_html=True,
                    )

    st.markdown(
        "<div style='text-align:center; margin-top:1rem; font-size:0.9rem; color:#64748b;'>"
        "Remembered your password? "
        "<a href='?page=login' style='color:#10b981;font-weight:600;text-decoration:none;'>"
        "Sign in</a></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return False


# ---------------------------------------------------------------------------
# RESET PASSWORD PAGE (landed from email link)
# ---------------------------------------------------------------------------
def render_reset_password_page() -> bool:
    st.markdown(
        """
        <style>
        .auth-card {
            max-width: 460px;
            margin: 2rem auto;
            padding: 2.5rem;
            border-radius: 16px;
            background: #ffffff;
            box-shadow: 0 8px 32px rgba(15, 23, 42, 0.08);
            border: 1px solid #e2e8f0;
        }
        .auth-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.25rem;
        }
        .auth-subtitle {
            color: #64748b;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">Set a new password</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-subtitle">Choose a strong password for your account.</div>',
        unsafe_allow_html=True,
    )

    with st.form("reset_password_form", clear_on_submit=False):
        new_password = st.text_input("New password", type="password", placeholder="Min 8 characters")
        confirm = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Update password", use_container_width=True, type="primary")

        if submitted:
            if not new_password or not confirm:
                show_error_message("Please fill in both fields.")
            elif len(new_password) < 8:
                show_error_message("Password must be at least 8 characters long.")
            elif new_password != confirm:
                show_error_message("Passwords do not match.")
            else:
                with st.spinner("Updating password..."):
                    ok, msg = update_password(new_password)
                if ok:
                    st.success(msg)
                    st.markdown(
                        "<div style='text-align:center; margin-top:1rem;'>"
                        "<a href='?page=login' style='color:#10b981;font-weight:600;'>"
                        "Go to login</a></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    show_error_message(msg)

    st.markdown("</div>", unsafe_allow_html=True)
    return False


# ---------------------------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------------------------
def handle_logout():
    sign_out()
    st.rerun()
