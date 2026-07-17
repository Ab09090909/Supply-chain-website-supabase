"""
Business Card + QR Code module.

Renders a beautiful digital business card and generates a QR code that,
when scanned, opens the user's public business card page online.

Layout
------
The card matches the user's reference design — a **horizontal layout**
with the profile photo on the left and contact info on the right,
separated by a thin vertical line. The QR code is generated separately
(downloadable on its own) and is NOT embedded in the card.

    ┌──────────────────────────────────────────────────┐
    │   ┌────────┐   │  🏠  12 Your Business Road       │
    │   │  PHOTO │   │  City, State                    │
    │   └────────┘   │  55555                          │
    │                │  📞  555-555-5555               │
    │   NAME         │  ✉️  mail@emailaddress.com       │
    │   title        │  📷  your_instagram              │
    │                │  📘  your_facebook               │
    └──────────────────────────────────────────────────┘
"""
from __future__ import annotations

import base64
import hashlib
import io
import re
import urllib.request
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
# Avatar URL helper (Gravatar fallback)
# -----------------------------------------------------------------------
def _avatar_data_url(user: dict) -> str:
    """Return a data: URL for the user's avatar, or '' if unavailable.

    Tries the user's ``avatar_url`` first, then falls back to Gravatar
    (using the email's MD5). Returns '' if neither is reachable — the
    HTML preview will then show a coloured initials disc.
    """
    avatar_url = (user.get("avatar_url") or "").strip()
    email = (user.get("email") or "").strip().lower()
    if avatar_url.startswith(("http://", "https://")):
        try:
            req = urllib.request.Request(
                avatar_url,
                headers={"User-Agent": "Mozilla/5.0 EthioChain/1.0"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = resp.read()
            b64 = base64.b64encode(data).decode()
            return f"data:image/jpeg;base64,{b64}"
        except Exception:
            pass
    if email:
        try:
            digest = hashlib.md5(email.encode("utf-8")).hexdigest()
            grav = f"https://www.gravatar.com/avatar/{digest}?d=404&s=200"
            req = urllib.request.Request(
                grav, headers={"User-Agent": "Mozilla/5.0 EthioChain/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = resp.read()
            b64 = base64.b64encode(data).decode()
            return f"data:image/jpeg;base64,{b64}"
        except Exception:
            pass
    return ""


# -----------------------------------------------------------------------
# Inline card preview — HORIZONTAL layout matching the reference image
# -----------------------------------------------------------------------
def _build_card_preview_html(qr_png_b64: str, user: dict) -> str:
    """Build an HTML preview of the business card matching the reference:
    profile photo on the left, contact info on the right, vertical
    divider between them. The QR is NOT embedded in this card — the
    user downloads it separately.
    """
    name = (user.get("full_name") or "Your Name").strip()
    role = (user.get("role") or "").strip()
    title = (user.get("title") or role or "Member").strip()
    phone = (user.get("phone") or "—").strip()
    email = (user.get("email") or "—").strip()
    location = (user.get("location") or "—").strip()
    instagram = (user.get("instagram") or "").strip()
    facebook = (user.get("facebook") or "").strip()

    # Avatar (data URL or initials)
    avatar = _avatar_data_url(user)
    if avatar:
        avatar_html = (
            f'<img src="{avatar}" '
            f'style="width:140px;height:140px;border-radius:50%;object-fit:cover;'
            f'border:4px solid #ffffff;box-shadow:0 2px 12px rgba(0,0,0,0.10);" />'
        )
    else:
        # Initials disc
        initials = "".join(p[0].upper() for p in name.split()[:2] if p) or "?"
        avatar_html = (
            f'<div style="width:140px;height:140px;border-radius:50%;'
            f'background:linear-gradient(135deg,#dbeafe 0%,#bfdbfe 100%);'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:3.4rem;font-weight:700;color:#475569;'
            f'border:4px solid #ffffff;box-shadow:0 2px 12px rgba(0,0,0,0.10);">'
            f'{initials}</div>'
        )

    # Contact info rows
    def _row(icon, text):
        return (
            f'<div style="display:flex;align-items:flex-start;gap:14px;'
            f'margin-bottom:14px;font-size:0.95rem;color:#1f2937;line-height:1.35;">'
            f'<div style="flex:0 0 24px;font-size:1.1rem;line-height:1.2;'
            f'display:flex;align-items:center;justify-content:center;'
            f'width:24px;height:24px;color:#334155;">{icon}</div>'
            f'<div style="flex:1;text-transform:uppercase;letter-spacing:0.03em;'
            f'word-break:break-word;">{text}</div></div>'
        )

    rows_html = ""
    if location and location != "—":
        rows_html += _row("🏠", location)
    if phone and phone != "—":
        rows_html += _row("📞", phone)
    if email and email != "—":
        rows_html += _row("✉️", email)
    if instagram:
        ig = (instagram.lstrip("@")
                       .replace("https://instagram.com/", "")
                       .replace("http://instagram.com/", "")
                       .replace("instagram.com/", ""))
        if ig:
            rows_html += _row("📷", ig)
    if facebook:
        fb = (facebook.lstrip("@")
                       .replace("https://facebook.com/", "")
                       .replace("https://www.facebook.com/", "")
                       .replace("http://facebook.com/", "")
                       .replace("facebook.com/", ""))
        if fb:
            rows_html += _row("📘", fb)

    return f"""
    <div style="
        max-width: 720px;
        margin: 1rem auto;
        background: #ffffff;
        border-radius: 16px;
        box-shadow: 0 10px 36px rgba(0,0,0,0.14);
        padding: 28px 32px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        display: flex;
        gap: 0;
        align-items: stretch;
        background-image:
            linear-gradient(180deg, #fdfdfb 0%, #f6f4ef 100%);
    ">
        <div style="
            flex: 0 0 42%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding-right: 24px;
            text-align: center;
        ">
            {avatar_html}
            <div style="
                margin-top: 18px;
                font-size: 1.45rem;
                font-weight: 700;
                color: #1e293b;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            ">{name}</div>
            <div style="
                margin-top: 4px;
                font-size: 0.78rem;
                color: #64748b;
                letter-spacing: 0.22em;
                text-transform: uppercase;
            ">{title or role or 'Member'}</div>
        </div>
        <div style="
            flex: 0 0 1px;
            background: linear-gradient(180deg, transparent 0%, #cbd5e1 20%, #cbd5e1 80%, transparent 100%);
            margin: 0 18px;
        "></div>
        <div style="
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding-left: 12px;
        ">
            {rows_html}
        </div>
    </div>
    <div style="
        max-width: 720px;
        margin: 0 auto 1rem auto;
        text-align: right;
        font-size: 0.72rem;
        color: #94a3b8;
    ">
        <span style="
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 3px 10px;
            border-radius: 8px;
            font-weight: 700;
            letter-spacing: 0.06em;
        ">EthioChain</span>
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

    # 1. Card PNG (no QR embedded — it's a separate download)
    with c1:
        png_bytes = None
        try:
            from utils.card_image import render_card_to_png
            png_bytes = render_card_to_png(user)
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

    # 2. QR code PNG (separate, framed, with "SCAN ME" label)
    with c2:
        qr_png = None
        try:
            from utils.card_image import render_qr_only_png
            public_url = build_public_card_url(user)
            qr_png = render_qr_only_png(public_url or vcard_str)
        except Exception:
            qr_png = qr_bytes  # fall back to raw QR
        if qr_png:
            st.download_button(
                label="⬇️ Download QR (PNG)",
                data=qr_png,
                file_name=f"qr_{safe_name}.png",
                mime="image/png",
                use_container_width=True,
                help="Download the QR code separately (encodes your public card link).",
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
