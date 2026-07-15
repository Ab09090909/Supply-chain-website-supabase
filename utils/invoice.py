"""
Lightweight PDF invoice generator.

Uses only the Python standard library — no fpdf, reportlab, or other
heavy deps. The output is a tiny but valid PDF with the order
header, line items, and totals.

For a more sophisticated design, swap this for reportlab. But for
invoices this is enough and has zero install cost.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
import io
import zlib


def _pdf_escape(s: str) -> str:
    """Escape a string for inclusion in a PDF text object."""
    return (
        s.replace("\\", "\\\\")
         .replace("(", "\\(")
         .replace(")", "\\)")
    )


def _format_money_br(amount: float) -> str:
    """Format an amount in Ethiopian Birr."""
    return f"Br {amount:,.2f}"


def _text_line(x: float, y: float, text: str, font_size: int = 10, font: str = "Helvetica") -> bytes:
    """Generate a PDF text-positioning stream for one line."""
    return f"BT /{font} {font_size} Tf {x} {y} Td ({_pdf_escape(text)}) Tj ET".encode("latin-1", errors="replace")


def generate_invoice_pdf(
    order: Dict[str, Any],
    buyer: Dict[str, Any],
    seller: Dict[str, Any],
    items: List[Dict[str, Any]],
) -> bytes:
    """Generate a PDF invoice for a single order.

    Returns the PDF as bytes. Designed to be passed directly to
    ``st.download_button(data=..., file_name=...)``.
    """
    # Page size: A4 in points (595 x 842)
    page_w, page_h = 595, 842
    margin = 50
    body_w = page_w - 2 * margin

    # Build the content stream
    stream_parts: List[bytes] = []
    y = page_h - margin

    def line(text: str, font_size: int = 10, font: str = "Helvetica", indent: int = 0):
        nonlocal y
        stream_parts.append(_text_line(margin + indent, y, text, font_size, font))
        y -= font_size + 4

    def hr():
        nonlocal y
        stream_parts.append(b"0.5 w 50 0.5 m " + str(page_w - margin).encode() + b" 0.5 l S")
        y -= 8

    # Header
    line("AI SUPPLY CHAIN PLATFORM", font_size=18, font="Helvetica-Bold")
    line("INVOICE / RECEIPT", font_size=11, font="Helvetica-Bold")
    y -= 6
    hr()

    # Order info
    order_number = order.get("order_number", "")
    placed_at = (order.get("placed_at") or order.get("created_at") or "")[:19]
    line(f"Order #: {order_number}", font_size=10, font="Helvetica-Bold")
    line(f"Placed:  {placed_at}", font_size=9)
    status = (order.get("status") or "").upper()
    if status:
        line(f"Status:  {status}", font_size=9)
    y -= 4
    hr()

    # Parties
    line("FROM (Seller):", font_size=10, font="Helvetica-Bold")
    line(f"  {seller.get('full_name', '')}", font_size=9)
    if seller.get("company"):
        line(f"  {seller.get('company', '')}", font_size=9)
    if seller.get("email"):
        line(f"  {seller.get('email', '')}", font_size=9)
    if seller.get("phone"):
        line(f"  {seller.get('phone', '')}", font_size=9)
    if seller.get("location"):
        line(f"  {seller.get('location', '')}", font_size=9)
    y -= 4
    line("BILL TO (Buyer):", font_size=10, font="Helvetica-Bold")
    line(f"  {buyer.get('full_name', '')}", font_size=9)
    if buyer.get("email"):
        line(f"  {buyer.get('email', '')}", font_size=9)
    if buyer.get("phone"):
        line(f"  {buyer.get('phone', '')}", font_size=9)
    if buyer.get("location"):
        line(f"  {buyer.get('location', '')}", font_size=9)
    y -= 6
    hr()

    # Line items header
    line("ITEMS", font_size=10, font="Helvetica-Bold")
    y -= 2

    # Table header
    line(f"{'SKU':<14} {'Description':<32} {'Qty':>4} {'Unit':>10} {'Total':>12}", font_size=8, font="Helvetica-Bold")
    y -= 2
    hr()

    # Rows
    for it in items:
        sku = str(it.get("sku", ""))[:14]
        name = str(it.get("name", ""))[:32]
        qty = int(it.get("quantity") or 0)
        unit = float(it.get("unit_price") or 0)
        total = qty * unit
        line(f"{sku:<14} {name:<32} {qty:>4} {_format_money_br(unit):>10} {_format_money_br(total):>12}", font_size=9)
    y -= 4
    hr()

    # Totals
    subtotal = sum(int(it.get("quantity") or 0) * float(it.get("unit_price") or 0) for it in items)
    tax = float(order.get("tax") or 0)
    shipping = float(order.get("shipping_cost") or 0)
    total = float(order.get("total") or (subtotal + tax + shipping))

    line(f"Subtotal:   {_format_money_br(subtotal):>14}", font_size=10)
    line(f"Tax (15%):  {_format_money_br(tax):>14}", font_size=10)
    line(f"Shipping:   {_format_money_br(shipping):>14}", font_size=10)
    y -= 2
    line(f"TOTAL:      {_format_money_br(total):>14}", font_size=12, font="Helvetica-Bold")
    y -= 12

    # Footer
    hr()
    line("Thank you for your business.", font_size=9, font="Helvetica-Oblique")
    line(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", font_size=7)

    content = b"\n".join(stream_parts)
    # Build the PDF
    objects: List[bytes] = []
    # 1. Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    # 2. Pages
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    # 3. Page
    objects.append(
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_w} {page_h}] "
        f"/Resources << /Font << /Helvetica 4 0 R /Helvetica-Bold 5 0 R "
        f"/Helvetica-Oblique 6 0 R >> >> /Contents 7 0 R >>".encode("latin-1")
    )
    # 4, 5, 6. Fonts
    for font_name in ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique"):
        objects.append(
            f"<< /Type /Font /Subtype /Type1 /BaseFont /{font_name} >>".encode("latin-1")
        )
    # 7. Contents (compressed)
    compressed = zlib.compress(content)
    objects.append(
        f"<< /Length {len(compressed)} /Filter /FlateDecode >>\nstream\n".encode("latin-1")
        + compressed
        + b"\nendstream"
    )

    # Assemble the PDF
    out = b"%PDF-1.4\n"
    offsets: List[int] = []
    for obj in objects:
        offsets.append(len(out))
        out += f"{offsets[-1]} 0 obj\n".encode("latin-1") + obj + b"\nendobj\n"
    # xref
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode("latin-1")
    return out
