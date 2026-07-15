"""
Demand forecast module â€” predicts future demand for each product.

Returns BOTH the forecast and the historical fit so the UI can plot a
per-product chart of actuals vs fitted vs future forecast.

Every forecast is logged to ai_prediction_log so the engine can later
score its own accuracy and apply a bias correction.
"""
from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional
import streamlit as st
import pandas as pd
import numpy as np

from .engine import MLEngine


def forecast_demand(product_id: str, horizon_days: int = 30) -> Dict[str, Any]:
    """Forecast demand for a SINGLE product over the next horizon_days.

    Returns a dict with:
      - predicted_demand_30d, avg_daily_demand, peak_day, peak_qty, trend
      - confidence (now derived from past MAPE, not from sample count alone)
      - history: list of {date, actual, fitted}  (for the chart)
      - forecast: list of {date, predicted}      (for the chart)
      - accuracy: latest MAE/MAPE/samples for this product
    """
    engine = MLEngine()
    models = engine.train_demand_models()
    data = engine.load_training_data()

    product_id_str = str(product_id)
    if product_id_str not in models:
        # Fallback: use simple category average
        products = data["products"]
        prod = products[products["id"].astype(str) == product_id_str]
        if prod.empty:
            return {"predicted_demand": 0, "confidence": 0, "method": "no_data",
                    "history": [], "forecast": []}
        return {
            "predicted_demand": 10,
            "predicted_demand_30d": 10,
            "avg_daily_demand": 0.3,
            "peak_day": (date.today() + timedelta(days=7)).isoformat(),
            "peak_qty": 1.0,
            "trend": "stable",
            "confidence": 0.3,
            "method": "category_avg_fallback",
            "samples": 0,
            "history": [],
            "forecast": [],
            "accuracy": None,
        }

    m_info = models[product_id_str]
    m = m_info["model"]
    bias = m_info.get("bias", 0.0) or 0.0

    # Predict next horizon_days from the day after the last training day.
    last_day_num = int(m_info["samples"])  # rough proxy
    # Use the history's last day_num as the actual anchor so the forecast
    # starts right after the last observed day.
    history = m_info.get("history", [])
    if history:
        last_hist_date = datetime.fromisoformat(history[-1]["date"]).date()
        future_dates = [last_hist_date + timedelta(days=i + 1) for i in range(horizon_days)]
        # Use the day_num continuation. The history's last day_num is
        # (last_hist_date - first_date).days, which we can recompute.
        first_date = datetime.fromisoformat(history[0]["date"]).date()
        last_day_num = (last_hist_date - first_date).days
    else:
        future_dates = [date.today() + timedelta(days=i) for i in range(horizon_days)]

    future_days = np.arange(last_day_num + 1, last_day_num + 1 + horizon_days).reshape(-1, 1)
    future_preds = m.predict(future_days)
    # Apply learned bias correction + clip negatives to zero.
    future_preds = np.maximum(future_preds - bias, 0)

    total_demand = float(np.sum(future_preds))
    avg_daily = float(np.mean(future_preds))
    peak_day_idx = int(np.argmax(future_preds))
    peak_day_date = future_dates[peak_day_idx].isoformat()
    forecast_series = [
        {"date": future_dates[i].isoformat(), "predicted": float(future_preds[i])}
        for i in range(horizon_days)
    ]

    # Confidence: combine sample count with past accuracy (MAPE).
    # Lower MAPE â†’ higher confidence. If no metrics yet, fall back to
    # the in-sample MAE heuristic.
    accuracy = engine.get_accuracy(product_id_str, "demand_forecast")
    sample_conf = min(0.5, m_info["samples"] / 50)
    mae_conf = max(0, 1 - (m_info["mae"] / max(avg_daily, 1)))
    if accuracy and accuracy.get("mape") is not None:
        mape = float(accuracy["mape"])
        # accuracy_pct = 100 - mape; confidence = accuracy_pct / 100, clipped.
        acc_conf = max(0.1, min(0.95, (100.0 - mape) / 100.0))
        confidence = 0.3 * acc_conf + 0.4 * sample_conf + 0.3 * mae_conf
    else:
        confidence = 0.3 + sample_conf * 0.4 + mae_conf * 0.3
    confidence = float(np.clip(confidence, 0.1, 0.95))

    result = {
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
        "method": "linear_regression" if m_info.get("model_kind") == "linear" else "gradient_boosting",
        "first_date": m_info["first_date"],
        "last_date": m_info["last_date"],
        "history": history,
        "forecast": forecast_series,
        "accuracy": _format_accuracy(accuracy),
        "bias": round(bias, 3),
    }

    # ---- Log the prediction so we can later score it ----
    target_date = (datetime.fromisoformat(forecast_series[-1]["date"]).date()) if forecast_series else None
    try:
        engine.log_prediction(
            product_id=product_id_str,
            prediction_type="demand_forecast",
            predicted_value=total_demand,
            horizon_days=horizon_days,
            target_date=target_date,
            input_features={
                "method": result["method"],
                "samples": result["samples"],
                "trend": result["trend"],
                "bias_applied": result["bias"],
            },
        )
    except Exception:
        pass

    return result


def _format_accuracy(acc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not acc:
        return None
    return {
        "mae": float(acc.get("mae") or 0),
        "mape": float(acc.get("mape")) if acc.get("mape") is not None else None,
        "rmse": float(acc.get("rmse") or 0),
        "samples": int(acc.get("samples") or 0),
        "bias": float(acc.get("bias") or 0),
    }


def forecast_all_products(horizon_days: int = 30) -> List[Dict[str, Any]]:
    """Forecast demand for ALL products that have order history."""
    engine = MLEngine()
    data = engine.load_training_data()
    products = data["products"]

    results: List[Dict[str, Any]] = []
    for _, p in products.iterrows():
        product_id = str(p["id"])
        try:
            forecast = forecast_demand(product_id, horizon_days)
        except Exception:
            forecast = {"method": "no_data"}
        forecast["product_id"] = product_id
        forecast["sku"] = p.get("sku")
        forecast["name"] = p.get("name")
        forecast["category"] = p.get("category", "")
        forecast["current_stock"] = int(p.get("stock") or 0)
        results.append(forecast)

    return results


def save_demand_forecasts_to_supabase(forecasts: List[Dict[str, Any]]) -> int:
    """Persist demand forecasts to the ai_predictions table (legacy)."""
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
            "model_version": "v6.0.0-self-learning",
            "input_features": {
                "horizon_days": 30,
                "trend": f.get("trend"),
                "samples": f.get("samples"),
                "method": f.get("method"),
                "bias_applied": f.get("bias", 0),
            },
        })
    return engine.save_predictions(rows)
