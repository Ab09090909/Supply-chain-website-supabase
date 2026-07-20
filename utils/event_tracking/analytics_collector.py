"""
Server-side event collector for the live analytics dashboard.

What this does
---------------
Captures user actions (page views, button clicks, QR scans, etc.) in a
persistent JSONL file and exposes aggregation helpers for the dashboard.

Why a file instead of Supabase?
  • On Streamlit Cloud the filesystem is ephemeral — analytics data
    would vanish on every restart.
  • On Render with a $1/mo persistent disk, the file survives restarts
    and gives us a true server-side analytics pipeline without paying
    for an external service (Plausible, Umami, etc.).
  • JSONL is append-only and easy to grep / parse / migrate later.

Privacy
-------
We never log IP addresses, user agents, or any PII. We log:
  • event_id      — UUID for the event
  • timestamp     — ISO 8601 UTC
  • event_type    — page_view | qr_scan | card_download | order_placed
  • user_id       — the logged-in user (NULL for anonymous)
  • user_role     — producer / merchant / customer / admin (NULL anonymous)
  • page          — e.g. "profile", "marketplace", "?card=abc-123"
  • metadata      — event-specific JSON (e.g. {"product_id": "..."})
  • app_url       — which domain the event came from (for custom-domain analytics)
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# The directory where analytics events are stored.
# On Render, mount a persistent disk at /var/data (see render.yaml).
# On local dev / Streamlit Cloud, fall back to /tmp (ephemeral, but
# at least the code doesn't crash).
_DEFAULT_DATA_DIR = os.environ.get("ANALYTICS_DATA_DIR", "/var/data/analytics")
_LOCAL_FALLBACK  = os.path.join(os.path.expanduser("~"), ".eschain", "analytics")


def _resolve_data_dir() -> Path:
    """Find the analytics data directory, falling back gracefully.

    Order:
      1. ``$ANALYTICS_DATA_DIR`` env var (best — set this on Render)
      2. ``/var/data/analytics`` (Render's recommended persistent disk mount)
      3. ``~/.eschain/analytics`` (local dev fallback)
    """
    candidates = [_DEFAULT_DATA_DIR, _LOCAL_FALLBACK, "/tmp/eschain-analytics"]
    for d in candidates:
        try:
            p = Path(d)
            p.mkdir(parents=True, exist_ok=True)
            # Test writability
            test = p / ".write_test"
            test.write_text("ok")
            test.unlink()
            return p
        except Exception:
            continue
    # Last resort — in-memory (events lost on restart)
    return Path("/tmp/eschain-analytics")


_DATA_DIR = _resolve_data_dir()
_EVENTS_FILE = _DATA_DIR / "events.jsonl"


def is_persistent() -> bool:
    """Return True if analytics are being written to a persistent disk.

    Useful for showing the user a "✓ data persists across restarts" badge
    vs "⚠ running in ephemeral mode" warning.

    On Render free tier (no disk), the data dir is /tmp and this
    returns False. To make it True, add a Render disk and set
    ANALYTICS_DATA_DIR=/var/data/analytics.
    """
    return str(_DATA_DIR).startswith("/var/data/")


def track(
    event_type: str,
    *,
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
    page: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record an analytics event. Silent on failure (best-effort)."""
    try:
        # Try to detect the app URL (for multi-domain analytics)
        try:
            from utils.app_url import get_app_url
            app_url = get_app_url()
        except Exception:
            app_url = "unknown"

        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "epoch": int(time.time()),
            "event_type": event_type,
            "user_id": user_id,
            "user_role": user_role,
            "page": page,
            "app_url": app_url,
            "metadata": metadata or {},
        }
        # Append to the JSONL file
        with _EVENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Never let analytics break the app
        pass


def load_events(
    *,
    since_epoch: Optional[int] = None,
    event_type: Optional[str] = None,
    limit: int = 10000,
) -> List[Dict[str, Any]]:
    """Load events from the JSONL file, newest first.

    Args:
        since_epoch: only return events after this Unix timestamp.
                     Useful for "last 24h" / "last 7d" filters.
        event_type:  only return events of this type (e.g. "qr_scan").
        limit:       max events to return (default 10k).
    """
    if not _EVENTS_FILE.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        # Read backwards (newest first) by reading the whole file and
        # reversing — fine for ~10k events. For very large files we'd
        # use a tail-style approach.
        with _EVENTS_FILE.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):
            if len(out) >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if since_epoch is not None and (e.get("epoch") or 0) < since_epoch:
                continue
            if event_type and e.get("event_type") != event_type:
                continue
            out.append(e)
    except Exception:
        return out
    return out


def aggregate_by_day(events: List[Dict[str, Any]]) -> Dict[str, int]:
    """Return {YYYY-MM-DD: count} for the given events."""
    out: Dict[str, int] = {}
    for e in events:
        ts = e.get("timestamp") or ""
        # ISO 8601 like "2026-07-20T17:40:12+00:00"
        day = ts[:10] if len(ts) >= 10 else "unknown"
        out[day] = out.get(day, 0) + 1
    return out


def aggregate_by_type(events: List[Dict[str, Any]]) -> Dict[str, int]:
    """Return {event_type: count} for the given events."""
    out: Dict[str, int] = {}
    for e in events:
        t = e.get("event_type") or "unknown"
        out[t] = out.get(t, 0) + 1
    return out


def aggregate_by_page(events: List[Dict[str, Any]], top_n: int = 10) -> List[tuple]:
    """Return [(page, count), ...] sorted by count, top N."""
    out: Dict[str, int] = {}
    for e in events:
        p = e.get("page") or "unknown"
        out[p] = out.get(p, 0) + 1
    return sorted(out.items(), key=lambda kv: -kv[1])[:top_n]


def stats_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a high-level summary for the dashboard header."""
    if not events:
        return {
            "total_events": 0,
            "unique_users": 0,
            "unique_sessions": 0,
            "first_event": None,
            "last_event": None,
        }
    user_ids = {e.get("user_id") for e in events if e.get("user_id")}
    timestamps = [e.get("epoch", 0) for e in events]
    return {
        "total_events": len(events),
        "unique_users": len(user_ids),
        "first_event": min(timestamps) if timestamps else None,
        "last_event": max(timestamps) if timestamps else None,
    }


def clear_all() -> int:
    """Wipe the analytics file. Returns the number of events deleted.

    Admin-only — useful for testing or starting fresh. Returns 0 if
    the file doesn't exist.
    """
    if not _EVENTS_FILE.exists():
        return 0
    try:
        n = sum(1 for _ in _EVENTS_FILE.open("r", encoding="utf-8"))
        _EVENTS_FILE.unlink()
        return n
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Module test (run as ``python -m utils.event_tracking.analytics_collector``)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Analytics collector self-test")
    print(f"  Data dir:   {_DATA_DIR}")
    print(f"  Events file:{_EVENTS_FILE}")
    print(f"  Persistent: {is_persistent()}")
    print()
    track("test_event", user_id="u1", user_role="admin", page="self_test")
    events = load_events(limit=5)
    print(f"  Loaded {len(events)} event(s). Summary:")
    print(f"   ", stats_summary(events))
