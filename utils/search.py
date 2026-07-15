"""
Product search & filter helpers.

Used by the marketplace pages to search by name/SKU/category,
filter by price range, sort by price/rating/date, etc.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import re


def filter_products(
    products: List[Dict[str, Any]],
    query: str = "",
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    in_stock_only: bool = False,
    sort_by: str = "newest",
) -> List[Dict[str, Any]]:
    """Filter and sort a list of product dicts in-memory.

    The marketplace currently fetches all products and filters client-side.
    For larger catalogs you'd want to push these into PostgREST `.ilike`,
    `.gte`, `.lte`, `.order` query params; for <1000 products the
    in-memory approach is fast enough and avoids a roundtrip per filter.
    """
    q = (query or "").strip().lower()
    cat = (category or "").strip()
    if cat.lower() in ("all", "any", ""):
        cat = ""

    out = []
    for p in products:
        # Text search: name, SKU, description, brand
        if q:
            hay = " ".join([
                str(p.get("name", "")),
                str(p.get("sku", "")),
                str(p.get("description", "") or ""),
                str(p.get("brand", "") or ""),
                str(p.get("category", "") or ""),
            ]).lower()
            if q not in hay:
                continue

        # Category
        if cat and (p.get("category") or "").lower() != cat.lower():
            continue

        # Price range
        price = float(p.get("price") or 0)
        if min_price is not None and price < float(min_price):
            continue
        if max_price is not None and price > float(max_price):
            continue

        # Min rating
        if min_rating is not None:
            rating = float(p.get("avg_rating") or 0)
            if rating < float(min_rating):
                continue

        # In-stock
        if in_stock_only and int(p.get("stock") or 0) <= 0:
            continue

        out.append(p)

    # Sort
    if sort_by == "price_asc":
        out.sort(key=lambda p: float(p.get("price") or 0))
    elif sort_by == "price_desc":
        out.sort(key=lambda p: float(p.get("price") or 0), reverse=True)
    elif sort_by == "rating":
        out.sort(key=lambda p: float(p.get("avg_rating") or 0), reverse=True)
    elif sort_by == "popular":
        out.sort(key=lambda p: int(p.get("sales_count") or 0), reverse=True)
    elif sort_by == "name":
        out.sort(key=lambda p: str(p.get("name") or "").lower())
    else:  # newest
        out.sort(key=lambda p: str(p.get("created_at") or ""), reverse=True)

    return out
