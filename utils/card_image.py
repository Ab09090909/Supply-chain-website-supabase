"""
Render the digital business card to a PNG image using Pillow (PIL).

The card matches the user's reference design — a **horizontal layout**
with the profile photo on the left and contact info on the right,
separated by a thin vertical line. The QR code is rendered SEPARATELY
(downloadable on its own) — the card itself has no QR, keeping it clean
and scannable for human reading.

Layout (matching the reference image):
    ┌──────────────────────────────────────────────────┐
    │                                                  │
    │   ┌────────┐                                     │
    │   │        │   ┌─┐  12 Your Business Road        │
    │   │  PHOTO │   │H│  City, State                  │
    │   │        │   └─┘  55555                        │
    │   │        │                                     │
    │   └────────┘   ┌─┐  555-555-5555                 │
    │                │P│                                │
    │   NAME         └─┘                                │
    │   title/company┌─┐  mail@emailaddress.com         │
    │                │@│                                │
    │                └─┘                                │
    │                ┌─┐  your_instagram                │
    │                │I│                                │
    │                └─┘                                │
    │                ┌─┐  your_facebook                 │
    │                │f│                                │
    │                └─┘                                │
    └──────────────────────────────────────────────────┘

Why Pillow instead of HTML-to-image?
  * No system dependencies (no Chromium, no GTK)
  * Fast — runs in milliseconds
  * Works identically on Streamlit Cloud, local Linux/macOS/Windows
"""
from __future__ import annotations

import io
import math
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
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/Library/Fonts/Georgia.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/georgia.ttf",
]

_FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/Library/Fonts/Georgia Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/georgiab.ttf",
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


# -----------------------------------------------------------------------
# Avatar helpers
# -----------------------------------------------------------------------
def _draw_circular_avatar(target: Image.Image, cx: int, cy: int, radius: int,
                          user: dict):
    """Draw a circular profile photo on ``target`` centred at (cx, cy).

    Tries to download the user's avatar_url, fetches a Gravatar for their
    email, or falls back to the user's initials on a coloured disc.
    """
    import os
    import urllib.request
    import hashlib
    avatar_url = (user.get("avatar_url") or "").strip()
    email = (user.get("email") or "").strip().lower()

    img = None
    # 1) Try the user's avatar_url (only http(s) for safety)
    if avatar_url and avatar_url.startswith(("http://", "https://")):
        try:
            req = urllib.request.Request(
                avatar_url,
                headers={"User-Agent": "Mozilla/5.0 EthioChain/1.0"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = resp.read()
            from PIL import Image as _Img
            img = _Img.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            img = None

    # 2) Fall back to Gravatar (d=404 → we'll handle 404 ourselves)
    if img is None and email:
        try:
            digest = hashlib.md5(email.encode("utf-8")).hexdigest()
            grav = f"https://www.gravatar.com/avatar/{digest}?d=404&s=200"
            req = urllib.request.Request(
                grav, headers={"User-Agent": "Mozilla/5.0 EthioChain/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = resp.read()
            from PIL import Image as _Img
            img = _Img.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            img = None

    # 3) Fallback — initials disc
    if img is None:
        img = _initials_disc(user)

    # Crop to square, resize, mask to circle
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize(
        (radius * 2, radius * 2), Image.LANCZOS
    )
    # Build a circular alpha mask
    mask = Image.new("L", (radius * 2, radius * 2), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse((0, 0, radius * 2 - 1, radius * 2 - 1), fill=255)
    target.paste(img, (cx - radius, cy - radius), mask)


def _initials_disc(user: dict) -> Image.Image:
    """Build a 200x200 initials disc as a fallback avatar."""
    img = Image.new("RGB", (200, 200), (220, 230, 240))
    draw = ImageDraw.Draw(img)
    name = (user.get("full_name") or "?").strip()
    initials = "".join(p[0].upper() for p in name.split()[:2] if p) or "?"
    # Soft gradient
    for y in range(200):
        for x in range(0, 200, 4):
            t = (x + y) / 400
            r = int(180 + 30 * t)
            g = int(200 + 25 * t)
            b = int(220 + 20 * t)
            for dx in range(min(4, 200 - x)):
                img.putpixel((x + dx, y), (r, g, b))
    # Initials
    f = _find_font(_FONT_BOLD_CANDIDATES, 90)
    bbox = draw.textbbox((0, 0), initials, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((200 - tw) // 2 - bbox[0], (200 - th) // 2 - bbox[1]),
        initials, font=f, fill=(80, 90, 110),
    )
    return img


# -----------------------------------------------------------------------
# Geometric icons — Pillow fonts don't include emoji glyphs
# -----------------------------------------------------------------------
def _draw_icon(draw, x, y, kind, size=18, color=(60, 70, 85)):
    """Draw a small monochrome icon using geometric shapes."""
    if kind == "home":
        # Roof
        draw.polygon(
            [(x, y + size // 2), (x + size // 2, y), (x + size, y + size // 2)],
            outline=color, width=2,
        )
        # Body
        draw.rectangle(
            [x + size // 6, y + size // 2, x + size - size // 6, y + size],
            outline=color, width=2,
        )
        # Door
        draw.rectangle(
            [x + size // 2 - 2, y + 3 * size // 4,
             x + size // 2 + 2, y + size - 1],
            fill=color,
        )
    elif kind == "phone":
        # Rounded rectangle with a small "speaker" line
        draw.rounded_rectangle(
            [x, y + 1, x + size - 1, y + size - 1],
            radius=3, outline=color, width=2,
        )
        # diagonal line for handset
        draw.line(
            [(x + 3, y + 3), (x + size - 3, y + size - 3)],
            fill=color, width=1,
        )
    elif kind == "email":
        # Envelope rectangle + V shape
        draw.rectangle(
            [x, y + 2, x + size - 1, y + size - 2],
            outline=color, width=2,
        )
        draw.line(
            [(x, y + 2), (x + size // 2, y + size // 2 + 1),
             (x + size - 1, y + 2)],
            fill=color, width=2,
        )
    elif kind == "instagram":
        # Rounded square
        draw.rounded_rectangle(
            [x, y, x + size - 1, y + size - 1],
            radius=4, outline=color, width=2,
        )
        # Camera lens
        draw.ellipse(
            [x + size // 4, y + size // 4,
             x + 3 * size // 4 - 1, y + 3 * size // 4 - 1],
            outline=color, width=2,
        )
        # Flash dot
        draw.ellipse(
            [x + 3 * size // 4 - 3, y + 2, x + 3 * size // 4 + 1, y + 6],
            fill=color,
        )
    elif kind == "facebook":
        # Circle with f
        draw.ellipse(
            [x, y, x + size - 1, y + size - 1],
            outline=color, width=2,
        )
        f_x = x + size * 0.55
        f_y = y + size * 0.20
        draw.line([(f_x, f_y), (f_x, y + size * 0.85)], fill=color, width=2)
        draw.line(
            [(x + size * 0.30, y + size * 0.45), (f_x + 4, y + size * 0.45)],
            fill=color, width=2,
        )


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------
def render_card_to_png(
    user: dict,
    vcard: str = "",
    qr_data: str = "",
    width: int = 900,
    height: int = 540,
) -> Optional[bytes]:
    """Render the business card to a PNG byte string.

    Default is **900x540 (landscape)** — matching the reference design
    with photo on the left and contact info on the right.

    The QR code is intentionally NOT on the card. To share the card,
    download the QR separately (it encodes the public URL).

    Args:
        user:    the user dict (name, email, phone, etc.)
        vcard:   (unused — kept for backward compatibility)
        qr_data: (unused — kept for backward compatibility)
        width, height: canvas dimensions (default 900x540)

    Returns ``None`` if Pillow isn't installed.
    """
    if not _PIL_OK:
        return None

    # ── User data ──────────────────────────────────────────
    name      = (user.get("full_name") or "Your Name").strip()
    role      = (user.get("role") or "").strip().upper()
    title     = (user.get("title") or role or "MEMBER").strip()
    if title and title == title.upper() and not user.get("title"):
        # Don't shout the role — keep it Title Case for the card
        title = title.title()
    phone     = (user.get("phone") or "—").strip()
    email     = (user.get("email") or "—").strip()
    location  = (user.get("location") or "—").strip()
    instagram = (user.get("instagram") or "").strip()
    facebook  = (user.get("facebook") or "").strip()

    # ── Canvas ─────────────────────────────────────────────
    img = Image.new("RGB", (width, height), (245, 243, 238))
    draw = ImageDraw.Draw(img)

    # Subtle paper texture — very faint warm tint
    for y in range(0, height, 2):
        for x in range(0, width, 8):
            v = 248 + (y % 4) * 1
            for dx in range(min(8, width - x)):
                img.putpixel((x + dx, y), (v, v - 2, v - 5))

    # ── Card panel (white, with shadow) ────────────────────
    pad = 18
    panel_box = (pad, pad, width - pad, height - pad)
    # Drop shadow
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle((pad + 6, pad + 8, width - pad + 6, height - pad + 8),
                 fill=(0, 0, 0, 35))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    img.paste(shadow, (0, 0), shadow)
    img.paste((255, 255, 255), panel_box[:2] + (panel_box[2] - panel_box[0],
                                                  panel_box[3] - panel_box[1]))
    # Re-apply paper texture inside the panel
    for y in range(pad, height - pad, 2):
        for x in range(pad, width - pad, 8):
            v = 255 - ((y + x) % 3)
            for dx in range(min(8, width - pad - x)):
                img.putpixel((x + dx, y), (v, v, v - 1))

    draw = ImageDraw.Draw(img)

    # ── Fonts ──────────────────────────────────────────────
    f_name      = _find_font(_FONT_BOLD_CANDIDATES,    30)
    f_title     = _find_font(_FONT_REGULAR_CANDIDATES, 16)
    f_body      = _find_font(_FONT_REGULAR_CANDIDATES, 15)
    f_body_bold = _find_font(_FONT_REGULAR_CANDIDATES, 15)
    f_brand     = _find_font(_FONT_BOLD_CANDIDATES,    11)

    # ── LEFT column: avatar + name + title ─────────────────
    left_w = int(width * 0.42)  # photo side
    center_x = pad + left_w // 2
    avatar_radius = 100
    avatar_cy = pad + 130
    _draw_circular_avatar(img, center_x, avatar_cy, avatar_radius, user)

    # Subtle white ring around the avatar
    ring = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse(
        (center_x - avatar_radius - 4, avatar_cy - avatar_radius - 4,
         center_x + avatar_radius + 4, avatar_cy + avatar_radius + 4),
        outline=(255, 255, 255, 255), width=4,
    )
    img.paste(ring, (0, 0), ring)

    # Name (centred under photo)
    name_text = name.upper()
    nb = draw.textbbox((0, 0), name_text, font=f_name)
    nw = nb[2] - nb[0]
    name_y = avatar_cy + avatar_radius + 26
    draw.text(
        (center_x - nw // 2 - nb[0], name_y),
        name_text, font=f_name, fill=(40, 50, 65),
    )

    # Title (centred under name)
    title_y = name_y + (nb[3] - nb[1]) + 14
    title_text = (title or "MEMBER").upper()
    tb = draw.textbbox((0, 0), title_text, font=f_title)
    tw = tb[2] - tb[0]
    draw.text(
        (center_x - tw // 2 - tb[0], title_y),
        title_text, font=f_title, fill=(120, 130, 145),
    )

    # ── Vertical separator line ────────────────────────────
    sep_x = pad + left_w
    sep_top = pad + 60
    sep_bottom = height - pad - 60
    draw.line(
        [(sep_x, sep_top), (sep_x, sep_bottom)],
        fill=(200, 200, 205), width=2,
    )

    # ── RIGHT column: contact info rows ───────────────────
    right_x = sep_x + 36
    right_w = width - right_x - 40

    icon_size = 22
    icon_gap = 14
    text_max_w = right_w - icon_size - icon_gap

    def _draw_row(y, kind, text, font, fill=(35, 45, 60)):
        # Icon
        _draw_icon(draw, right_x, y, kind, size=icon_size, color=(45, 55, 70))
        text_x = right_x + icon_size + icon_gap
        # Wrap text if too long
        lines = _wrap_text(draw, text, font, text_max_w)
        first_line_y = y + 2
        for li, line in enumerate(lines):
            draw.text(
                (text_x, first_line_y + li * 20), line, font=font, fill=fill,
            )
        return max(icon_size, len(lines) * 20 + 4)

    rows = []
    # Address (uppercase — addresses are conventionally all-caps on cards)
    if location and location != "—":
        rows.append(("home", location.upper(), f_body_bold))
    # Phone — keep as typed (so any extension letters or formatting stay readable)
    if phone and phone != "—":
        rows.append(("phone", phone, f_body_bold))
    # Email — keep as typed (so @ and . stay where the user put them)
    if email and email != "—":
        rows.append(("email", email, f_body))
    if instagram:
        ig = (instagram.lstrip("@")
                       .replace("https://instagram.com/", "")
                       .replace("http://instagram.com/", "")
                       .replace("instagram.com/", ""))
        if ig:
            rows.append(("instagram", f"@{ig}", f_body))  # as-typed (no uppercase)
    if facebook:
        fb = (facebook.lstrip("@")
                       .replace("https://facebook.com/", "")
                       .replace("https://www.facebook.com/", "")
                       .replace("http://facebook.com/", "")
                       .replace("facebook.com/", ""))
        if fb:
            rows.append(("facebook", f"@{fb}", f_body))  # as-typed (no uppercase)

    # Lay the rows out from the top
    row_y = sep_top
    row_spacing = 26
    for kind, text, font in rows:
        used = _draw_row(row_y, kind, text, font)
        row_y += used + row_spacing
        if row_y > sep_bottom - 30:
            break  # don't overflow the card

    # ── "Powered by EthioChain" badge (bottom-right) ───────
    brand = "EthioChain"
    bb = draw.textbbox((0, 0), brand, font=f_brand)
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    bx = width - pad - bw - 18
    by = height - pad - bh - 14
    pill_w = bw + 24
    pill_h = bh + 10
    draw.rounded_rectangle(
        [bx - 12, by - 5, bx - 12 + pill_w, by - 5 + pill_h],
        radius=10, fill=(16, 185, 129),
    )
    draw.text((bx, by), brand, font=f_brand, fill=(255, 255, 255))

    # ── Save and return ──────────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


def render_qr_only_png(data: str, size: int = 480) -> Optional[bytes]:
    """Render JUST the QR code as a square PNG, for separate download.

    The QR is white-on-white with a coloured frame and "SCAN ME" label,
    so it looks intentional on its own. Returns ``None`` if qrcode
    or Pillow aren't installed.
    """
    if not _PIL_OK:
        return None
    try:
        import qrcode
        from qrcode.image.pil import PilImage
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        qr_img = qr.make_image(
            fill_color="black", back_color="white", image_factory=PilImage
        )
        if hasattr(qr_img, "convert"):
            qr_img = qr_img.convert("RGB")
    except Exception:
        return None

    qr_img = qr_img.resize((size, size), Image.LANCZOS)

    # Build a framed canvas: padding + QR + label below
    pad = 30
    label_h = 60
    canvas_w = size + 2 * pad
    canvas_h = size + 2 * pad + label_h
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    cdraw = ImageDraw.Draw(canvas)

    # Coloured frame
    cdraw.rounded_rectangle(
        [6, 6, canvas_w - 6, canvas_h - 6],
        radius=20, outline=(16, 185, 129), width=4,
    )
    # QR
    canvas.paste(qr_img, (pad, pad))

    # "SCAN ME" label
    f = _find_font(_FONT_BOLD_CANDIDATES, 28)
    label = "SCAN TO VIEW CARD"
    bb = cdraw.textbbox((0, 0), label, font=f)
    lw = bb[2] - bb[0]
    cdraw.text(
        ((canvas_w - lw) // 2 - bb[0], size + pad + 14),
        label, font=f, fill=(16, 185, 129),
    )
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", quality=95)
    return buf.getvalue()
