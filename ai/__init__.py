"""
AI package — self-learning ML engine for the AI Supply Chain Platform.

Modules:
  • engine           — fetches Supabase data, trains & caches models
  • price_prediction — optimizes product prices
  • demand_forecast  — predicts future demand per product
  • recommendations  — recommends products to users (collaborative filtering)

All models retrain automatically every 5 minutes from the latest Supabase data.
As more orders/products/users accumulate, predictions naturally improve —
this is the "self-learning" behavior.
"""
from .engine import MLEngine, get_training_summary
from .price_prediction import predict_optimal_prices
from .demand_forecast import forecast_demand, forecast_all_products
from .recommendations import get_recommendations

__all__ = [
    "MLEngine",
    "get_training_summary",
    "predict_optimal_prices",
    "forecast_demand",
    "forecast_all_products",
    "get_recommendations",
]
