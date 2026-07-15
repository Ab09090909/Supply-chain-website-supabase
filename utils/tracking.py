"""
Order tracking & timeline.

Uses the order_tracking and order_timeline tables (see migration_v6.sql).
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from database.connection import get_supabase_client, get_supabase_admin_client


def get_tracking(order_id: str) -> Optional[Dict[str, Any]]:
    """Get the tracking record for an order (one per order)."""
    try:
        client = get_supabase_client()
        r = (
            client.table("order_tracking")
            .select("*")
            .eq("order_id", order_id)
            .limit(1)
            .execute()
        )
        if r.data:
            return r.data[0]
        return None
    except Exception:
        return None


def get_timeline(order_id: str) -> List[Dict[str, Any]]:
    """Get the order_timeline events, newest first."""
    try:
        client = get_supabase_client()
        r = (
            client.table("order_timeline")
            .select("*, profiles!order_timeline_actor_id_fkey(full_name)")
            .eq("order_id", order_id)
            .order("created_at", desc=True)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def update_tracking(
    order_id: str,
    *,
    status: Optional[str] = None,
    tracking_number: Optional[str] = None,
    carrier: Optional[str] = None,
    estimated_delivery: Optional[str] = None,
    notes: Optional[str] = None,
) -> tuple[bool, str]:
    """Seller-side: update the tracking record for an order.

    Creates the record if it doesn't exist. Status changes also write
    a row to order_timeline via a database trigger.
    """
    try:
        client = get_supabase_client()
        existing = get_tracking(order_id)
        payload: Dict[str, Any] = {}
        if status is not None:
            payload["status"] = status
            if status == "shipped":
                from datetime import datetime, timezone
                payload["shipped_at"] = datetime.now(timezone.utc).isoformat()
            if status == "delivered":
                from datetime import datetime, timezone
                payload["delivered_at"] = datetime.now(timezone.utc).isoformat()
        if tracking_number is not None:
            payload["tracking_number"] = tracking_number
        if carrier is not None:
            payload["carrier"] = carrier
        if estimated_delivery is not None:
            payload["estimated_delivery"] = estimated_delivery
        if notes is not None:
            payload["notes"] = notes

        if existing:
            client.table("order_tracking").update(payload).eq("order_id", order_id).execute()
        else:
            payload["order_id"] = order_id
            if "status" not in payload:
                payload["status"] = "pending"
            client.table("order_tracking").insert(payload).execute()
        return True, "Tracking updated."
    except Exception as e:
        return False, f"Failed: {e}"


def add_timeline_event(
    order_id: str,
    event: str,
    description: str = "",
) -> tuple[bool, str]:
    """Manually add a timeline event (most are auto-created by triggers)."""
    try:
        client = get_supabase_client()
        client.table("order_timeline").insert({
            "order_id": order_id,
            "event": event,
            "description": description or None,
            "actor_id": None,  # the trigger will set it; manual ones get null
        }).execute()
        return True, "Event added."
    except Exception as e:
        return False, f"Failed: {e}"
