"""
Business Card + QR Code module.

Renders a beautiful digital business card (matching the design from
the user's reference image) and generates a downloadable QR code that,
when scanned, opens the user's contact info on the scanner's phone.

Features
--------
* Beautiful HTML business card with round profile photo, name, title,
  and contact details (address, phone, email, social media).
* QR code is generated locally (no network call) and encoded as a
  vCard so most phones automatically offer to "Add to Contacts" on scan.
* Both the QR code and the full business card can be downloaded as
  PNG files — fully offline.
* The QR code uses the high error-correction level so it works even
  when printed small or partially obscured.
* A "Print" view is also provided via a separate download button.

Usage
-----
    from utils.business_card import render_business_card
    render_business_card(user_dict)  # user_dict has full_name, email,
                                       # phone, location, avatar_url, etc.
"""
from __future__ import annotations

import base64
import io
import json
import re
from typing import Dict, Optional

import streamlit as st

from utils.ui import _html


# Lazy-import qrcode so the module loads even if qrcode isn't installed.
# We show a friendly warning if the user tries to generate a QR code
# without the library available.
def _get_qr_lib():
    try:
        import qrcode
        from qrcode.image.pure import PyPNGImage
        # Return a factory that builds a PNG image
        return qrcode, PyPNGImage
    except ImportError:
        return None, None


def _safe_filename(text: str) -> str:
    """Turn a user-provided name into something safe for a filename."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", (text or "user").strip())
    return s.strip("_") or "user"


# -----------------------------------------------------------------------
# vCard encoding — what the QR code stores
# -----------------------------------------------------------------------
def build_vcard(user: dict) -> str:
    """Build a vCard 3.0 string for the given user.

    The QR code stores this string, so when someone scans the QR with
    their phone camera they get a "Save contact" prompt with all the
    fields pre-filled (name, phone, email, address, social media as URLs).
    """
    name = (user.get("full_name") or "EthioChain User").strip()
    # Split name into first/last — best effort
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
        # ADR field: PO Box, extended, street, city, region, postal, country
        lines.append(f"ADR;TYPE=WORK:;;{location};;;;")
    if website:
        lines.append(f"URL:{website}")
    if instagram:
        # Store as URL so phones link to the profile
        ig = instagram if instagram.startswith("http") else f"https://instagram.com/{instagram.lstrip('@')}"
        lines.append(f"URL;TYPE=Instagram:{ig}")
    if facebook:
        fb = facebook if facebook.startswith("http") else f"https://facebook.com/{facebook.lstrip('@')}"
        lines.append(f"URL;TYPE=Facebook:{fb}")
    lines.append("END:VCARD")
    return "\r\n".join(lines)


# -----------------------------------------------------------------------
# QR code generation
# -----------------------------------------------------------------------
def make_qr_png(data: str, size: int = 12, border: int = 2) -> Optional[bytes]:
    """Generate a QR code as PNG bytes. Returns None if qrcode isn't installed.

    Args:
        data:   the string to encode (usually a vCard)
        size:   pixel size of each "module" (square). The final image
                will be roughly ``size * len_modules`` pixels wide.
        border: number of white modules around the edge.
    """
    qrcode, image_factory = _get_qr_lib()
    if qrcode is None:
        return None
    qr = qrcode.QRCode(
        version=None,                       # auto-detect smallest version
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 30% — robust
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white", image_factory=image_factory)
    # Different image factories expose different save APIs:
    #  * PyPNGImage.save(path)         — needs a file path
    #  * PIL.Image.save(buf, format=…)  — needs a buffer + format
    # We unify by detecting the type and using the right call.
    buf = io.BytesIO()
    try:
        # PIL-backed image (image_factory returned a PIL Image)
        img.save(buf, format="PNG")
    except TypeError:
        # PyPNGImage — save to a temp file, then read back
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
# Business card HTML — looks like the user's reference image
# -----------------------------------------------------------------------
def _build_card_html(user: dict) -> str:
    """Build the HTML for the digital business card."""
    name = user.get("full_name") or "Your Name"
    role = (user.get("role") or "").strip().capitalize()
    company = user.get("company") or "Independent"
    title = user.get("title") or role or "Member"
    phone = user.get("phone") or "—"
    email = user.get("email") or "—"
    location = user.get("location") or "—"
    instagram = user.get("instagram") or ""
    facebook = user.get("facebook") or ""
    avatar = user.get("avatar_url") or ""

    # Build initials for the fallback avatar
    parts = name.split()
    initials = (parts[0][:1] + (parts[1][:1] if len(parts) > 1 else "")).upper() or "?"

    if avatar:
        avatar_html = (
            f'<img src="{avatar}" '
            f'style="width:130px;height:130px;border-radius:50%;object-fit:cover;'
            f'border:3px solid #d4d4d4;box-shadow:0 4px 12px rgba(0,0,0,0.1);" />'
        )
    else:
        avatar_html = (
            f'<div style="width:130px;height:130px;border-radius:50%;'
            f'background:linear-gradient(135deg,#10b981 0%,#047857 100%);'
            f'display:flex;align-items:center;justify-content:center;'
            f'color:#fff;font-weight:700;font-size:2.4rem;font-family:Georgia,serif;'
            f'border:3px solid #d4d4d4;box-shadow:0 4px 12px rgba(0,0,0,0.1);">{initials}</div>'
        )

    # Social links
    social_rows = ""
    if instagram:
        ig = instagram if instagram.startswith("http") else f"https://instagram.com/{instagram.lstrip('@')}"
        social_rows += f"""
        <div style="display:flex;align-items:center;gap:10px;margin-top:10px;font-size:0.85rem;color:#1f2937;">
            <span style="font-size:1.15rem;">📷</span>
            <span style="text-transform:uppercase;letter-spacing:0.04em;font-weight:500;">{instagram.lstrip('@').replace('https://instagram.com/','')}</span>
        </div>"""
    if facebook:
        fb = facebook if facebook.startswith("http") else f"https://facebook.com/{facebook.lstrip('@')}"
        fb_display = facebook.lstrip('@').replace('https://facebook.com/','').replace('https://www.facebook.com/','')
        social_rows += f"""
        <div style="display:flex;align-items:center;gap:10px;margin-top:10px;font-size:0.85rem;color:#1f2937;">
            <span style="font-size:1.15rem;">📘</span>
            <span style="text-transform:uppercase;letter-spacing:0.04em;font-weight:500;">{fb_display}</span>
        </div>"""

    card_html = f"""
    <div style="
        max-width: 540px;
        margin: 1rem auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 8px 28px rgba(0,0,0,0.12);
        padding: 28px 32px;
        display: grid;
        grid-template-columns: auto 1px 1fr;
        gap: 24px;
        align-items: center;
        font-family: 'Georgia', 'Times New Roman', serif;
    ">
        <div style="display:flex;flex-direction:column;align-items:center;gap:10px;min-width:140px;">
            {avatar_html}
            <div style="text-align:center;margin-top:8px;">
                <div style="font-size:1.35rem;font-weight:700;color:#0f172a;letter-spacing:0.05em;text-transform:uppercase;">{name}</div>
                <div style="font-size:0.78rem;color:#6b7280;letter-spacing:0.18em;text-transform:uppercase;margin-top:4px;">{title or role or 'Member'}</div>
            </div>
        </div>
        <div style="width:1px;align-self:stretch;background:linear-gradient(180deg,transparent 0%,#cbd5e1 20%,#cbd5e1 80%,transparent 100%);"></div>
        <div style="display:flex;flex-direction:column;gap:8px;">
            <div style="display:flex;align-items:flex-start;gap:12px;font-size:0.92rem;color:#1f2937;">
                <span style="font-size:1.1rem;line-height:1.2;">🏠</span>
                <span style="text-transform:uppercase;letter-spacing:0.03em;font-weight:500;line-height:1.35;">{location}</span>
            </div>
            <div style="display:flex;align-items:center;gap:12px;margin-top:6px;font-size:0.92rem;color:#1f2937;">
                <span style="font-size:1.1rem;">📞</span>
                <span style="font-weight:500;">{phone}</span>
            </div>
            <div style="display:flex;align-items:center;gap:12px;margin-top:6px;font-size:0.85rem;color:#1f2937;word-break:break-all;">
                <span style="font-size:1.1rem;">✉️</span>
                <span style="text-transform:lowercase;font-weight:500;">{email}</span>
            </div>
            {social_rows}
        </div>
    </div>
    """
    return card_html


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------
def render_business_card(user: dict) -> None:
    """Render the business card UI + QR code + download buttons.

    The user can:
      * See their beautiful digital business card
      * Download the card as a PNG image
      * Download the QR code as a PNG image
      * Customize the social-media fields shown on the card
    """
    st.markdown("---")
    st.markdown("### 💼 Digital Business Card")
    st.caption(
        "Your digital business card. Share it with anyone — the QR code "
        "stores your full contact info so phones offer to save it on scan."
    )

    # Optional inputs the user can fill in (Instagram / Facebook handles
    # don't exist in the profile by default, so we let the user add them).
    _render_social_inputs(user)

    # Refresh user dict with the social fields the user just typed in
    # (so the QR / card reflect them immediately without a DB round-trip).
    user_for_display = dict(user)
    user_for_display["instagram"] = st.session_state.get("bc_instagram", user.get("instagram") or "")
    user_for_display["facebook"]   = st.session_state.get("bc_facebook",   user.get("facebook")   or "")

    # Render the card
    _html(_build_card_html(user_for_display))

    # Download + QR section
    _render_downloads(user_for_display)


def _render_social_inputs(user: dict) -> None:
    """Render the social-media input row. State is held in session_state so
    the user can type without saving first.
    """
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
            help="Type your Instagram handle, e.g. @yourhandle. Leave empty to hide.",
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
    """Copy the social inputs into bc_instagram / bc_facebook so the
    QR + card use the latest values.
    """
    st.session_state["bc_instagram"] = st.session_state.get("_bc_ig_input", "")
    st.session_state["bc_facebook"]   = st.session_state.get("_bc_fb_input", "")


def _render_downloads(user: dict) -> None:
    """Render the download buttons: card PNG + QR code PNG."""
    st.markdown("")
    c1, c2, c3 = st.columns(3)

    # 1. Card PNG
    with c1:
        try:
            from utils.card_image import render_card_to_png
            png_bytes = render_card_to_png(user)
        except Exception:
            png_bytes = None
        if png_bytes:
            st.download_button(
                label="⬇️ Download Card (PNG)",
                data=png_bytes,
                file_name=f"business_card_{_safe_filename(user.get('full_name', ''))}.png",
                mime="image/png",
                use_container_width=True,
                help="Download the digital business card as a PNG image.",
            )
        else:
            st.button(
                "⬇️ Download Card (PNG)",
                disabled=True,
                use_container_width=True,
                help="Card image generation is unavailable.",
            )

    # 2. QR code PNG
    vcard = build_vcard(user)
    qr_bytes = make_qr_png(vcard, size=10, border=2)
    with c2:
        if qr_bytes:
            st.download_button(
                label="⬇️ Download QR Code (PNG)",
                data=qr_bytes,
                file_name=f"contact_qr_{_safe_filename(user.get('full_name', ''))}.png",
                mime="image/png",
                use_container_width=True,
                help="Download the QR code that encodes your contact info.",
            )
        else:
            st.button(
                "⬇️ Download QR Code (PNG)",
                disabled=True,
                use_container_width=True,
                help="Add `qrcode[pil]` to requirements.txt to enable QR codes.",
            )

    # 3. Show QR inline
    with c3:
        if qr_bytes:
            st.markdown(
                f"""
                <div style="display:flex;flex-direction:column;align-items:center;gap:4px;">
                    <img src="data:image/png;base64,{base64.b64encode(qr_bytes).decode()}"
                         style="width:88px;height:88px;border:1px solid #e2e8f0;border-radius:6px;" />
                    <span style="font-size:0.65rem;color:#64748b;">Scan to save contact</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("📦 `qrcode[pil]` not installed. Add it to `requirements.txt` to enable QR codes.")


# -----------------------------------------------------------------------
# Optional: also export a vCard file directly
# -----------------------------------------------------------------------
def make_vcard_file(user: dict) -> bytes:
    """Return the vCard as a downloadable .vcf file (raw bytes)."""
    return build_vcard(user).encode("utf-8")
