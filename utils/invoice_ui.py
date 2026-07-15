"""
Invoice download button — for any order detail page.
"""
from __future__ import annotations

import streamlit as st
from typing import Dict, Any, List
from database.connection import get_supabase_client
from utils.invoice import generate_invoice_pdf


def render_invoice_button(order: Dict[str, Any], buyer: Dict[str, Any], seller: Dict[str, Any]):
    """Show a 'Download invoice (PDF)' button for a completed order."""
    items = _load_order_items(order.get("id"))
    if not items:
        return
    pdf = generate_invoice_pdf(order, buyer, seller, items)
    order_num = order.get("order_number") or order.get("id", "invoice")[:8]
    st.download_button(
        label="📄 Download invoice (PDF)",
        data=pdf,
        file_name=f"invoice_{order_num}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


def _load_order_items(order_id: str) -> List[Dict[str, Any]]:
    try:
        client = get_supabase_client()
        r = (
            client.table("order_items")
            .select("*")
            .eq("order_id", order_id)
            .execute()
        )
        return r.data or []
    except Exception:
        return []
