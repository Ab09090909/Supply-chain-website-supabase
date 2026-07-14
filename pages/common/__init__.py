"""Common pages shared across all roles — marketplace, AI insights, notifications."""
from .marketplace import render_shared_marketplace
from .ai_insights import render_ai_insights
from .notifications import render_notifications

__all__ = [
    "render_shared_marketplace",
    "render_ai_insights",
    "render_notifications",
]
