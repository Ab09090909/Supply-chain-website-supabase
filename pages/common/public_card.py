"""
Public business card view — a beautiful shareable page that anyone can
open by scanning the QR code on the card.

This is a PUBLIC page: no login required, no Streamlit auth gates.
We just look up the user by ID and render their business card.

URL format
----------
``?card=<user_id>``

We could also support lookup by a public slug (e.g. ``?u=abraham``) but
keeping the simple user_id lookup is fine for v1.

How it works
------------
1. ``render_public_card_page()`` is called by the main router when the
   ``card`` query param is set (and the user is NOT logged in OR even
   when they are — the public page is always accessible).
2. It looks up the user by ID in the ``profiles`` table.
3. It renders the card with the same data, plus a "Save Contact"
   button (downloads the vCard) and a "Copy Email / Phone" affordance.
"""
from __future__ import annotations

import streamlit as st
import base64
import re

from database.connection import get_supabase_client, get_supabase_admin_client


def _safe_filename(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", (text or "user").strip())
    return s.strip("_") or "user"


def _get_client():
    """Prefer the admin client (bypasses RLS) for public lookups, fall back."""
    try:
        return get_supabase_admin_client()
    except Exception:
        return get_supabase_client()


def _build_vcard(user: dict) -> str:
    """Build a vCard 3.0 string for the given user."""
    from utils.business_card import build_vcard
    return build_vcard(user)


def render_public_card_page(card_id: str) -> None:
    """Render the public business card page for the given user ID.

    Called by the main router when ``?card=<id>`` is in the URL.
    No login required.
    """
    # Hide the sidebar (this is a public page)
    st.markdown(
        """<style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="stSidebarCollapsedControl"] { display: none; }
        .block-container { padding-top: 0.5rem; max-width: 720px; }
        </style>""",
        unsafe_allow_html=True,
    )

    # Look up the user
    try:
        client = _get_client()
        r = client.table("profiles").select(
            "id, full_name, email, phone, location, role, company, "
            "avatar_url, is_verified, instagram, facebook"
        ).eq("id", card_id).maybe_single().execute()
        user = r.data if r and r.data else None
    except Exception as e:
        st.error(f"Failed to load card: {e}")
        return

    if not user:
        st.markdown(
            """
            <div style='
                text-align: center;
                padding: 80px 24px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            '>
                <div style='font-size: 4rem; margin-bottom: 16px;'>🔍</div>
                <h2 style='color: #0f172a; font-weight: 700;'>Card not found</h2>
                <p style='color: #64748b; max-width: 420px; margin: 0 auto;'>
                    This business card link is no longer valid or the
                    profile has been deleted.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Optional: load extended social fields from session_state if the
    # owner is viewing their own card (they typed these in the profile
    # page but they're not stored in the DB). For a public view we use
    # the values saved in the user's profile, or fall back to the
    # values the owner is editing in their own session.
    instagram = ""
    facebook = ""
    # The owner may have unsaved IG/FB in their session — only inject
    # these for the owner themselves. The cards they download include
    # the unsaved values, but the public page shows only saved values.
    try:
        from auth.session import get_current_user
        me = get_current_user() or {}
        if me.get("id") == user.get("id"):
            instagram = st.session_state.get("bc_instagram", "") or ""
            facebook = st.session_state.get("bc_facebook", "") or ""
    except Exception:
        pass

    user_for_card = dict(user)
    user_for_card["instagram"] = instagram
    user_for_card["facebook"]   = facebook

    # ── Render the page header (EthioChain branding) ─────────
    st.markdown(
        """
        <div style='text-align:center; margin-bottom: 1.5rem;'>
          <div style='
              display: inline-flex; align-items: center; justify-content: center;
              gap: 10px;
              background: linear-gradient(135deg, #0f3d23 0%, #1a5c2e 50%, #10b981 100%);
              background-size: 200% 200%; animation: gradientShift 6s ease infinite;
              padding: 8px 16px 8px 10px; border-radius: 50px;
              color: white; font-weight: 800; font-size: 0.9rem;
              box-shadow: 0 6px 18px rgba(16, 185, 129, 0.3);
          '>
              <span style='
                  display: inline-flex; align-items: center; justify-content: center;
                  width: 28px; height: 28px; border-radius: 50%;
                  background: rgba(255, 255, 255, 0.18); font-size: 0.95rem;
              '>📦</span>
              <span>EthioChain</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Render the card preview (HTML, with embedded QR if available) ─
    from utils.business_card import make_qr_png, _build_card_preview_html
    from utils.ui import _html

    vcard = _build_vcard(user_for_card)
    # The public page also has a "scan to save" QR — but since the QR
    # on the card itself should link BACK to this page (so people can
    # re-share it), we encode THIS page's URL into the QR if we know
    # the public base URL. Otherwise we fall back to encoding the
    # vCard so phones can save the contact directly.
    qr_bytes = make_qr_png(vcard, size=10, border=2)
    if qr_bytes:
        qr_b64 = base64.b64encode(qr_bytes).decode()
    else:
        qr_b64 = ""

    _html(_build_card_preview_html(qr_b64, user_for_card))

    # ── Action buttons ──────────────────────────────────────
    st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    safe_name = _safe_filename(user.get("full_name", ""))

    # Save Contact (.vcf) — always available
    with c1:
        vcf_bytes = vcard.encode("utf-8")
        st.download_button(
            label="📇 Save Contact",
            data=vcf_bytes,
            file_name=f"contact_{safe_name}.vcf",
            mime="text/vcard",
            use_container_width=True,
            help="Download a .vcf file you can import into any contacts app.",
            type="primary",
        )

    # Copy phone
    with c2:
        phone = user.get("phone") or ""
        if phone:
            st.download_button(
                label=f"📞 {phone}",
                data=phone,
                file_name=f"phone_{safe_name}.txt",
                mime="text/plain",
                use_container_width=True,
                help="Download a text file with the phone number.",
            )
        else:
            st.button("📞 No phone", disabled=True, use_container_width=True)

    # Copy email
    with c3:
        email = user.get("email") or ""
        if email:
            st.download_button(
                label=f"✉️ {email}",
                data=email,
                file_name=f"email_{safe_name}.txt",
                mime="text/plain",
                use_container_width=True,
                help="Download a text file with the email address.",
            )
        else:
            st.button("✉️ No email", disabled=True, use_container_width=True)

    # ── Powered by + share links ────────────────────────────
    st.markdown(
        """
        <div style='
            text-align: center; margin-top: 1.5rem;
            padding: 1rem;
            background: #f0fdf4;
            border-radius: 12px;
            border: 1px solid #a7f3d0;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        '>
          <div style='font-size: 0.8rem; color: #047857; font-weight: 600;'>
              Powered by
              <a href='https://eschain.streamlit.app' style='color: #10b981; text-decoration: none; font-weight: 700;'>EthioChain</a>
              · AI Supply Chain Platform
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
