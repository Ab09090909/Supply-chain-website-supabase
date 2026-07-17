"""
Price prediction module — recommends optimal prices for products.

Each prediction is logged to ai_prediction_log. When the producer later
changes the price, the engine backfills actual_value and computes MAPE
per product — that's the "price accuracy" the UI charts.

v7 update: now works with the new category-relative bounded model (which
pre-computes ``predicted_price`` per row in the features DataFrame) as
well as the legacy sklearn model. The v7 model replaces the broken v6
ML approach that was producing wild price predictions (MAPE >2000%).
"""
from __future__ import annotations

from typing import Any, Dict, List
import streamlit as st
import pandas as pd
import numpy as np

from .engine import MLEngine


def predict_optimal_prices() -> List[Dict[str, Any]]:
    """Predict optimal prices for ALL products. Returns list of dicts.

    Each dict now includes `accuracy` (MAE/MAPE/samples from past
    predictions) and `history` (predicted-vs-actual time series for the
    per-product chart).
    """
    engine = MLEngine()
    model_info = engine.train_price_model()

    if not model_info.get("trained"):
        return []

    features_df = model_info["products_features"]
    model_kind = model_info.get("model_kind", "legacy")
    model_status = model_info.get("status", "ok")
    model = model_info.get("model")  # None for the v7 bounded model
    feature_names = model_info.get("feature_names", [])

    data = engine.load_training_data()
    log_df = data.get("prediction_log")
    raw_metrics = data.get("model_metrics")
    if raw_metrics is None:
        metrics_df = pd.DataFrame()
    elif not hasattr(raw_metrics, "empty"):
        metrics_df = pd.DataFrame(raw_metrics)
    else:
        metrics_df = raw_metrics

    # Pre-index past predictions + metrics by product_id (string).
    past_by_pid: Dict[str, List[Dict[str, Any]]] = {}
    if log_df is not None and hasattr(log_df, "empty") and not log_df.empty:
        price_log = log_df[log_df["prediction_type"] == "price_optimization"].copy()
        if not price_log.empty:
            price_log["product_id"] = price_log["product_id"].astype(str)
            price_log["predicted_value"] = pd.to_numeric(price_log["predicted_value"], errors="coerce")
            price_log["actual_value"] = pd.to_numeric(price_log["actual_value"], errors="coerce")
            price_log["created_at"] = pd.to_datetime(price_log["created_at"], errors="coerce")
            for pid, g in price_log.groupby("product_id"):
                g = g.sort_values("created_at")
                past_by_pid[pid] = [
                    {
                        "predicted_at": str(r["created_at"].date()) if pd.notna(r["created_at"]) else "",
                        "predicted": float(r["predicted_value"]) if pd.notna(r["predicted_value"]) else None,
                        "actual": float(r["actual_value"]) if pd.notna(r["actual_value"]) else None,
                    }
                    for _, r in g.iterrows()
                ]

    metrics_by_pid: Dict[str, Dict[str, Any]] = {}
    if not metrics_df.empty:
        m = metrics_df[metrics_df["prediction_type"] == "price_optimization"].copy()
        if not m.empty:
            m["product_id"] = m["product_id"].astype(str)
            m["evaluated_at"] = pd.to_datetime(m["evaluated_at"], errors="coerce")
            m = m.sort_values("evaluated_at").groupby("product_id").tail(1)
            for _, row in m.iterrows():
                metrics_by_pid[str(row["product_id"])] = {
                    "mae": float(row.get("mae") or 0),
                    "mape": float(row["mape"]) if pd.notna(row.get("mape")) else None,
                    "rmse": float(row.get("rmse") or 0),
                    "samples": int(row.get("samples") or 0),
                    "bias": float(row.get("bias") or 0),
                }

    results: List[Dict[str, Any]] = []
    for _, row in features_df.iterrows():
        try:
            pid_str = str(row["id"])
            current_price = float(row["price"])

            # ---- v7 path: predicted_price is already computed in the
            # features DataFrame by the bounded category-relative formula.
            if model_kind == "category_relative_bounded" and "predicted_price" in row:
                predicted_price = float(row["predicted_price"])
                # Defense-in-depth clamp: never recommend halving or
                # doubling a product's price.
                if current_price > 0:
                    predicted_price = max(current_price * 0.5, min(current_price * 1.5, predicted_price))
                predicted_price = max(0.0, predicted_price)
            else:
                # ---- legacy sklearn path (kept for backward compat) ----
                if model is None or not feature_names:
                    continue
                X = row[feature_names].values.astype(float).reshape(1, -1)
                predicted_price = float(model.predict(X)[0])
                bias = float(metrics_by_pid.get(pid_str, {}).get("bias", 0.0) or 0.0)
                predicted_price = max(0.0, predicted_price - bias)

            diff = predicted_price - current_price
            pct_change = (diff / current_price * 100) if current_price > 0 else 0

            if pct_change > 5:
                recommendation = "increase"
            elif pct_change < -5:
                recommendation = "decrease"
            else:
                recommendation = "hold"

            m_acc = metrics_by_pid.get(pid_str)
            accuracy = m_acc if m_acc else None
            # Confidence: blend past accuracy with sample count. In the v7
            # model there is no R² (deterministic formula), so we lean on
            # past accuracy + sample count alone.
            n_with_sales = int(model_info.get("samples_with_sales", 0) or 0)
            sample_conf = min(0.5, n_with_sales / 50)
            if accuracy and accuracy.get("mape") is not None:
                # Softer curve than 100 - mape so one bad row doesn't nuke
                # the confidence for everyone. 0% MAPE → 1.0; 100% → 0.5;
                # 200%+ → 0.2.
                mape = float(accuracy["mape"])
                acc_pct = max(0.2, min(1.0, 1.0 - (mape / 200.0)))
                confidence = 0.6 * acc_pct + 0.4 * sample_conf
            else:
                confidence = 0.4 + sample_conf * 0.3
            # If we're in fallback mode (too little data), cap confidence
            # so the UI doesn't show a green "high confidence" badge on a
            # number that came from a flat baseline.
            if model_status != "ok" and confidence > 0.5:
                confidence = 0.45

            results.append({
                "product_id": pid_str,
                "sku": row["sku"],
                "name": row["name"],
                "current_price": current_price,
                "predicted_price": round(predicted_price, 2),
                "difference": round(diff, 2),
                "pct_change": round(pct_change, 1),
                "recommendation": recommendation,
                "confidence": round(float(np.clip(confidence, 0.1, 0.95)), 3),
                "bias": round(float(m_acc.get("bias", 0)) if m_acc else 0.0, 3),
                "history": past_by_pid.get(pid_str, []),
                "accuracy": accuracy,
                "model_kind": model_kind,
                "model_status": model_status,
            })

            # Log the prediction so it can be scored later.
            try:
                engine.log_prediction(
                    product_id=pid_str,
                    prediction_type="price_optimization",
                    predicted_value=predicted_price,
                    input_features={
                        "current_price": current_price,
                        "recommendation": recommendation,
                        "pct_change": round(pct_change, 1),
                        "model_kind": model_kind,
                        "model_status": model_status,
                    },
                )
            except Exception:
                pass

        except Exception:
            continue

    return results


def save_price_predictions_to_supabase(predictions: List[Dict[str, Any]]) -> int:
    """Persist price predictions to the ai_predictions table (legacy)."""
    engine = MLEngine()
    rows = []
    for p in predictions:
        rows.append({
            "product_id": p["product_id"],
            "prediction_type": "price_optimization",
            "predicted_value": p["predicted_price"],
            "confidence": p["confidence"],
            "model_version": "v7.0.0-bounded",
            "input_features": {
                "current_price": p["current_price"],
                "recommendation": p["recommendation"],
                "pct_change": p["pct_change"],
                "model_kind": p.get("model_kind", "legacy"),
                "model_status": p.get("model_status", "ok"),
            },
        })
    return engine.save_predictions(rows)
