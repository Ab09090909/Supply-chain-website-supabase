"""Common pages shared across all roles — marketplace, AI insights, notifications, product detail, assistant, merchant requests."""
from .marketplace import render_shared_marketplace
from .ai_insights import render_ai_insights
from .notifications import render_notifications
from .product_detail import render_product_detail
from .ai_assistant import render_ai_assistant
from .merchant_requests import render_merchant_requests

__all__ = [
    "render_shared_marketplace",
    "render_ai_insights",
    "render_notifications",
    "render_product_detail",
    "render_ai_assistant",
    "render_merchant_requests",
]
