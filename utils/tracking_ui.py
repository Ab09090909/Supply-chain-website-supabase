"""
Order tracking UI — buyer-facing status timeline + seller update form.
"""
from __future__ import annotations

import streamlit as st
from typing import Dict, Any
from datetime import date
from utils.tracking import (
    get_tracking,
    get_timeline,
    update_tracking,
)


_STATUS_LABELS = {
    "pending": "⏳ Pending",
    "confirmed": "✅ Confirmed",
    "processing": "🔄 Processing",
    "shipped": "🚚 Shipped",
    "delivered": "📦 Delivered",
    "cancelled": "❌ Cancelled",
}


def render_buyer_tracking(order_id: str):
    """Render the buyer-facing tracking view: current status + timeline."""
    tracking = get_tracking(order_id)
    timeline = get_timeline(order_id)

    st.markdown("##### 📦 Order Tracking")

    if not tracking and not timeline:
        st.info("Tracking information isn't available yet. The seller will update it soon.")
        return

    # Current status banner
    if tracking:
        status = tracking.get("status", "pending")
        label = _STATUS_LABELS.get(status, status.title())
        st.markdown(f"**Current Status:** {label}")
        cols = st.columns(2)
        with cols[0]:
            if tracking.get("tracking_number"):
                st.markdown(f"**Tracking #:** `{tracking.get('tracking_number')}`")
            if tracking.get("carrier"):
                st.markdown(f"**Carrier:** {tracking.get('carrier')}")
        with cols[1]:
            if tracking.get("estimated_delivery"):
                st.markdown(f"**Estimated delivery:** {tracking.get('estimated_delivery')}")
            if tracking.get("shipped_at"):
                st.markdown(f"**Shipped at:** {tracking.get('shipped_at')[:10]}")
            if tracking.get("delivered_at"):
                st.markdown(f"**Delivered at:** {tracking.get('delivered_at')[:10]}")
        if tracking.get("notes"):
            st.caption(f"📝 {tracking.get('notes')}")
    else:
        st.caption("Status: pending (no tracking info yet)")

    st.markdown("---")

    # Timeline
    st.markdown("##### 📜 Timeline")
    if not timeline:
        st.caption("No events yet.")
        return

    for ev in timeline:
        actor = (ev.get("profiles") or {}).get("full_name", "System")
        ts = (ev.get("created_at") or "")[:19]
        st.markdown(
            f"- **{ev.get('event', '')}**  \n"
            f"  {ev.get('description') or ''}  \n"
            f"  <small style='color:#64748b'>{ts} · by {actor}</small>",
            unsafe_allow_html=True,
        )


def render_seller_tracking_form(order_id: str):
    """Render the seller-facing form to update an order's tracking."""
    st.markdown("##### 🚚 Update Tracking")
    tracking = get_tracking(order_id) or {}

    with st.form(f"track_form_{order_id}"):
        col1, col2 = st.columns(2)
        with col1:
            current_status = tracking.get("status", "pending")
            status_keys = list(_STATUS_LABELS.keys())
            status_idx = status_keys.index(current_status) if current_status in status_keys else 0
            status = st.selectbox(
                "Status",
                options=status_keys,
                index=status_idx,
                format_func=lambda x: _STATUS_LABELS.get(x, x),
                key=f"trk_status_{order_id}",
            )
            tracking_number = st.text_input(
                "Tracking number",
                value=tracking.get("tracking_number") or "",
                key=f"trk_num_{order_id}",
            )
        with col2:
            carrier = st.text_input(
                "Carrier",
                value=tracking.get("carrier") or "",
                placeholder="e.g. Ethiopian Postal Service, DHL",
                key=f"trk_carrier_{order_id}",
            )
            eta = st.date_input(
                "Estimated delivery",
                value=date.fromisoformat(tracking["estimated_delivery"])
                if tracking.get("estimated_delivery")
                else None,
                key=f"trk_eta_{order_id}",
            )
        notes = st.text_area(
            "Notes",
            value=tracking.get("notes") or "",
            key=f"trk_notes_{order_id}",
        )

        if st.form_submit_button("Save tracking", type="primary"):
            ok, msg = update_tracking(
                order_id,
                status=status,
                tracking_number=tracking_number,
                carrier=carrier,
                estimated_delivery=eta.isoformat() if eta else None,
                notes=notes,
            )
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
