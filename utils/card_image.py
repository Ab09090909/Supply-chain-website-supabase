"""
Render the digital business card to a PNG image using Pillow (PIL).

This is the "offline" renderer — no headless browser, no external
service. We use Pillow's ``ImageDraw`` to paint the card on a 1080x540
canvas (matching the 2:1 aspect ratio of the user's reference design),
then return the PNG bytes for download.

The card layout follows the user's reference design:
    ┌──────────────────────────────────────────────────────┐
    │                                                      │
    │     ┌─────────┐     │   ABRAHAM SMITH               │
    │     │         │     │                               │
    │     │   QR    │     │   PRODUCER                    │
    │     │         │     │                               │
    │     └─────────┘     │   🏠  12 Your Business Road  │
    │                     │   📞  +251 911 123 456        │
    │      ABRAHAM SMITH   │   ✉️  abraham@gmail.com       │
    │                      │   📷  ABRAHAM                │
    │                      │   📘  ABRAHAM.SMITH           │
    │                      │                               │
    └──────────────────────────────────────────────────────┘

The QR code is the main feature on the left — when scanned it imports
all the contact info into the scanner's phone. The right side shows
the same info as text so people can read it at a glance.

Why Pillow instead of HTML-to-image?
  * No system dependencies (no Chromium, no GTK)
  * Fast — runs in milliseconds
  * Works identically on Streamlit Cloud, local Linux/macOS/Windows
  * The user said "offline" — Pillow is purely offline
"""
from __future__ import annotations

import io
from typing import Optional

# Pillow is part of the `qrcode[pil]` extra we add in requirements.txt
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    _PIL_OK = True
except Exception:
    _PIL_OK = False


# -----------------------------------------------------------------------
# Font loading — try a few common paths so the card looks good on
# any OS (Linux, macOS, Windows)
# -----------------------------------------------------------------------
_FONT_REGULAR_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Georgia.ttf",
    "C:/Windows/Fonts/georgia.ttf",
    "C:/Windows/Fonts/arial.ttf",
]

_FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/Library/Fonts/Georgia Bold.ttf",
    "C:/Windows/Fonts/georgiab.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _find_font(candidates, size: int):
    """Return the first existing font in ``candidates``, scaled to ``size``."""
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: int) -> list:
    """Wrap text to fit within ``max_width`` pixels using the given font."""
    if not text:
        return []
    words = text.split()
    lines, current = [], ""
    for w in words:
        trial = (current + " " + w).strip() if current else w
        bbox = draw.textbbox((0, 0), trial, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            if draw.textbbox((0, 0), w, font=font)[2] > max_width:
                chunk = ""
                for ch in w:
                    if draw.textbbox((0, 0), chunk + ch, font=font)[2] > max_width and chunk:
                        lines.append(chunk)
                        chunk = ch
                    else:
                        chunk += ch
                current = chunk
            else:
                current = w
    if current:
        lines.append(current)
    return lines


def _fetch_avatar_bytes(url: str) -> Optional[bytes]:
    """Best-effort fetch of the avatar image. Returns None on any failure."""
    if not url:
        return None
    try:
        import requests
        r = requests.get(url, timeout=4)
        if r.ok and r.content:
            return r.content
    except Exception:
        pass
    return None


def _generate_qr_png(data: str, size: int = 540) -> Optional[Image.Image]:
    """Generate a QR code as a PIL Image (or None if qrcode isn't installed).

    Returns a square ``Image`` with the QR pattern on a white background.
    Uses the PIL image factory so we don't depend on pypng.
    """
    try:
        import qrcode
        from qrcode.image.pil import PilImage
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=8,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white",
                            image_factory=PilImage)
        # qrcode's PIL factory returns a PIL Image, but it may be in
        # 'L' (luminance) mode — convert to 'RGB' for our use.
        if hasattr(img, "convert"):
            return img.convert("RGB")
        # Fallback for non-PIL backends: save via tempfile
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tmp_path = tf.name
        try:
            img.save(tmp_path)
            return Image.open(tmp_path).convert("RGB")
        finally:
            try: os.unlink(tmp_path)
            except Exception: pass
        return None
    except Exception:
        return None


# -----------------------------------------------------------------------
# Geometric icons — Pillow fonts don't include emoji glyphs
# -----------------------------------------------------------------------
def _draw_icon(draw, x, y, kind, size=18, color=(75, 85, 99)):
    """Draw a small monochrome icon using geometric shapes."""
    if kind == "home":
        draw.polygon(
            [(x, y + size // 2), (x + size // 2, y), (x + size, y + size // 2)],
            outline=color, width=2,
        )
        draw.rectangle(
            [x + size // 6, y + size // 2, x + size - size // 6, y + size],
            outline=color, width=2,
        )
    elif kind == "phone":
        draw.rounded_rectangle(
            [x, y + 2, x + size - 2, y + size - 2],
            radius=4, outline=color, width=2,
        )
    elif kind == "email":
        draw.rectangle(
            [x, y + 2, x + size, y + size - 2],
            outline=color, width=2,
        )
        draw.line(
            [(x, y + 2), (x + size // 2, y + size // 2), (x + size, y + 2)],
            fill=color, width=2,
        )
    elif kind == "instagram":
        draw.rounded_rectangle(
            [x, y, x + size, y + size],
            radius=4, outline=color, width=2,
        )
        draw.ellipse(
            [x + size // 4, y + size // 4, x + 3 * size // 4, y + 3 * size // 4],
            outline=color, width=2,
        )
        draw.ellipse(
            [x + 3 * size // 4 - 2, y + 2, x + 3 * size // 4 + 2, y + 6],
            fill=color,
        )
    elif kind == "facebook":
        draw.ellipse(
            [x, y, x + size, y + size],
            outline=color, width=2,
        )
        f_x = x + size * 0.55
        f_y = y + size * 0.20
        draw.line([(f_x, f_y), (f_x, y + size * 0.85)], fill=color, width=2)
        draw.line(
            [(x + size * 0.35, y + size * 0.45), (f_x + 4, y + size * 0.45)],
            fill=color, width=2,
        )


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------
def render_card_to_png(user: dict, vcard: str = "", width: int = 1080, height: int = 540) -> Optional[bytes]:
    """Render the business card to a PNG byte string.

    Args:
        user:   the user dict (name, email, phone, etc.)
        vcard:  the vCard string to encode in the QR. If empty, we
                build it from ``user`` on the fly.
        width, height: canvas dimensions (default 1080x540 = 2:1)

    Returns ``None`` if Pillow isn't installed.
    """
    if not _PIL_OK:
        return None

    # ── User data ──────────────────────────────────────────
    name      = (user.get("full_name") or "Your Name").strip()
    role      = (user.get("role") or "").strip().capitalize()
    title     = (user.get("title") or role or "Member").strip()
    phone     = (user.get("phone") or "—").strip()
    email     = (user.get("email") or "—").strip()
    location  = (user.get("location") or "—").strip()
    instagram = (user.get("instagram") or "").strip()
    facebook  = (user.get("facebook") or "").strip()

    # Build vCard for the QR if not provided
    if not vcard:
        from utils.business_card import build_vcard
        vcard = build_vcard(user)

    # ── Card canvas ────────────────────────────────────────
    img = Image.new("RGB", (width, height), (255, 255, 255))

    # Subtle paper texture — faint horizontal banding
    texture = Image.new("RGB", (width, height), (252, 250, 246))
    for y in range(height):
        v = 248 + (y % 2) * 2
        for x in range(0, width, 8):
            for dx in range(min(8, width - x)):
                texture.putpixel((x + dx, y), (v, v - 2, v - 4))

    # Vignette
    vignette = Image.new("L", (width, height), 0)
    vd = ImageDraw.Draw(vignette)
    vd.rectangle((0, 0, width, height), fill=80)
    vd.rectangle((40, 40, width - 40, height - 40), fill=140)
    vd.rectangle((80, 80, width - 80, height - 80), fill=220)
    vignette = vignette.filter(ImageFilter.GaussianBlur(40))
    img = Image.composite(img, texture, vignette)

    draw = ImageDraw.Draw(img)

    # ── Fonts ──────────────────────────────────────────────
    f_name      = _find_font(_FONT_BOLD_CANDIDATES,    36)
    f_title     = _find_font(_FONT_REGULAR_CANDIDATES, 18)
    f_body      = _find_font(_FONT_REGULAR_CANDIDATES, 22)
    f_body_bold = _find_font(_FONT_BOLD_CANDIDATES,    22)
    f_body_sm   = _find_font(_FONT_REGULAR_CANDIDATES, 19)
    f_qr_label  = _find_font(_FONT_BOLD_CANDIDATES,    14)

    # ── Layout: 2 columns ──────────────────────────────────
    # Left  ~46%: QR code + name + title
    # Right ~54%: contact details
    margin = 50
    col_left_x = margin
    col_left_w = 420
    col_divider_x = col_left_x + col_left_w
    col_right_x = col_divider_x + 32
    col_right_w = width - col_right_x - margin

    # ── QR CODE on the LEFT ────────────────────────────────
    qr_size = 320
    qr_x = col_left_x + (col_left_w - qr_size) // 2
    qr_y = 60
    qr_box = (qr_x, qr_y, qr_x + qr_size, qr_y + qr_size)

    qr_img = _generate_qr_png(vcard, size=qr_size)
    if qr_img is not None:
        # Resize the QR to exactly qr_size × qr_size
        qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
        # Add a thin border around the QR
        border = 8
        bordered = Image.new("RGB",
                              (qr_size + 2 * border, qr_size + 2 * border),
                              (255, 255, 255))
        bordered.paste(qr_img, (border, border))
        img.paste(bordered, qr_box[:2])
        # "SCAN ME" label under the QR
        scan_label = "SCAN TO SAVE CONTACT"
        sl_bbox = draw.textbbox((0, 0), scan_label, font=f_qr_label)
        sl_w = sl_bbox[2] - sl_bbox[0]
        sl_x = qr_x + (qr_size - sl_w) // 2
        sl_y = qr_y + qr_size + 14
        # Subtle pill background
        pad_x, pad_y = 12, 5
        pill_w = sl_w + 2 * pad_x
        pill_h = (sl_bbox[3] - sl_bbox[1]) + 2 * pad_y
        draw.rounded_rectangle(
            [sl_x - pad_x, sl_y - pad_y,
             sl_x - pad_x + pill_w, sl_y - pad_y + pill_h],
            radius=8, fill=(16, 185, 129),
        )
        draw.text((sl_x, sl_y), scan_label, font=f_qr_label, fill=(255, 255, 255))
    else:
        # Fallback: show a placeholder if qrcode isn't installed
        draw.rounded_rectangle(
            list(qr_box), radius=10, outline=(180, 180, 180), width=2,
            fill=(245, 245, 245),
        )
        msg = "QR unavailable\ninstall qrcode[pil]"
        f_fb = _find_font(_FONT_BOLD_CANDIDATES, 18)
        for li, line in enumerate(msg.split("\n")):
            bb = draw.textbbox((0, 0), line, font=f_fb)
            tw = bb[2] - bb[0]
            draw.text(
                (qr_x + (qr_size - tw) // 2,
                 qr_y + qr_size // 2 - 20 + li * 26),
                line, font=f_fb, fill=(120, 120, 120),
            )

    # ── Name + title (below the QR, centered) ─────────────
    name_y = qr_box[3] + 56  # extra space for the SCAN ME pill
    name_bbox = draw.textbbox((0, 0), name.upper(), font=f_name)
    name_w = name_bbox[2] - name_bbox[0]
    name_x = col_left_x + (col_left_w - name_w) // 2
    draw.text((name_x, name_y), name.upper(), font=f_name, fill=(15, 23, 42))

    title_y = name_y + 48
    title_bbox = draw.textbbox((0, 0), title.upper(), font=f_title)
    title_w = title_bbox[2] - title_bbox[0]
    title_x = col_left_x + (col_left_w - title_w) // 2
    draw.text((title_x, title_y), title.upper(), font=f_title, fill=(107, 114, 128))

    # ── Divider line ──────────────────────────────────────
    div_top = 60
    div_bot = height - 60
    draw.line(
        [(col_divider_x, div_top), (col_divider_x, div_bot)],
        fill=(203, 213, 225), width=1,
    )

    # ── Contact info (right column) ───────────────────────
    info_x = col_right_x
    info_y_start = 90
    icon_size = 24
    icon_gap = 18

    def _draw_row(y, kind, text, font, fill=(31, 41, 55)):
        _draw_icon(draw, info_x, y, kind, size=icon_size, color=(75, 85, 99))
        text_x = info_x + icon_size + icon_gap
        max_text_w = col_right_w - icon_size - icon_gap
        lines = _wrap_text(draw, text, font, max_text_w)
        for li, line in enumerate(lines):
            draw.text((text_x, y + 2 + li * 26), line, font=font, fill=fill)
        return max(icon_size, len(lines) * 26 + 4)

    y = info_y_start
    y += _draw_row(y, "home", location.upper(), f_body_bold)
    y += 18
    y += _draw_row(y, "phone", phone, f_body_bold)
    y += 18
    y += _draw_row(y, "email", email, f_body_sm, fill=(31, 41, 55))
    if instagram:
        ig = (instagram.lstrip("@")
                       .replace("https://instagram.com/", "")
                       .replace("http://instagram.com/", ""))
        y += 18 + _draw_row(y, "instagram", ig.upper(), f_body_bold)
    if facebook:
        fb = (facebook.lstrip("@")
                       .replace("https://facebook.com/", "")
                       .replace("https://www.facebook.com/", "")
                       .replace("http://facebook.com/", ""))
        y += 18 + _draw_row(y, "facebook", fb.upper(), f_body_bold)

    # ── Save and return ──────────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()
