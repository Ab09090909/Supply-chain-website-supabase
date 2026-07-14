"""
Demand forecast module — predicts future demand for each product.

Uses the MLEngine's per-product time-series models (linear regression on
daily order quantity over time) to predict demand for the next N days.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import streamlit as st
import pandas as pd
import numpy as np

from .engine import MLEngine


def forecast_demand(product_id: str, horizon_days: int = 30) -> Dict[str, Any]:
    """Forecast demand for a SINGLE product over the next horizon_days."""
    engine = MLEngine()
    models = engine.train_demand_models()
    data = engine.load_training_data()

    product_id_str = str(product_id)
    if product_id_str not in models:
        # Fallback: use simple category average
        products = data["products"]
        prod = products[products["id"].astype(str) == product_id_str]
        if prod.empty:
            return {"predicted_demand": 0, "confidence": 0, "method": "no_data"}
        return {
            "predicted_demand": 10,
            "confidence": 0.3,
            "method": "category_avg_fallback",
            "samples": 0,
        }

    m_info = models[product_id_str]
    m = m_info["model"]

    # Predict next horizon_days
    last_day_num = m_info["samples"]  # rough proxy
    future_days = np.arange(last_day_num, last_day_num + horizon_days).reshape(-1, 1)
    future_preds = m.predict(future_days)
    future_preds = np.maximum(future_preds, 0)  # no negative demand

    total_demand = float(np.sum(future_preds))
    avg_daily = float(np.mean(future_preds))
    peak_day_idx = int(np.argmax(future_preds))
    peak_day_date = (datetime.utcnow() + timedelta(days=peak_day_idx)).strftime("%Y-%m-%d")

    # Confidence: based on sample size + model fit (MAE)
    sample_conf = min(0.5, m_info["samples"] / 50)
    mae_conf = max(0, 1 - (m_info["mae"] / max(avg_daily, 1)))
    confidence = 0.3 + sample_conf * 0.4 + mae_conf * 0.3
    confidence = float(np.clip(confidence, 0.1, 0.95))

    return {
        "product_id": product_id_str,
        "predicted_demand_30d": round(total_demand, 1),
        "avg_daily_demand": round(avg_daily, 2),
        "peak_day": peak_day_date,
        "peak_qty": round(float(future_preds[peak_day_idx]), 1),
        "trend": "increasing" if m_info["slope"] > 0 else "decreasing" if m_info["slope"] < 0 else "stable",
        "slope": round(m_info["slope"], 3),
        "mae": round(m_info["mae"], 2),
        "samples": m_info["samples"],
        "confidence": round(confidence, 3),
        "method": "linear_regression",
        "first_date": m_info["first_date"],
        "last_date": m_info["last_date"],
    }


def forecast_all_products(horizon_days: int = 30) -> List[Dict[str, Any]]:
    """Forecast demand for ALL products that have order history."""
    engine = MLEngine()
    data = engine.load_training_data()
    products = data["products"]

    results: List[Dict[str, Any]] = []
    for _, p in products.iterrows():
        product_id = str(p["id"])
        forecast = forecast_demand(product_id, horizon_days)
        forecast["product_id"] = product_id
        forecast["sku"] = p["sku"]
        forecast["name"] = p["name"]
        forecast["category"] = p.get("category", "")
        forecast["current_stock"] = int(p["stock"])
        results.append(forecast)

    return results


def save_demand_forecasts_to_supabase(forecasts: List[Dict[str, Any]]) -> int:
    """Persist demand forecasts to the ai_predictions table."""
    engine = MLEngine()
    rows = []
    for f in forecasts:
        if f.get("method") == "no_data":
            continue
        rows.append({
            "product_id": f["product_id"],
            "prediction_type": "demand_forecast",
            "predicted_value": f.get("predicted_demand_30d", 0),
            "confidence": f.get("confidence", 0),
            "model_version": "v2.0.0",
            "input_features": {
                "horizon_days": 30,
                "trend": f.get("trend"),
                "samples": f.get("samples"),
                "method": f.get("method"),
            },
        })
    return engine.save_predictions(rows)
