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
            f'style="width:130px;height:130px;border-radius:50%;object-fit:cover;'
            f'border:4px solid #ffffff;box-shadow:0 2px 12px rgba(0,0,0,0.10);" />'
        )
    else:
        # Initials disc
        initials = "".join(p[0].upper() for p in name.split()[:2] if p) or "?"
        avatar_html = (
            f'<div style="width:130px;height:130px;border-radius:50%;'
            f'background:linear-gradient(135deg,#dbeafe 0%,#bfdbfe 100%);'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:3.2rem;font-weight:700;color:#475569;'
            f'border:4px solid #ffffff;box-shadow:0 2px 12px rgba(0,0,0,0.10);">'
            f'{initials}</div>'
        )

    # Contact info rows.
    # KEY FIX: don't force uppercase on phone/email — it makes them wrap
    # at every special character. Use a smaller font, ``overflow-wrap:
    # anywhere`` so long strings break gracefully, and ``min-width:0``
    # on the flex child so the column actually shrinks.
    def _row(icon, text, *, uppercase=False, font_size="0.85rem"):
        ls = "0.04em" if uppercase else "0"
        transform = "uppercase" if uppercase else "none"
        weight = "600" if uppercase else "500"
        return (
            f'<div style="display:flex;align-items:flex-start;gap:10px;'
            f'margin-bottom:10px;font-size:{font_size};color:#1f2937;line-height:1.4;'
            f'min-width:0;">'
            f'<div style="flex:0 0 20px;font-size:1rem;line-height:1.2;'
            f'display:flex;align-items:center;justify-content:center;'
            f'width:20px;height:20px;color:#334155;">{icon}</div>'
            f'<div style="flex:1;min-width:0;text-transform:{transform};'
            f'letter-spacing:{ls};font-weight:{weight};'
            f'overflow-wrap:anywhere;word-break:normal;">{text}</div></div>'
        )

    rows_html = ""
    # Address — uppercase is fine because it's plain words
    if location and location != "—":
        rows_html += _row("🏠", location, uppercase=True, font_size="0.78rem")
    # Phone — keep as typed, no uppercase (so it doesn't break)
    if phone and phone != "—":
        rows_html += _row("📞", phone, font_size="0.88rem")
    # Email — keep as typed, lowercase
    if email and email != "—":
        rows_html += _row("✉️", email, font_size="0.82rem")
    # Instagram — display as "@handle" without forcing uppercase (so the @ survives)
    if instagram:
        ig = (instagram.lstrip("@")
                       .replace("https://instagram.com/", "")
                       .replace("http://instagram.com/", "")
                       .replace("instagram.com/", ""))
        if ig:
            rows_html += _row("📷", f"@{ig}", font_size="0.85rem")
    if facebook:
        fb = (facebook.lstrip("@")
                       .replace("https://facebook.com/", "")
                       .replace("https://www.facebook.com/", "")
                       .replace("http://facebook.com/", "")
                       .replace("facebook.com/", ""))
        if fb:
            rows_html += _row("📘", f"@{fb}", font_size="0.85rem")

    return f"""
    <div style="
        max-width: 720px;
        margin: 1rem auto;
        background: #ffffff;
        border-radius: 16px;
        box-shadow: 0 10px 36px rgba(0,0,0,0.14);
        padding: 24px 28px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        display: flex;
        gap: 0;
        align-items: stretch;
        background-image:
            linear-gradient(180deg, #fdfdfb 0%, #f6f4ef 100%);
    ">
        <div style="
            flex: 0 0 38%;
            min-width: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding-right: 20px;
            text-align: center;
        ">
            {avatar_html}
            <div style="
                margin-top: 16px;
                font-size: 1.3rem;
                font-weight: 700;
                color: #1e293b;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                line-height: 1.2;
                word-break: break-word;
                max-width: 100%;
            ">{name}</div>
            <div style="
                margin-top: 4px;
                font-size: 0.72rem;
                color: #64748b;
                letter-spacing: 0.2em;
                text-transform: uppercase;
            ">{title or role or 'Member'}</div>
        </div>
        <div style="
            flex: 0 0 1px;
            background: linear-gradient(180deg, transparent 0%, #cbd5e1 20%, #cbd5e1 80%, transparent 100%);
            margin: 0 16px;
        "></div>
        <div style="
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding-left: 8px;
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
      * Live HTML preview of the card (no QR — the QR is shown
        separately below the card so it's scannable on its own)
      * Scannable QR code panel with caption
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
    # The QR encodes the public URL (so scanning opens the card online,
    # no login required)
    qr_data = public_url if public_url else vcard_str

    # Render the live card preview (NO QR on the card itself)
    from utils.ui import _html
    _html(_build_card_preview_html("", user_for_display))

    # ── Scannable QR code — shown SEPARATELY below the card ─────
    _render_inline_qr(qr_data)

    # Download buttons
    _render_downloads(user_for_display, vcard_str, qr_data)


def _render_inline_qr(qr_data: str) -> None:
    """Render a scannable QR code panel below the business card.

    The QR is displayed on its own row, not embedded in the card, so
    it can be easily scanned with a phone. Below the QR we show a
    short instruction ("Point your phone camera to scan").
    """
    if not qr_data:
        return
    qr_bytes = make_qr_png(qr_data, size=10, border=2)
    if not qr_bytes:
        st.warning(
            "⚠️ QR code generation is unavailable. "
            "Add `qrcode` and `Pillow` to requirements.txt and restart."
        )
        return

    qr_b64 = base64.b64encode(qr_bytes).decode()

    from utils.ui import _html
    _html(f"""
    <div style="
        max-width: 720px;
        margin: 0 auto 1rem auto;
        background: #ffffff;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.10);
        padding: 20px 24px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        display: flex;
        align-items: center;
        gap: 22px;
        background-image:
            linear-gradient(180deg, #f0fdf4 0%, #ecfdf5 100%);
    ">
        <div style="
            flex: 0 0 auto;
            background: #ffffff;
            padding: 10px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            border: 2px solid #10b981;
        ">
            <img src="data:image/png;base64,{qr_b64}"
                 style="width:140px;height:140px;display:block;" />
        </div>
        <div style="flex:1;min-width:0;">
            <div style="
                font-size: 0.7rem;
                font-weight: 700;
                color: #047857;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                margin-bottom: 6px;
            ">📱 Scan to view online</div>
            <div style="
                font-size: 1.05rem;
                font-weight: 700;
                color: #0f172a;
                margin-bottom: 4px;
                line-height: 1.3;
            ">Open this card on your phone</div>
            <div style="
                font-size: 0.82rem;
                color: #475569;
                line-height: 1.4;
            ">
                Point your phone's camera at the QR code, or share the
                link above. No login required — anyone can see your card.
            </div>
        </div>
    </div>
    """)


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


def _render_downloads(user: dict, vcard_str: str, qr_data: str) -> None:
    """Render the download buttons.

    Args:
        user: the user dict
        vcard_str: the vCard 3.0 string (for the .vcf download)
        qr_data: the string the QR encodes (usually the public URL)
    """
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

    # 2. QR code PNG (separate, framed, with "SCAN TO VIEW CARD" label)
    with c2:
        qr_png = None
        try:
            from utils.card_image import render_qr_only_png
            qr_png = render_qr_only_png(qr_data or vcard_str)
        except Exception:
            # Fall back to the raw (unframed) QR bytes
            qr_png = make_qr_png(qr_data or vcard_str)
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
