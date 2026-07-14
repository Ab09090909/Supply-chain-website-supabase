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

# --------------------------------------------------------------------------
# Currency — switched to Ethiopian Birr (ETB)
# --------------------------------------------------------------------------
CURRENCY_CODE = "ETB"
CURRENCY_SYMBOL = "Br"

# --------------------------------------------------------------------------
# Product units — international + Ethiopian standards
# --------------------------------------------------------------------------
# Grouped by category so the dropdown in the UI can show optgroups.
PRODUCT_CATEGORIES = [
    "Grains", "Dairy", "Fruits", "Vegetables",
    "Pantry", "Beverages", "Herbs", "Meat & Poultry",
    "Seafood", "Bakery", "Coffee & Tea", "Spices",
    "Other",
]

# Flat list for selectbox (with helpful labels)
UNIT_OPTIONS = [
    # --- Weight (metric / international) ---
    "kg (kilogram)",
    "g (gram)",
    "ton (metric ton)",
    "quintal (100 kg)",  # Ethiopian standard
    "mg (milligram)",
    # --- Weight (Ethiopian / regional) ---
    "sack (50 kg)",
    "sack (100 kg)",
    "bag (60 kg — coffee standard)",
    "bag (small)",
    # --- Volume (international) ---
    "litre (L)",
    "ml (millilitre)",
    "gallon (US)",
    "gallon (UK)",
    # --- Count / pieces ---
    "piece (unit)",
    "dozen (12)",
    "half-dozen (6)",
    "pair (2)",
    "set",
    # --- Packaging ---
    "box",
    "carton",
    "crate",
    "bottle",
    "jar",
    "can",
    "packet",
    "bunch",
    "bundle",
    # --- Length (for non-food like textiles) ---
    "m (metre)",
    "cm (centimetre)",
    "roll",
    # --- Other ---
    "other",
]

# Quick lookup from label → short form for display
UNIT_SHORT = {
    "kg (kilogram)": "kg",
    "g (gram)": "g",
    "ton (metric ton)": "ton",
    "quintal (100 kg)": "quintal",
    "mg (milligram)": "mg",
    "sack (50 kg)": "sack",
    "sack (100 kg)": "sack",
    "bag (60 kg — coffee standard)": "bag",
    "bag (small)": "bag",
    "litre (L)": "L",
    "ml (millilitre)": "ml",
    "gallon (US)": "gal",
    "gallon (UK)": "gal",
    "piece (unit)": "pc",
    "dozen (12)": "dz",
    "half-dozen (6)": "6-pc",
    "pair (2)": "pair",
    "set": "set",
    "box": "box",
    "carton": "carton",
    "crate": "crate",
    "bottle": "btl",
    "jar": "jar",
    "can": "can",
    "packet": "pkt",
    "bunch": "bunch",
    "bundle": "bundle",
    "m (metre)": "m",
    "cm (centimetre)": "cm",
    "roll": "roll",
    "other": "—",
}

# --------------------------------------------------------------------------
# Quality grades (commonly used in agricultural supply chains)
# --------------------------------------------------------------------------
QUALITY_GRADES = [
    "Grade A (Premium)",
    "Grade A",
    "Grade B (Standard)",
    "Grade C (Processing)",
    "Premium",
    "Export Quality",
    "Local Market",
    "Organic Certified",
    "Ungraded",
]

# --------------------------------------------------------------------------
# Common certifications
# --------------------------------------------------------------------------
CERTIFICATION_OPTIONS = [
    "Organic",
    "Fair Trade",
    "Rainforest Alliance",
    "UTZ Certified",
    "ISO 22000 (Food Safety)",
    "HACCP",
    "Halal",
    "Kosher",
    "Ethiopian Coffee Association",
    "EGA (Ethiopian Garlic Authority)",
    "Pasteurized",
    "Raw",
    "Unfiltered",
    "Aged 6 months",
    "Aged 12 months",
    "Vegan",
    "Gluten-Free",
]

# --------------------------------------------------------------------------
# Payment terms
# --------------------------------------------------------------------------
PAYMENT_TERMS = [
    "Cash on Delivery",
    "Net 7 (7 days)",
    "Net 15 (15 days)",
    "Net 30 (30 days)",
    "Net 60 (60 days)",
    "Prepayment (100% upfront)",
    "50% Advance, 50% on Delivery",
    "Letter of Credit",
]

# --------------------------------------------------------------------------
# Order statuses with friendly labels
# --------------------------------------------------------------------------
ORDER_STATUS_LABELS = {
    "pending": "Pending",
    "confirmed": "Confirmed",
    "processing": "Processing",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}
