"""
Live Analytics Dashboard — only available when deployed on Render
(with a persistent disk for analytics data).

This is a server-side analytics dashboard that:
  • Tracks page views, button clicks, QR scans, downloads in real-time
  • Stores events in a JSONL file on a persistent disk (Render $1/mo)
  • Aggregates into beautiful interactive Plotly charts
  • Provides time-range filters (24h / 7d / 30d / all-time)
  • Exports as CSV / PNG for reports
  • Shows a "persistent mode" badge so you know your data survives restarts

Why is this Render-only?
  • Streamlit Cloud's filesystem is ephemeral — analytics would reset on
    every restart, making the dashboard useless
  • Streamlit Cloud restricts WebSocket / long-running connections
  • The interactive Plotly charts need a stable server process
  • The data collection requires a persistent disk mount
"""
from __future__ import annotations

import io
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

import streamlit as st
import pandas as pd

from auth.session import get_current_user, get_current_role
from utils.ui import page_header


# ---------------------------------------------------------------------------
# Optional: try to import plotly. If not available, we fall back to native
# Streamlit charts (which are also interactive, just less pretty).
# ---------------------------------------------------------------------------
try:
    import plotly.express as px
    import plotly.graph_objects as go
    _HAVE_PLOTLY = True
except Exception:
    _HAVE_PLOTLY = False


def _is_render_environment() -> bool:
    """Detect if we're running on Render (vs Streamlit Cloud / local).

    Render sets the RENDER env var, and the persistent disk is mounted
    at /var/data. Either signal means we're on Render.
    """
    import os
    if os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL"):
        return True
    # Persistent disk mounted?
    if os.path.isdir("/var/data"):
        return True
    return False


def _track_this_page() -> None:
    """Record that the user is viewing the analytics dashboard."""
    try:
        from utils.event_tracking.analytics_collector import track
        user = get_current_user() or {}
        track(
            "page_view",
            user_id=user.get("id"),
            user_role=(user.get("role") or "").lower() or None,
            page="analytics_dashboard",
        )
    except Exception:
        pass


def render_analytics_dashboard() -> None:
    """Render the live analytics dashboard.

    Available to ALL roles (producers / merchants / customers / admins).
    Each user sees their own analytics (filtered by user_id) so the
    dashboard is personal.
    """
    page_header(
        "📊 Live Analytics",
        "Real-time charts of your activity on the platform",
    )

    # Track this page view
    _track_this_page()

    # Banner: tell the user what platform we're on
    on_render = _is_render_environment()
    try:
        from utils.event_tracking.analytics_collector import is_persistent
        persistent = is_persistent()
    except Exception:
        persistent = False

    if on_render and persistent:
        st.success(
            "✅ **Live mode active** — your analytics are being written to "
            "a persistent disk and will survive app restarts."
        )
    elif on_render:
        st.info(
            "ℹ️ **Running on Render** — analytics are working but data is "
            "currently in ephemeral storage. Add a persistent disk in "
            "Render's settings to keep data across restarts."
        )
    else:
        st.warning(
            "⚠️ **Not running on Render** — analytics work but data will be "
            "lost on the next app restart. Deploy to Render with a "
            "persistent disk for the full experience."
        )

    # ---- Load events ----
    try:
        from utils.event_tracking.analytics_collector import (
            load_events, aggregate_by_day, aggregate_by_type,
            aggregate_by_page, stats_summary,
        )
    except Exception as e:
        st.error(f"Failed to load analytics module: {e}")
        return

    # ---- Time range filter ----
    range_col, refresh_col = st.columns([3, 1])
    with range_col:
        time_range = st.selectbox(
            "📅 Time range",
            options=["Last 24 hours", "Last 7 days", "Last 30 days", "All time"],
            index=2,
            key="analytics_time_range",
        )
    with refresh_col:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # Compute the since_epoch
    now = int(time.time())
    if time_range == "Last 24 hours":
        since = now - 86400
    elif time_range == "Last 7 days":
        since = now - 7 * 86400
    elif time_range == "Last 30 days":
        since = now - 30 * 86400
    else:
        since = None

    # ---- Filter by user (each user sees their own data) ----
    user = get_current_user() or {}
    role = (user.get("role") or "").lower()
    user_id = user.get("id")
    is_admin = role == "admin"

    all_events = load_events(since_epoch=since)
    if is_admin:
        events = all_events  # admins see everything
    else:
        events = [e for e in all_events if e.get("user_id") == user_id]

    if not events:
        st.info("📭 No events in this time range. Interact with the app to generate data!")
        return

    # ---- Header KPIs ----
    summary = stats_summary(events)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📊 Total events", summary["total_events"])
    k2.metric("👤 Unique users", summary["unique_users"])
    if summary["last_event"]:
        last_dt = datetime.fromtimestamp(summary["last_event"], tz=timezone.utc)
        k3.metric("🕒 Last event", last_dt.strftime("%Y-%m-%d %H:%M UTC"))
    if summary["first_event"]:
        first_dt = datetime.fromtimestamp(summary["first_event"], tz=timezone.utc)
        days_tracked = max(1, (now - summary["first_event"]) // 86400)
        k4.metric("📅 Tracking for", f"{days_tracked} day(s)")

    st.markdown("---")

    # ---- Events over time (line chart) ----
    st.markdown("### 📈 Events over time")
    by_day = aggregate_by_day(events)
    if by_day:
        df = pd.DataFrame(
            sorted(by_day.items()),
            columns=["Date", "Count"],
        )
        df["Date"] = pd.to_datetime(df["Date"])
        if _HAVE_PLOTLY:
            fig = px.line(
                df, x="Date", y="Count",
                title="Events per day",
                markers=True,
                color_discrete_sequence=["#10b981"],
            )
            fig.update_layout(
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            fig.update_traces(
                line=dict(width=3),
                marker=dict(size=10, color="#10b981", line=dict(width=2, color="white")),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(df.set_index("Date"))

    # ---- Two-column layout: event types + top pages ----
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎯 Event types")
        by_type = aggregate_by_type(events)
        if by_type:
            df_t = pd.DataFrame(
                sorted(by_type.items(), key=lambda kv: -kv[1]),
                columns=["Event", "Count"],
            )
            if _HAVE_PLOTLY:
                fig = px.bar(
                    df_t, x="Count", y="Event",
                    orientation="h",
                    title="Events by type",
                    color="Count",
                    color_continuous_scale=["#a7f3d0", "#10b981", "#047857"],
                )
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    yaxis={"categoryorder": "total ascending"},
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(df_t.set_index("Event"))

    with col2:
        st.markdown("### 📄 Top pages")
        top_pages = aggregate_by_page(events, top_n=10)
        if top_pages:
            df_p = pd.DataFrame(top_pages, columns=["Page", "Count"])
            if _HAVE_PLOTLY:
                fig = px.pie(
                    df_p, values="Count", names="Page",
                    title="Page views (top 10)",
                    color_discrete_sequence=px.colors.sequential.Greens,
                    hole=0.4,
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(df_p, use_container_width=True, hide_index=True)

    # ---- Hourly heatmap (when in the day are users most active?) ----
    st.markdown("### ⏰ Activity by hour of day")
    if events:
        # Build a heatmap: day-of-week × hour
        heatmap_data: Dict[int, Dict[int, int]] = {}
        for e in events:
            ts = e.get("epoch", 0)
            if not ts:
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            dow = dt.weekday()  # 0=Monday, 6=Sunday
            hr = dt.hour
            heatmap_data.setdefault(dow, {}).setdefault(hr, 0)
            heatmap_data[dow][hr] += 1

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        z = [[heatmap_data.get(d, {}).get(h, 0) for h in range(24)] for d in range(7)]

        if _HAVE_PLOTLY:
            fig = go.Figure(data=go.Heatmap(
                z=z,
                x=[f"{h:02d}:00" for h in range(24)],
                y=days,
                colorscale="Greens",
                hovertemplate="<b>%{y}</b> at <b>%{x}</b><br>Events: %{z}<extra></extra>",
            ))
            fig.update_layout(
                title="When are you most active?",
                xaxis_title="Hour (UTC)",
                yaxis_title="Day of week",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Install `plotly` to see the activity heatmap.")

    # ---- User-role breakdown (admin only) ----
    if is_admin and events:
        st.markdown("### 👥 Events by user role")
        role_counts: Dict[str, int] = {}
        for e in events:
            r = e.get("user_role") or "anonymous"
            role_counts[r] = role_counts.get(r, 0) + 1
        if role_counts:
            df_r = pd.DataFrame(
                sorted(role_counts.items(), key=lambda kv: -kv[1]),
                columns=["Role", "Count"],
            )
            if _HAVE_PLOTLY:
                fig = px.bar(
                    df_r, x="Role", y="Count",
                    color="Role",
                    title="Activity by user role",
                    color_discrete_sequence=["#10b981", "#34d399", "#6ee7b7", "#a7f3d0", "#fbbf24"],
                )
                st.plotly_chart(fig, use_container_width=True)

    # ---- Recent events table ----
    st.markdown("### 📋 Recent events (newest first)")
    df_recent = pd.DataFrame([
        {
            "Time": datetime.fromtimestamp(e["epoch"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "Type": e.get("event_type", ""),
            "Page": e.get("page", ""),
            "User": (e.get("user_id") or "")[:8] + "…" if e.get("user_id") else "anon",
            "Role": e.get("user_role") or "—",
            "Metadata": json.dumps(e.get("metadata") or {}, ensure_ascii=False)[:80],
        }
        for e in events[:30]
    ])
    st.dataframe(df_recent, use_container_width=True, hide_index=True)

    # ---- Export buttons ----
    st.markdown("---")
    st.markdown("### 💾 Export")
    exp_col1, exp_col2 = st.columns(2)

    with exp_col1:
        # CSV export
        csv_buf = io.StringIO()
        df_full = pd.DataFrame(events)
        df_full.to_csv(csv_buf, index=False)
        st.download_button(
            label="⬇️ Download as CSV",
            data=csv_buf.getvalue(),
            file_name=f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with exp_col2:
        # JSON export
        json_str = json.dumps(events, indent=2, ensure_ascii=False)
        st.download_button(
            label="⬇️ Download as JSON",
            data=json_str,
            file_name=f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )

    # ---- Admin: clear data button ----
    if is_admin:
        with st.expander("⚠️ Admin: Clear analytics data", expanded=False):
            st.warning(
                "This will permanently delete all analytics events. "
                "This action cannot be undone."
            )
            confirm = st.text_input(
                "Type 'DELETE' to confirm",
                key="analytics_delete_confirm",
            )
            if st.button("🗑️ Clear all analytics", type="primary"):
                if confirm == "DELETE":
                    try:
                        from utils.event_tracking.analytics_collector import clear_all
                        n = clear_all()
                        st.success(f"Deleted {n} events.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")
                else:
                    st.error("Type 'DELETE' to confirm.")


# ---------------------------------------------------------------------------
# Sidebar nav entry — adds an "Analytics" link to the sidebar for all roles
# ---------------------------------------------------------------------------
def add_analytics_to_sidebar() -> None:
    """Inject the analytics link into the sidebar (called from app.py)."""
    try:
        user = get_current_user() or {}
        if not user:
            return
        with st.sidebar:
            st.markdown("---")
            if st.button("📊 Live Analytics", key="nav_analytics", use_container_width=True):
                st.session_state["force_nav"] = "analytics"
                st.rerun()
    except Exception:
        pass
