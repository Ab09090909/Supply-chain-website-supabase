"""Format helpers."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4


def format_currency(amount: float | int | None, currency: str = "USD") -> str:
    """Format a number as USD currency string."""
    if amount is None:
        return "—"
    try:
        return f"${float(amount):,.2f}"
    except Exception:
        return str(amount)


def format_datetime(dt_str: str | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format an ISO timestamp as readable string."""
    if not dt_str:
        return "—"
    try:
        # Handle both 'Z' suffix and offset formats
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
