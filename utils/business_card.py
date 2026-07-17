"""
Business Card + QR Code module.

Renders a beautiful digital business card and generates a QR code that,
when scanned, opens the user's public business card page online.

Why online instead of vCard?
  * The user said "make link for qr code to see user business card
    online without login" — so the QR encodes a URL to the public
    card page, not a vCard. This means:
      - Anyone can scan the QR with their phone → opens the URL in
        the phone's browser → sees the full card → can "Save Contact"
        from there.
      - The public URL is shareable anywhere (text, email, social) —
        not just via QR scan.
  * The user can preview the public URL right in the profile tab.

Layout
------
The card matches the user's reference design — everything stacked
vertically under the QR:
    ┌────────────────────────────────┐
    │     ┌───────────────┐           │
    │     │      QR       │           │
    │     └───────────────┘           │
    │      SCAN TO VIEW ONLINE        │
    │                                 │
    │      ABRAHAM SMITH              │
    │      SENIOR PRODUCER            │
    │                                 │
    │   🏠  12 Your Business Road     │
    │   📞  +251 911 123 456          │
    │   ✉️  abraham@gmail.com         │
    │   📷  @abraham                  │
    │   📘  abraham.smith              │
    │                                 │
    │     ── Powered by EthioChain ── │
    └─────────────────────────────────┘
"""
from __future__ import annotations

import base64
import io
import re
from typing import Optional

import streamlit as st


# -----------------------------------------------------------------------
# vCard encoding — still useful for "Save Contact" downloads
# -----------------------------------------------------------------------
def build_vcard(user: dict) -> str:
    """Build a vCard 3.0 string for the given user.

    The public card page offers a "Save Contact" download that gives
    the user this vCard — phones offer to import it.
    """
    name = (user.get("full_name") or "EthioChain User").strip()
    parts = name.split(maxsplit=1)
    first = parts[0] if parts else name
    last = parts[1] if len(parts) > 1 else ""

    role = (user.get("role") or "").strip().capitalize()
    company = (user.get("company") or "EthioChain").strip()
    title = (user.get("title") or role or "Member").strip()
    phone = (user.get("phone") or "").strip()
    email = (user.get("email") or "").strip()
    location = (user.get("location") or "").strip()
    website = (user.get("website") or "https://eschain.streamlit.app").strip()
    instagram = (user.get("instagram") or "").strip()
    facebook = (user.get("facebook") or "").strip()

    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{name}",
        f"N:{last};{first};;;",
        f"ORG:{company}",
        f"TITLE:{title}",
    ]
    if phone:
        lines.append(f"TEL;TYPE=CELL:{phone}")
    if email:
        lines.append(f"EMAIL;TYPE=WORK:{email}")
    if location:
        lines.append(f"ADR;TYPE=WORK:;;{location};;;;")
    if website:
        lines.append(f"URL:{website}")
    if instagram:
        ig = instagram if instagram.startswith("http") else f"https://instagram.com/{instagram.lstrip('@')}"
        lines.append(f"URL;TYPE=Instagram:{ig}")
    if facebook:
        fb = facebook if facebook.startswith("http") else f"https://facebook.com/{facebook.lstrip('@')}"
        lines.append(f"URL;TYPE=Facebook:{fb}")
    lines.append("END:VCARD")
    return "\r\n".join(lines)


# -----------------------------------------------------------------------
# Public card URL — what the QR encodes
# -----------------------------------------------------------------------
def build_public_card_url(user: dict, base_url: str = "") -> str:
    """Build the public business card URL for the given user.

    The URL is what the QR code encodes — when someone scans it with
    their phone, this URL opens and shows the business card online.
    No login required.

    Args:
        user:     the user dict (we read the user id)
        base_url: optional override for the base URL. If empty, we
                  default to the production EthioChain URL.
    """
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        return ""
    base = (base_url or "https://eschain.streamlit.app").rstrip("/")
    return f"{base}/?card={user_id}"


# -----------------------------------------------------------------------
# QR code generation
# -----------------------------------------------------------------------
def _make_qr_image(data: str, size: int = 10, border: int = 2):
    """Generate a QR code as a PIL Image. Returns None if qrcode isn't installed."""
    try:
        import qrcode
        from qrcode.image.pil import PilImage
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white",
                            image_factory=PilImage)
        return img
    except Exception:
        return None


def make_qr_png(data: str, size: int = 10, border: int = 2) -> Optional[bytes]:
    """Generate a QR code as PNG bytes. Returns None if qrcode isn't installed."""
    img = _make_qr_image(data, size=size, border=border)
    if img is None:
        return None
    buf = io.BytesIO()
    try:
        img.save(buf, format="PNG")
    except Exception:
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tmp_path = tf.name
        try:
            img.save(tmp_path)
            with open(tmp_path, "rb") as f:
                buf.write(f.read())
        finally:
            try: os.unlink(tmp_path)
            except Exception: pass
    return buf.getvalue()


# -----------------------------------------------------------------------
# Inline card preview — stacked vertically under the QR
# -----------------------------------------------------------------------
def _build_card_preview_html(qr_png_b64: str, user: dict) -> str:
    """Build an HTML preview of the business card with QR on top and
    all info below — matching the user's "stack everything under the
    QR" request.
    """
    name = user.get("full_name") or "Your Name"
    role = (user.get("role") or "").strip().capitalize()
    title = user.get("title") or role or "Member"
    phone = user.get("phone") or "—"
    email = user.get("email") or "—"
    location = user.get("location") or "—"
    instagram = user.get("instagram") or ""
    facebook = user.get("facebook") or ""

    if qr_png_b64:
        qr_html = f'<img src="data:image/png;base64,{qr_png_b64}" style="width:220px;height:220px;border-radius:10px;box-shadow:0 4px 14px rgba(0,0,0,0.1);" />'
    else:
        qr_html = '<div style="width:220px;height:220px;border-radius:10px;background:#fee2e2;display:flex;align-items:center;justify-content:center;color:#991b1b;font-size:0.8rem;text-align:center;padding:8px;">QR unavailable</div>'

    social_rows = ""
    if instagram:
        ig = instagram.lstrip("@")
        social_rows += f"""
        <div style="display:flex;align-items:center;justify-content:center;gap:8px;margin-top:8px;font-size:0.88rem;color:#1f2937;">
            <span style="font-size:1.05rem;">📷</span>
            <span style="text-transform:uppercase;letter-spacing:0.04em;font-weight:500;">{ig}</span>
        </div>"""
    if facebook:
        fb = facebook.lstrip("@")
        social_rows += f"""
        <div style="display:flex;align-items:center;justify-content:center;gap:8px;margin-top:8px;font-size:0.88rem;color:#1f2937;">
            <span style="font-size:1.05rem;">📘</span>
            <span style="text-transform:uppercase;letter-spacing:0.04em;font-weight:500;">{fb}</span>
        </div>"""

    return f"""
    <div style="
        max-width: 460px;
        margin: 1rem auto;
        background: #ffffff;
        border-radius: 14px;
        box-shadow: 0 8px 28px rgba(0,0,0,0.12);
        padding: 22px 24px 18px 24px;
        text-align: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    ">
        <div style="display:flex;flex-direction:column;align-items:center;gap:8px;">
            {qr_html}
            <div style="background:#10b981;color:white;font-size:0.55rem;font-weight:700;letter-spacing:0.06em;padding:3px 10px;border-radius:10px;margin-top:-2px;">SCAN TO VIEW ONLINE</div>
        </div>
        <div style="margin-top:14px;">
            <div style="font-size:1.25rem;font-weight:700;color:#0f172a;letter-spacing:0.05em;text-transform:uppercase;">{name}</div>
            <div style="font-size:0.72rem;color:#6b7280;letter-spacing:0.18em;text-transform:uppercase;margin-top:3px;">{title or role or 'Member'}</div>
        </div>
        <div style="height:1px;background:linear-gradient(90deg,transparent,#cbd5e1,transparent);margin:14px 0;"></div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:6px;">
            <div style="display:flex;align-items:center;gap:8px;font-size:0.88rem;color:#1f2937;">
                <span style="font-size:0.95rem;">🏠</span>
                <span style="text-transform:uppercase;letter-spacing:0.03em;font-weight:500;">{location}</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:2px;font-size:0.88rem;color:#1f2937;">
                <span style="font-size:0.95rem;">📞</span>
                <span style="font-weight:500;">{phone}</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:2px;font-size:0.82rem;color:#1f2937;word-break:break-all;">
                <span style="font-size:0.95rem;">✉️</span>
                <span style="text-transform:lowercase;font-weight:500;">{email}</span>
            </div>
            {social_rows}
        </div>
        <div style="margin-top:16px;font-size:0.65rem;color:#94a3b8;letter-spacing:0.04em;">
            Powered by <strong style="color:#10b981;">EthioChain</strong>
        </div>
    </div>
    """


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------
def _safe_filename(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", (text or "user").strip())
    return s.strip("_") or "user"


def render_business_card(user: dict) -> None:
    """Render the business card section in the profile page.

    Shows:
      * Public card URL (so the user can copy/share it)
      * Social handle inputs (Instagram / Facebook)
      * Live HTML preview of the card with the QR
      * Download buttons (Card PNG, QR PNG, vCard file)
    """
    st.markdown("---")
    st.markdown("### 💼 Digital Business Card")
    st.caption(
        "Your digital business card. Share it via QR or link — anyone "
        "who scans it sees the card online, no login required."
    )

    # Build the public URL (what the QR encodes)
    public_url = build_public_card_url(user)
    if public_url:
        # Show the URL with a copy button so the user can share it
        st.markdown("**🔗 Your public card link:**")
        st.code(public_url, language=None)

    # Optional Instagram / Facebook handles
    _render_social_inputs(user)

    # Refresh user dict with the social fields the user typed
    user_for_display = dict(user)
    user_for_display["instagram"] = st.session_state.get("bc_instagram", user.get("instagram") or "")
    user_for_display["facebook"]   = st.session_state.get("bc_facebook",   user.get("facebook")   or "")

    vcard_str = build_vcard(user_for_display)
    # The QR code on the card encodes the public URL (so scanning
    # opens the card in a phone browser, not just a contact save).
    qr_data = public_url if public_url else vcard_str
    qr_bytes = make_qr_png(qr_data, size=10, border=2)

    # Render the live card preview
    if qr_bytes:
        qr_b64 = base64.b64encode(qr_bytes).decode()
    else:
        qr_b64 = ""

    from utils.ui import _html
    _html(_build_card_preview_html(qr_b64, user_for_display))

    if not qr_bytes:
        st.warning(
            "⚠️ QR code generation is unavailable. "
            "Add `qrcode` and `Pillow` to requirements.txt and restart."
        )

    # Download buttons
    _render_downloads(user_for_display, vcard_str, qr_bytes)


def _render_social_inputs(user: dict) -> None:
    if "bc_instagram" not in st.session_state:
        st.session_state["bc_instagram"] = user.get("instagram") or ""
    if "bc_facebook" not in st.session_state:
        st.session_state["bc_facebook"] = user.get("facebook") or ""

    c1, c2 = st.columns(2)
    with c1:
        st.text_input(
            "Instagram handle (optional)",
            value=st.session_state["bc_instagram"],
            key="_bc_ig_input",
            placeholder="@yourhandle",
            help="Type your Instagram handle, e.g. @yourhandle.",
            on_change=_sync_social_inputs,
        )
    with c2:
        st.text_input(
            "Facebook handle (optional)",
            value=st.session_state["bc_facebook"],
            key="_bc_fb_input",
            placeholder="yourpage",
            help="Type your Facebook page name, e.g. yourpage.",
            on_change=_sync_social_inputs,
        )


def _sync_social_inputs() -> None:
    st.session_state["bc_instagram"] = st.session_state.get("_bc_ig_input", "")
    st.session_state["bc_facebook"]   = st.session_state.get("_bc_fb_input", "")


def _render_downloads(user: dict, vcard_str: str, qr_bytes: Optional[bytes]) -> None:
    """Render the download buttons."""
    st.markdown("")
    c1, c2, c3 = st.columns(3)
    safe_name = _safe_filename(user.get("full_name", ""))

    # 1. Card PNG
    with c1:
        png_bytes = None
        try:
            from utils.card_image import render_card_to_png
            # Build the URL so the QR on the downloaded card also points
            # to the public page
            public_url = build_public_card_url(user)
            png_bytes = render_card_to_png(
                user,
                qr_data=public_url or vcard_str,
            )
        except Exception:
            png_bytes = None
        if png_bytes:
            st.download_button(
                label="⬇️ Download Card (PNG)",
                data=png_bytes,
                file_name=f"business_card_{safe_name}.png",
                mime="image/png",
                use_container_width=True,
                help="Download the digital business card as a PNG image.",
            )
        else:
            st.button(
                "⬇️ Download Card (PNG)",
                disabled=True,
                use_container_width=True,
                help="Pillow isn't installed.",
            )

    # 2. QR code PNG (encodes the public URL)
    with c2:
        if qr_bytes:
            st.download_button(
                label="⬇️ Download QR (PNG)",
                data=qr_bytes,
                file_name=f"qr_{safe_name}.png",
                mime="image/png",
                use_container_width=True,
                help="Download the QR code (encodes your public card link).",
            )
        else:
            st.button(
                "⬇️ Download QR (PNG)",
                disabled=True,
                use_container_width=True,
                help="qrcode isn't installed.",
            )

    # 3. vCard file (always available — for "Save Contact")
    with c3:
        vcf_bytes = vcard_str.encode("utf-8")
        st.download_button(
            label="⬇️ Save Contact (.vcf)",
            data=vcf_bytes,
            file_name=f"contact_{safe_name}.vcf",
            mime="text/vcard",
            use_container_width=True,
            help="Download a .vcf file you can import into any contacts app.",
        )


def make_vcard_file(user: dict) -> bytes:
    return build_vcard(user).encode("utf-8")
