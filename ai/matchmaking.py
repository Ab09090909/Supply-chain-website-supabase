"""
AI Matchmaking — finds the best merchant matches for a producer.

Uses a weighted scoring algorithm based on:
  • Category overlap (30%) — producer's product categories vs merchant's preferred_categories
  • Quality grade match (20%) — producer's product grades vs merchant's preferred_quality_grades
  • Brand match (15%) — producer's brands vs merchant's preferred_brands
  • Price range fit (15%) — producer's average price vs merchant's max_price_range
  • Payment terms compatibility (10%) — do their payment terms align?
  • Location proximity (5%) — same region bonus
  • Order history (5%) — has the merchant ordered similar products before?

Returns a list of merchants sorted by match percentage, with breakdown.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import streamlit as st
import pandas as pd
import numpy as np

from database.connection import get_supabase_client


def find_best_merchant_matches(producer_id: str, top_n: int = 10) -> List[Dict[str, Any]]:
    """Find the best merchant matches for a given producer.

    Returns a list of dicts, each containing:
      - merchant_id, merchant_name, merchant_email, merchant_company, merchant_location
      - match_percentage (0-100)
      - breakdown (dict of individual scores)
      - matched_categories, matched_grades, matched_brands
    """
    try:
        client = get_supabase_client()

        # Fetch producer's products
        products = (
            client.table("products")
            .select("*")
            .eq("producer_id", producer_id)
            .eq("status", "active")
            .execute()
        ).data or []

        if not products:
            return []

        # Extract producer's product attributes
        producer_categories = list(set(p.get("category", "") for p in products if p.get("category")))
        producer_grades = list(set(p.get("quality_grade", "") for p in products if p.get("quality_grade")))
        producer_brands = list(set(p.get("brand", "") for p in products if p.get("brand")))
        producer_avg_price = float(np.mean([float(p.get("price", 0)) for p in products])) if products else 0

        # Fetch all merchants with their preferences
        merchants = (
            client.table("profiles")
            .select("id, full_name, email, company, location, phone, role, avatar_url, is_verified, created_at")
            .eq("role", "merchant")
            .eq("is_active", True)
            .execute()
        ).data or []

        if not merchants:
            return []

        # Fetch all merchant preferences
        merchant_ids = [m["id"] for m in merchants]
        prefs_response = (
            client.table("user_preferences")
            .select("*")
            .in_("user_id", merchant_ids)
            .execute()
        ).data or []
        prefs_map = {p["user_id"]: p for p in prefs_response}

        # Fetch existing requests to show status
        existing_requests = (
            client.table("merchant_requests")
            .select("merchant_id, status")
            .eq("producer_id", producer_id)
            .execute()
        ).data or []
        request_status = {r["merchant_id"]: r["status"] for r in existing_requests}

        # Fetch merchant order history (what they've ordered before)
        orders = (
            client.table("orders")
            .select("buyer_id, order_items!inner(product_id)")
            .in_("buyer_id", merchant_ids)
            .execute()
        ).data or []
        merchant_order_products: Dict[str, List[str]] = {}
        for o in orders:
            mid = o.get("buyer_id")
            if mid not in merchant_order_products:
                merchant_order_products[mid] = []
            for item in (o.get("order_items") or []):
                if item.get("product_id"):
                    merchant_order_products[mid].append(str(item["product_id"]))

        # Score each merchant
        results: List[Dict[str, Any]] = []
        producer_product_ids = {str(p["id"]) for p in products}

        for merchant in merchants:
            mid = merchant["id"]
            mprefs = prefs_map.get(mid, {})

            # --- Category overlap (30%) ---
            m_cats = set(mprefs.get("preferred_categories") or [])
            matched_cats = list(set(producer_categories) & m_cats)
            cat_score = len(matched_cats) / max(len(producer_categories), 1) if producer_categories else 0

            # --- Quality grade match (20%) ---
            m_grades = set(mprefs.get("preferred_quality_grades") or [])
            matched_grades = list(set(producer_grades) & m_grades)
            grade_score = len(matched_grades) / max(len(producer_grades), 1) if producer_grades else 0.5  # neutral if no grades

            # --- Brand match (15%) ---
            m_brands = set(mprefs.get("preferred_brands") or [])
            matched_brands = list(set(producer_brands) & m_brands)
            brand_score = len(matched_brands) / max(len(producer_brands), 1) if producer_brands else 0.5

            # --- Price range fit (15%) ---
            m_max_price = float(mprefs.get("max_price_range") or 0)
            if m_max_price > 0 and producer_avg_price > 0:
                if producer_avg_price <= m_max_price:
                    price_score = 1.0
                else:
                    price_score = max(0, 1.0 - (producer_avg_price - m_max_price) / m_max_price)
            else:
                price_score = 0.5  # neutral

            # --- Payment terms compatibility (10%) ---
            # If either side hasn't specified, assume compatible
            payment_score = 0.7  # default neutral-positive
            m_payment = mprefs.get("payment_terms")
            if m_payment:
                # Simple heuristic: Cash on Delivery and Net 30 are most common
                if "Cash on Delivery" in m_payment or "Net 30" in m_payment:
                    payment_score = 1.0
                else:
                    payment_score = 0.8

            # --- Location proximity (5%) ---
            producer = None
            try:
                producer = (
                    client.table("profiles")
                    .select("location")
                    .eq("id", producer_id)
                    .single()
                    .execute()
                ).data
            except Exception:
                pass
            p_location = (producer or {}).get("location", "") or ""
            m_location = merchant.get("location", "") or ""
            if p_location and m_location:
                # Simple: same city/region = full score, same country = partial
                if p_location.lower() in m_location.lower() or m_location.lower() in p_location.lower():
                    loc_score = 1.0
                elif "ethiopia" in p_location.lower() and "ethiopia" in m_location.lower():
                    loc_score = 0.6
                else:
                    loc_score = 0.3
            else:
                loc_score = 0.5

            # --- Order history (5%) ---
            ordered_products = merchant_order_products.get(mid, [])
            overlap = set(ordered_products) & producer_product_ids
            history_score = min(1.0, len(overlap) / 3) if ordered_products else 0.3

            # --- Weighted total ---
            total_score = (
                cat_score * 0.30 +
                grade_score * 0.20 +
                brand_score * 0.15 +
                price_score * 0.15 +
                payment_score * 0.10 +
                loc_score * 0.05 +
                history_score * 0.05
            )
            match_pct = round(total_score * 100, 1)

            results.append({
                "merchant_id": mid,
                "merchant_name": merchant.get("full_name", "Unknown"),
                "merchant_email": merchant.get("email", ""),
                "merchant_company": merchant.get("company") or "",
                "merchant_location": merchant.get("location") or "",
                "merchant_phone": merchant.get("phone") or "",
                "merchant_avatar": merchant.get("avatar_url"),
                "merchant_verified": merchant.get("is_verified", False),
                "match_percentage": match_pct,
                "breakdown": {
                    "category": round(cat_score * 100),
                    "quality_grade": round(grade_score * 100),
                    "brand": round(brand_score * 100),
                    "price_fit": round(price_score * 100),
                    "payment_terms": round(payment_score * 100),
                    "location": round(loc_score * 100),
                    "order_history": round(history_score * 100),
                },
                "matched_categories": matched_cats,
                "matched_grades": matched_grades,
                "matched_brands": matched_brands,
                "existing_request_status": request_status.get(mid),
            })

        # Sort by match percentage descending
        results.sort(key=lambda x: x["match_percentage"], reverse=True)
        return results[:top_n]

    except Exception as e:
        st.error(f"Matchmaking failed: {e}")
        return []
