"""
Producer analytics — sales, top products, customer geography.

Aggregates data from the orders, order_items, and products tables.
Designed for the producer dashboard, but the same queries work for
admin (platform-wide) when given a different scope.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import pandas as pd
from database.connection import get_supabase_client


def get_producer_sales_summary(producer_id: str, days: int = 30) -> Dict[str, Any]:
    """Return aggregate sales metrics for one producer over the last N days.

    Returns: {
      'total_revenue_etb', 'order_count', 'items_sold',
      'avg_order_value_etb', 'unique_customers', 'top_products': [...]
    }
    """
    try:
        client = get_supabase_client()
        # Get all of the producer's product ids
        prods = (
            client.table("products")
            .select("id, name, sku, price, stock, sales_count, avg_rating, review_count")
            .eq("producer_id", producer_id)
            .execute()
        ).data or []
        product_ids = [p["id"] for p in prods]
        if not product_ids:
            return {
                "total_revenue_etb": 0.0,
                "order_count": 0,
                "items_sold": 0,
                "avg_order_value_etb": 0.0,
                "unique_customers": 0,
                "top_products": [],
                "revenue_by_day": [],
                "days": days,
            }

        # Get order_items for these products, joined to orders
        # The query uses order_items!inner(...) to filter
        items = (
            client.table("order_items")
            .select("product_id, quantity, unit_price, order_id, orders!inner(buyer_id, total, status, placed_at, created_at)")
            .in_("product_id", product_ids)
            .execute()
        ).data or []

        # Filter to last N days and exclude cancelled orders
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        recent = [
            it for it in items
            if (it.get("orders") or {}).get("created_at", "") >= cutoff
            and (it.get("orders") or {}).get("status") != "cancelled"
        ]

        total_revenue = sum(
            float((it.get("orders") or {}).get("total") or 0)
            for it in recent
        )
        # Revenue per item (use unit_price * qty as a fallback)
        items_sold = sum(int(it.get("quantity") or 0) for it in recent)
        order_ids = list({(it.get("orders") or {}).get("order_id") for it in recent})
        customer_ids = list({(it.get("orders") or {}).get("buyer_id") for it in recent})
        avg_order_value = (total_revenue / len(order_ids)) if order_ids else 0.0

        # Top products: by item count in window
        per_product: Dict[str, int] = {}
        per_product_revenue: Dict[str, float] = {}
        for it in recent:
            pid = it.get("product_id")
            qty = int(it.get("quantity") or 0)
            rev = float(it.get("unit_price") or 0) * qty
            per_product[pid] = per_product.get(pid, 0) + qty
            per_product_revenue[pid] = per_product_revenue.get(pid, 0.0) + rev

        prod_map = {p["id"]: p for p in prods}
        top_products = sorted(
            [
                {
                    "id": pid,
                    "name": prod_map.get(pid, {}).get("name", "?"),
                    "sku": prod_map.get(pid, {}).get("sku", ""),
                    "units_sold": per_product.get(pid, 0),
                    "revenue_etb": per_product_revenue.get(pid, 0.0),
                    "avg_rating": float(prod_map.get(pid, {}).get("avg_rating") or 0),
                    "review_count": int(prod_map.get(pid, {}).get("review_count") or 0),
                }
                for pid in per_product
            ],
            key=lambda x: x["units_sold"],
            reverse=True,
        )[:10]

        # Revenue by day (last N days)
        revenue_by_day: Dict[str, float] = {}
        for it in recent:
            placed = (it.get("orders") or {}).get("created_at", "")
            if not placed:
                continue
            day = placed[:10]  # YYYY-MM-DD
            rev = float(it.get("unit_price") or 0) * int(it.get("quantity") or 0)
            revenue_by_day[day] = revenue_by_day.get(day, 0.0) + rev
        revenue_by_day_list = [
            {"date": d, "revenue": revenue_by_day[d]}
            for d in sorted(revenue_by_day.keys())
        ]

        return {
            "total_revenue_etb": total_revenue,
            "order_count": len(order_ids),
            "items_sold": items_sold,
            "avg_order_value_etb": avg_order_value,
            "unique_customers": len([c for c in customer_ids if c]),
            "top_products": top_products,
            "revenue_by_day": revenue_by_day_list,
            "days": days,
        }
    except Exception as e:
        return {
            "total_revenue_etb": 0.0,
            "order_count": 0,
            "items_sold": 0,
            "avg_order_value_etb": 0.0,
            "unique_customers": 0,
            "top_products": [],
            "revenue_by_day": [],
            "days": days,
            "error": str(e),
        }


def get_low_stock_products(producer_id: str) -> List[Dict[str, Any]]:
    """Return products where stock <= reorder_point."""
    try:
        client = get_supabase_client()
        prods = (
            client.table("products")
            .select("id, name, sku, stock, reorder_point, reorder_quantity, image_url, price")
            .eq("producer_id", producer_id)
            .eq("status", "active")
            .execute()
        ).data or []
        return [
            {
                **p,
                "shortfall": max(0, int(p.get("reorder_point") or 0) - int(p.get("stock") or 0)),
            }
            for p in prods
            if int(p.get("stock") or 0) <= int(p.get("reorder_point") or 0)
        ]
    except Exception:
        return []


def get_platform_summary() -> Dict[str, Any]:
    """Admin-side: aggregate metrics across the whole platform."""
    try:
        client = get_supabase_client()
        users = (client.table("profiles").select("id, role, created_at").execute()).data or []
        products = (client.table("products").select("id, status, stock, created_at").execute()).data or []
        orders = (client.table("orders").select("id, total, status, created_at").execute()).data or []
        return {
            "users_total": len(users),
            "users_producers": sum(1 for u in users if u.get("role") == "producer"),
            "users_merchants": sum(1 for u in users if u.get("role") == "merchant"),
            "users_customers": sum(1 for u in users if u.get("role") == "customer"),
            "products_total": len(products),
            "products_active": sum(1 for p in products if p.get("status") == "active"),
            "products_low_stock": sum(1 for p in products if int(p.get("stock") or 0) <= int(p.get("reorder_point") or 0)),
            "orders_total": len(orders),
            "orders_pending": sum(1 for o in orders if o.get("status") == "pending"),
            "orders_delivered": sum(1 for o in orders if o.get("status") == "delivered"),
            "gmv_etb": sum(float(o.get("total") or 0) for o in orders if o.get("status") != "cancelled"),
        }
    except Exception as e:
        return {"error": str(e)}
