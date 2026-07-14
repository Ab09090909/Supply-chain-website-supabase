"""Format helpers."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from .constants import CURRENCY_CODE, CURRENCY_SYMBOL, UNIT_SHORT


def format_currency(amount, currency: str = None) -> str:
    """Format a number as Ethiopian Birr currency string.

    Examples:
        format_currency(1234.5) -> "Br 1,234.50"
        format_currency(None)   -> "—"
    """
    if amount is None:
        return "—"
    try:
        amt = float(amount)
        # ETB typically doesn't use decimals for large amounts; keep 2 decimals
        if amt == int(amt):
            return f"{CURRENCY_SYMBOL} {int(amt):,}"
        return f"{CURRENCY_SYMBOL} {amt:,.2f}"
    except Exception:
        return str(amount)


def format_unit(unit: str | None) -> str:
    """Convert a long unit label like 'kg (kilogram)' to short 'kg'."""
    if not unit:
        return ""
    return UNIT_SHORT.get(unit, unit)


def format_datetime(dt_str: str | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format an ISO timestamp as readable string."""
    if not dt_str:
        return "—"
    try:
        clean = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        return dt.strftime(fmt)
    except Exception:
        return str(dt_str)


def generate_order_number(role: str = "CUST") -> str:
    """Generate a unique order number."""
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_uuid = uuid4().hex[:6].upper()
    return f"ORD-{role[:4].upper()}-{ts}-{short_uuid}"
