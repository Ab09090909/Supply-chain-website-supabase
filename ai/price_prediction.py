"""
Price prediction module — recommends optimal prices for products.

Uses the MLEngine's trained price model (linear regression on stock, reorder
point, category, sales velocity) to suggest a price for each product.
"""
from __future__ import annotations

from typing import Any, Dict, List
import streamlit as st
import pandas as pd
import numpy as np

from .engine import MLEngine


def predict_optimal_prices() -> List[Dict[str, Any]]:
    """Predict optimal prices for ALL products. Returns list of dicts."""
    engine = MLEngine()
    model_info = engine.train_price_model()

    if not model_info.get("trained"):
        return []

    model = model_info["model"]
    features_df = model_info["products_features"]
    feature_names = model_info["feature_names"]

    results: List[Dict[str, Any]] = []
    for _, row in features_df.iterrows():
        try:
            X = row[feature_names].values.astype(float).reshape(1, -1)
            predicted_price = float(model.predict(X)[0])
            current_price = float(row["price"])
            diff = predicted_price - current_price
            pct_change = (diff / current_price * 100) if current_price > 0 else 0

            # Recommendation logic
            if pct_change > 5:
                recommendation = "increase"
            elif pct_change < -5:
                recommendation = "decrease"
            else:
                recommendation = "hold"

            results.append({
                "product_id": row["id"],
                "sku": row["sku"],
                "name": row["name"],
                "current_price": current_price,
                "predicted_price": round(predicted_price, 2),
                "difference": round(diff, 2),
                "pct_change": round(pct_change, 1),
                "recommendation": recommendation,
                "confidence": 0.5 + min(0.4, model_info.get("r2", 0) / 2),
            })
        except Exception:
            continue

    return results


def save_price_predictions_to_supabase(predictions: List[Dict[str, Any]]) -> int:
    """Persist price predictions to the ai_predictions table."""
    engine = MLEngine()
    rows = []
    for p in predictions:
        rows.append({
            "product_id": p["product_id"],
            "prediction_type": "price_optimization",
            "predicted_value": p["predicted_price"],
            "confidence": p["confidence"],
            "model_version": "v2.0.0",
            "input_features": {
                "current_price": p["current_price"],
                "recommendation": p["recommendation"],
                "pct_change": p["pct_change"],
            },
        })
    return engine.save_predictions(rows)
