"""
Recommendations helper — thin wrapper around ai.recommendations.

The customer dashboard calls ``get_recommendations_for_user()``, which
delegates to the AI collaborative-filtering engine. If the AI module
is unavailable (e.g. scikit-learn not installed), we fall back to a
simple "most popular" heuristic so the page never crashes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st


def get_recommendations_for_user(
    user_id: str,
    *,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """Return product recommendations for *user_id*.

    Tries the AI collaborative-filtering engine first. If that fails
    (missing scikit-learn, no data, etc.), falls back to the
    "most popular products" heuristic from the database.
    """
    # ---- Strategy 1: AI engine (collaborative filtering) ----
    try:
        from ai.recommendations import get_recommendations
        recs = get_recommendations(user_id, limit=limit)
        if recs:
            return recs
    except Exception:
        pass

    # ---- Strategy 2: most-popular fallback ----
    try:
        from database.connection import get_supabase_client
        client = get_supabase_client()
        products = (
            client.table("products")
            .select("id, name, price, image_url, category, avg_rating, review_count, stock, sku")
            .eq("status", "active")
            .gt("stock", 0)
            .order("sales_count", desc=True)
            .limit(limit)
            .execute()
        ).data or []
        return products
    except Exception:
        return []
