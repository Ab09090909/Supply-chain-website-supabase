"""Constants used across the app."""
from __future__ import annotations

ROLE_OPTIONS = ["producer", "merchant", "customer", "admin"]

ROLE_DESCRIPTIONS = {
    "producer": "Sell products",
    "merchant": "Buy & resell",
    "customer": "Shop products",
    "admin":    "Manage all",
}

ROLE_COLORS = {
    "producer": "#10b981",  # emerald
    "merchant": "#f59e0b",  # amber
    "customer": "#3b82f6",  # blue
    "admin":    "#ef4444",  # red
}

ROLE_LABELS = {
    "producer": "Producer",
    "merchant": "Merchant",
    "customer": "Customer",
    "admin":    "Admin",
}
