"""
Business Card + QR Code module.

Renders a beautiful digital business card (matching the design from
the user's reference image) and generates a downloadable QR code that,
when scanned, opens the user's contact info on the scanner's phone.

Layout
------
The card matches the user's reference design:
    ┌──────────────────────────────────────────────────────┐
    │     ┌─────────┐     │   ABRAHAM SMITH               │
    │     │         │     │                               │
    │     │   QR    │     │   SENIOR PRODUCER              │
    │     │         │     │                               │
    │     └─────────┘     │   🏠  12 Your Business Road  │
    │                     │   📞  +251 911 123 456        │
    │      ABRAHAM SMITH   │   ✉️  abraham@gmail.com       │
    │                      │   📷  ABRAHAM                │
    │                      │   📘  ABRAHAM.SMITH           │
    └──────────────────────────────────────────────────────┘

The QR code is on the LEFT (the main feature), contact details on the
RIGHT. When scanned with a phone camera, the QR imports the contact
into the phone's address book.

Features
--------
* QR code is generated locally (no network call) and encoded as a
  vCard so most phones automatically offer to "Add to Contacts" on scan.
* Both the QR code and the full business card can be downloaded as
  PNG files — fully offline.
* The QR code uses the high error-correction level (30%) so it works
  even when printed small or partially obscured.

Usage
-----
    from utils.business_card import render_business_card
    render_business_card(user_dict)  # user_dict has full_name, email,
                                       # phone, location, avatar_url, etc.
"""
from __future__ import annotations

import base64
import io
import re
from typing import Optional

import streamlit as st


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
def _make_qr_image(data: str, size: int = 12, border: int = 2):
    """Generate a QR code as a PIL Image. Returns None if qrcode isn't installed.

    We always use the PIL image factory (qrcode.image.pil.PilImage) so we
    don't need a separate pypng dependency. If qrcode[pil] is installed
    (which pulls in Pillow automatically), this will work.
    """
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
        img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)
        return img
    except Exception:
        return None


def make_qr_png(data: str, size: int = 10, border: int = 2) -> Optional[bytes]:
    """Generate a QR code as PNG bytes. Returns None if qrcode isn't installed.

    Args:
        data:   the string to encode (usually a vCard)
        size:   pixel size of each "module" (square)
        border: number of white modules around the edge
    """
    img = _make_qr_image(data, size=size, border=border)
    if img is None:
        return None
    # Convert to bytes
    buf = io.BytesIO()
    try:
        img.save(buf, format="PNG")
    except Exception:
        # If image is not a PIL Image, try saving to a temp file
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tmp = tf.name
        try:
            img.save(tmp)
            with open(tmp, "rb") as f:
                buf.write(f.read())
        finally:
            try: os.unlink(tmp)
            except Exception: pass
    return buf.getvalue()


# -----------------------------------------------------------------------
# Inline card preview — shown above the download buttons
# -----------------------------------------------------------------------
def _build_card_preview_html(qr_png_b64: str, user: dict) -> str:
    """Build an HTML preview of the business card, matching the user's
    reference design. The QR is shown on the LEFT, contact info on the RIGHT.
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
        qr_html = f'<img src="data:image/png;base64,{qr_png_b64}" style="width:200px;height:200px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.1);" />'
    else:
        qr_html = '<div style="width:200px;height:200px;border-radius:8px;background:#fee2e2;display:flex;align-items:center;justify-content:center;color:#991b1b;font-size:0.8rem;text-align:center;padding:8px;">QR unavailable<br>install qrcode</div>'

    social_rows = ""
    if instagram:
        ig = instagram.lstrip("@")
        social_rows += f"""
        <div style="display:flex;align-items:center;gap:8px;margin-top:8px;font-size:0.85rem;color:#1f2937;">
            <span style="font-size:1.05rem;">📷</span>
            <span style="text-transform:uppercase;letter-spacing:0.04em;font-weight:500;">{ig}</span>
        </div>"""
    if facebook:
        fb = facebook.lstrip("@")
        social_rows += f"""
        <div style="display:flex;align-items:center;gap:8px;margin-top:8px;font-size:0.85rem;color:#1f2937;">
            <span style="font-size:1.05rem;">📘</span>
            <span style="text-transform:uppercase;letter-spacing:0.04em;font-weight:500;">{fb}</span>
        </div>"""

    return f"""
    <div style="
        max-width: 580px;
        margin: 1rem auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 8px 28px rgba(0,0,0,0.12);
        padding: 24px 28px;
        display: grid;
        grid-template-columns: auto 1px 1fr;
        gap: 22px;
        align-items: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    ">
        <div style="display:flex;flex-direction:column;align-items:center;gap:8px;min-width:200px;">
            {qr_html}
            <div style="background:#10b981;color:white;font-size:0.6rem;font-weight:700;letter-spacing:0.06em;padding:3px 10px;border-radius:10px;margin-top:-4px;">SCAN TO SAVE</div>
            <div style="text-align:center;margin-top:8px;">
                <div style="font-size:1.1rem;font-weight:700;color:#0f172a;letter-spacing:0.05em;text-transform:uppercase;">{name}</div>
                <div style="font-size:0.7rem;color:#6b7280;letter-spacing:0.18em;text-transform:uppercase;margin-top:3px;">{title or role or 'Member'}</div>
            </div>
        </div>
        <div style="width:1px;align-self:stretch;background:linear-gradient(180deg,transparent 0%,#cbd5e1 20%,#cbd5e1 80%,transparent 100%);"></div>
        <div style="display:flex;flex-direction:column;gap:6px;">
            <div style="display:flex;align-items:flex-start;gap:10px;font-size:0.88rem;color:#1f2937;">
                <span style="font-size:1rem;line-height:1.2;">🏠</span>
                <span style="text-transform:uppercase;letter-spacing:0.03em;font-weight:500;line-height:1.35;">{location}</span>
            </div>
            <div style="display:flex;align-items:center;gap:10px;margin-top:4px;font-size:0.88rem;color:#1f2937;">
                <span style="font-size:1rem;">📞</span>
                <span style="font-weight:500;">{phone}</span>
            </div>
            <div style="display:flex;align-items:center;gap:10px;margin-top:4px;font-size:0.8rem;color:#1f2937;word-break:break-all;">
                <span style="font-size:1rem;">✉️</span>
                <span style="text-transform:lowercase;font-weight:500;">{email}</span>
            </div>
            {social_rows}
        </div>
    </div>
    """


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------
def _safe_filename(text: str) -> str:
    """Turn a user-provided name into something safe for a filename."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", (text or "user").strip())
    return s.strip("_") or "user"


def render_business_card(user: dict) -> None:
    """Render the business card UI + QR code + download buttons.

    The user can:
      * See their digital business card (with QR on the left)
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

    # Build the vCard once, then use it for both the preview and the QR
    user_for_display = dict(user)
    user_for_display["instagram"] = st.session_state.get("bc_instagram", user.get("instagram") or "")
    user_for_display["facebook"]   = st.session_state.get("bc_facebook",   user.get("facebook")   or "")

    vcard_str = build_vcard(user_for_display)
    qr_bytes = make_qr_png(vcard_str, size=10, border=2)

    # Render the card preview (HTML with embedded QR)
    if qr_bytes:
        qr_b64 = base64.b64encode(qr_bytes).decode()
    else:
        qr_b64 = ""

    from utils.ui import _html
    _html(_build_card_preview_html(qr_b64, user_for_display))

    # Show a warning if the QR couldn't be generated
    if not qr_bytes:
        st.warning(
            "⚠️ QR code generation is unavailable. "
            "Add `qrcode` and `Pillow` to requirements.txt and restart the app."
        )

    # Download buttons
    _render_downloads(user_for_display, vcard_str, qr_bytes)


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


def _render_downloads(user: dict, vcard_str: str, qr_bytes: Optional[bytes]) -> None:
    """Render the download buttons: card PNG + QR code PNG.

    Both are best-effort — if Pillow or qrcode aren't available, the
    corresponding button is disabled (and a warning is already shown
    above). The .vcf download always works (no deps needed).
    """
    st.markdown("")
    c1, c2, c3 = st.columns(3)

    safe_name = _safe_filename(user.get("full_name", ""))

    # 1. Card PNG (uses PIL)
    with c1:
        png_bytes = None
        try:
            from utils.card_image import render_card_to_png
            png_bytes = render_card_to_png(user, vcard=vcard_str)
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
                help="Pillow isn't installed. Add it to requirements.txt.",
            )

    # 2. QR code PNG
    with c2:
        if qr_bytes:
            st.download_button(
                label="⬇️ Download QR (PNG)",
                data=qr_bytes,
                file_name=f"contact_qr_{safe_name}.png",
                mime="image/png",
                use_container_width=True,
                help="Download the QR code that encodes your contact info.",
            )
        else:
            st.button(
                "⬇️ Download QR (PNG)",
                disabled=True,
                use_container_width=True,
                help="qrcode isn't installed. Add it to requirements.txt.",
            )

    # 3. vCard file (always works — no deps)
    with c3:
        vcf_bytes = vcard_str.encode("utf-8")
        st.download_button(
            label="⬇️ Download vCard (.vcf)",
            data=vcf_bytes,
            file_name=f"contact_{safe_name}.vcf",
            mime="text/vcard",
            use_container_width=True,
            help="Download a .vcf file you can import into any contacts app.",
        )


# -----------------------------------------------------------------------
# Optional: also export a vCard file directly
# -----------------------------------------------------------------------
def make_vcard_file(user: dict) -> bytes:
    """Return the vCard as a downloadable .vcf file (raw bytes)."""
    return build_vcard(user).encode("utf-8")
