"""
Product reviews & ratings.

Uses the product_reviews table (see supabase_sql/migration_v6.sql).
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from database.connection import get_supabase_client


def list_reviews_for_product(product_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch visible reviews for a product, newest first."""
    try:
        client = get_supabase_client()
        r = (
            client.table("product_reviews")
            .select("*, profiles!product_reviews_reviewer_id_fkey(full_name, avatar_url)")
            .eq("product_id", product_id)
            .eq("is_visible", "true")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def list_reviews_by_buyer(buyer_id: str) -> List[Dict[str, Any]]:
    """Fetch all reviews written by a given buyer (used to show 'you already rated' on order pages)."""
    try:
        client = get_supabase_client()
        r = (
            client.table("product_reviews")
            .select("id, product_id, order_id, rating, title, body, created_at")
            .eq("reviewer_id", buyer_id)
            .order("created_at", desc=True)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def get_review_for_order(order_id: str, reviewer_id: str) -> Optional[Dict[str, Any]]:
    """Return the review (if any) the given reviewer left for the given order.

    Used by the order pages to detect "you've already rated this" so we can
    show the existing review instead of letting them post a duplicate.
    """
    try:
        client = get_supabase_client()
        r = (
            client.table("product_reviews")
            .select("id, product_id, order_id, rating, title, body, created_at")
            .eq("order_id", order_id)
            .eq("reviewer_id", reviewer_id)
            .maybe_single()
            .execute()
        )
        return r.data if r else None
    except Exception:
        return None


def list_products_with_ratings(producer_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return every product with its aggregate rating fields, optionally
    filtered to one producer. Used by producer inventory and admin views
    so the rating column is always available even when zero reviews exist.
    """
    try:
        client = get_supabase_client()
        q = client.table("products").select("id, name, sku, avg_rating, review_count")
        if producer_id:
            q = q.eq("producer_id", producer_id)
        r = q.execute()
        return r.data or []
    except Exception:
        return []


def has_user_purchased(user_id: str, product_id: str) -> bool:
    """Return True if the user has ever bought this product in a completed/pending order.

    Used to gate the "leave a review" form: only verified buyers can review.
    """
    try:
        client = get_supabase_client()
        r = (
            client.table("orders")
            .select("id, order_items!inner(product_id, quantity)")
            .or_("buyer_id.eq." + user_id)
            .execute()
        )
        # Filter to orders that contain this product
        for order in (r.data or []):
            for item in (order.get("order_items") or []):
                if str(item.get("product_id")) == str(product_id) and int(item.get("quantity") or 0) > 0:
                    return True
        return False
    except Exception:
        return False


def create_review(
    product_id: str,
    reviewer_id: str,
    rating: int,
    title: str = "",
    body: str = "",
    order_id: Optional[str] = None,
) -> tuple[bool, str]:
    """Create a new review. Returns (success, message_or_review_id)."""
    rating = int(rating)
    if rating < 1 or rating > 5:
        return False, "Rating must be 1-5"
    try:
        client = get_supabase_client()
        # Determine if this is a verified-buyer review
        verified = order_id is not None
        r = (
            client.table("product_reviews")
            .insert({
                "product_id": product_id,
                "reviewer_id": reviewer_id,
                "rating": rating,
                "title": title or None,
                "body": body or None,
                "order_id": order_id,
                "is_verified": verified,
                "is_visible": True,
            })
            .execute()
        )
        if r.data:
            return True, "Review posted!"
        return False, "Failed to post review."
    except Exception as e:
        msg = str(e)
        if "duplicate" in msg.lower() or "unique" in msg.lower():
            return False, "You've already reviewed this product from this order."
        return False, f"Failed: {msg[:200]}"


def delete_review(review_id: str, user_id: str) -> tuple[bool, str]:
    """Delete a review (only by its author or an admin)."""
    try:
        client = get_supabase_client()
        client.table("product_reviews").delete().eq("id", review_id).eq("reviewer_id", user_id).execute()
        return True, "Review deleted."
    except Exception as e:
        return False, f"Failed: {e}"


def mark_helpful(review_id: str) -> bool:
    """Increment the helpful_count on a review."""
    try:
        client = get_supabase_client()
        # Use a SQL expression update: helpful_count = helpful_count + 1
        # PostgREST doesn't support that directly via the simple client,
        # so we read-modify-write (acceptable for low-volume counters).
        r = client.table("product_reviews").select("helpful_count").eq("id", review_id).single().execute()
        current = int((r.data or {}).get("helpful_count") or 0)
        client.table("product_reviews").update({"helpful_count": current + 1}).eq("id", review_id).execute()
        return True
    except Exception:
        return False
