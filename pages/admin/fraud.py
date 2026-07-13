"""Admin fraud review center."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_admin_client
from utils.ui import page_header
from utils.helpers import format_datetime


def render_admin_fraud():
    page_header("Fraud Detection Center", "Review and resolve fraud alerts")

    user = get_current_user()
    if not user:
        return

    try:
        client = get_supabase_admin_client()
        alerts = client.table("fraud_logs").select("*").order("created_at", desc=True).execute().data or []
    except Exception as e:
        st.error(f"Failed to load alerts: {e}")
        return

    if not alerts:
        st.info("No fraud alerts. All clear!")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Alerts", len(alerts))
    with col2:
        st.metric("Pending", sum(1 for a in alerts if a["status"] == "pending"))
    with col3:
        st.metric("Confirmed", sum(1 for a in alerts if a["status"] == "confirmed"))
    with col4:
        st.metric("Dismissed", sum(1 for a in alerts if a["status"] == "dismissed"))

    st.markdown("---")

    for a in alerts:
        risk = float(a.get("risk_score", 0))
        risk_color = "#ef4444" if risk >= 0.7 else "#f59e0b" if risk >= 0.4 else "#10b981"
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
            with col1:
                st.markdown(f"**Alert #{a['id'][:8]}**")
                st.caption(f"{a.get('fraud_type', 'Unknown')} · {format_datetime(a.get('created_at'))}")
            with col2:
                st.metric("Risk Score", f"{risk * 100:.1f}%")
            with col3:
                st.metric("Status", a["status"].title())
            with col4:
                st.metric("Order ID", (a.get("order_id") or "—")[:8])

            if a.get("risk_factors"):
                st.markdown("**Risk Factors:**")
                st.markdown(", ".join(f"`{f}`" for f in a["risk_factors"]))

            if a["status"] == "pending":
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✅ Confirm Fraud", key=f"confirm_{a['id']}"):
                        try:
                            client.table("fraud_logs").update({
                                "status": "confirmed",
                                "reviewed_by": user["id"],
                                "reviewed_at": "now()",
                            }).eq("id", a["id"]).execute()
                            st.success("Alert confirmed.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
                with col_b:
                    if st.button("❌ Dismiss", key=f"dismiss_{a['id']}"):
                        try:
                            client.table("fraud_logs").update({
                                "status": "dismissed",
                                "reviewed_by": user["id"],
                                "reviewed_at": "now()",
                            }).eq("id", a["id"]).execute()
                            st.success("Alert dismissed.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
