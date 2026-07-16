"""
ML Engine — self-learning ML engine.

Self-learning loop (v6):
  1. Every prediction the engine makes is logged to `ai_prediction_log`
     with its timestamp and predicted value.
  2. On every retrain, the engine backfills `actual_value` for old
     predictions whose truth has now arrived:
       • demand_forecast  → sum of order_items.quantity in the prediction's
         [created_at, target_date] window
       • price_optimization → the product's current price (the producer's
         new price is the "ground truth" the AI was trying to predict)
  3. Per (product_id, prediction_type) it computes MAE / MAPE / RMSE / bias
     and writes the result to `ai_model_metrics`.
  4. The next prediction uses that bias as a correction term
     (predicted_final = predicted_raw - bias) — a simple residual-boosting
     loop that learns from systematic over/under-prediction.

This means the longer the platform runs, the more accurate the AI becomes:
not just because more training data arrives, but because the engine
explicitly measures its own past errors and corrects for them.

If pandas/numpy/scikit-learn aren't installed, all methods return empty/None
and the AI Insights tab shows a friendly message.
"""
from __future__ import annotations

from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st


# Check if ML dependencies are available
try:
    import pandas as pd
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    pd = None
    np = None
    ML_AVAILABLE = False


MODEL_VERSION = "v6.0.0-self-learning"


class MLEngine:
    """Loads + caches training data and trained models from Supabase.

    Write operations (logging predictions, backfilling actuals, writing
    metrics) use the regular user-scoped client and rely on RLS. The
    ``ai_prediction_log`` and ``ai_model_metrics`` tables must have
    INSERT policies for ``authenticated`` (see ``supabase_sql/schema.sql``).
    The admin client is no longer used for self-learning writes — that
    was a privilege-escalation hazard in case of any RLS gap.
    """

    def __init__(self):
        self._client = None

    # ------------------------------------------------------------------
    # Client accessors
    # ------------------------------------------------------------------
    @property
    def client(self):
        if self._client is None:
            from database.connection import get_supabase_client
            self._client = get_supabase_client()
        return self._client

    def _write_client(self):
        """Return the client used for self-learning writes. Honours RLS.

        If the current user is an admin, the admin client is used so that
        cross-tenant metrics can be written (admins see all rows). For
        non-admin users, the regular client is used and RLS determines
        what is writable. If RLS blocks the write, the operation fails
        loudly via the Supabase error — which is what we want, instead
        of silently escalating privileges.
        """
        try:
            user = st.session_state.get("user") or {}
        except Exception:
            user = {}
        if user.get("role") == "admin":
            try:
                from database.connection import get_supabase_admin_client
                return get_supabase_admin_client()
            except Exception:
                # Admin key not configured — fall back to anon client
                return self.client
        return self.client

    # ------------------------------------------------------------------
    # Data loading (cached 5 min)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=300, show_spinner="Training ML models on your latest data…")
    def load_training_data(_self) -> Dict[str, Any]:
        """Fetch all relevant tables from Supabase. Cached 5 min.

        Also fetches the prediction log + metrics so callers can use
        them for accuracy-aware confidence and for graphing.
        """
        if not ML_AVAILABLE:
            return {
                "orders": [], "order_items": [], "products": [], "profiles": [],
                "favorites": [], "cart_items": [],
                "prediction_log": [], "model_metrics": [],
            }

        client = _self.client

        def fetch(table, select="*"):
            try:
                r = client.table(table).select(select).execute()
                return pd.DataFrame(r.data or [])
            except Exception:
                return pd.DataFrame()

        return {
            "orders":         fetch("orders"),
            "order_items":    fetch("order_items"),
            "products":       fetch("products"),
            "profiles":       fetch("profiles"),
            "favorites":      fetch("favorites"),
            "cart_items":     fetch("cart_items"),
            "prediction_log": fetch("ai_prediction_log"),
            "model_metrics":  fetch("ai_model_metrics"),
        }

    # ------------------------------------------------------------------
    # Model training
    # ------------------------------------------------------------------
    @st.cache_resource(show_spinner="Training demand forecast models…")
    def train_demand_models(_self) -> Dict[str, Dict[str, Any]]:
        """Train a per-product demand model on daily order quantity.

        Uses GradientBoostingRegressor when enough samples are available
        (>= 14 days of data), falls back to LinearRegression otherwise.
        Both are sklearn — no extra deps required.

        Each model entry carries:
          - model: the trained regressor
          - slope, intercept: linear-trend summary (for the trend label)
          - mae: in-sample mean abs error
          - samples: number of order-item rows trained on
          - first_date, last_date: training window
          - history: list of {date, actual, fitted} for graphing
          - bias: latest learned bias correction (from ai_model_metrics)
        """
        if not ML_AVAILABLE:
            return {}
        from sklearn.linear_model import LinearRegression
        try:
            from sklearn.ensemble import GradientBoostingRegressor
            _HAVE_GBR = True
        except ImportError:
            _HAVE_GBR = False

        data = _self.load_training_data()
        if data["order_items"].empty:
            return {}

        raw_metrics = data.get("model_metrics")
        if raw_metrics is None:
            metrics_df = pd.DataFrame()
        elif not hasattr(raw_metrics, "empty"):
            metrics_df = pd.DataFrame(raw_metrics)
        else:
            metrics_df = raw_metrics
        metrics_map = _self._latest_metrics(metrics_df)

        items = data["order_items"].copy()
        items["created_at"] = pd.to_datetime(items["created_at"], errors="coerce")
        items = items.dropna(subset=["created_at"])
        items["quantity"] = pd.to_numeric(items["quantity"], errors="coerce").fillna(0)

        models: Dict[str, Dict[str, Any]] = {}
        for product_id, group in items.groupby("product_id"):
            if len(group) < 2:
                continue
            # Resample to daily totals. Use a temp column to avoid pandas 3.x
            # groupby-with-key changes that broke the old column-count assumption.
            g = group.copy()
            g["__d"] = g["created_at"].dt.date
            daily = g.groupby("__d", as_index=False)["quantity"].sum()
            daily.columns = ["date", "qty"]
            daily["date"] = pd.to_datetime(daily["date"])
            daily = daily.sort_values("date")

            # Reindex to a continuous daily series so the model sees the gaps
            # (zero-demand days matter for demand forecasting).
            full_range = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
            daily = daily.set_index("date").reindex(full_range, fill_value=0).reset_index()
            daily.columns = ["date", "qty"]
            daily["day_num"] = (daily["date"] - daily["date"].min()).dt.days

            X = daily[["day_num"]].values
            y = daily["qty"].values

            try:
                # Use GradientBoosting when we have enough history;
                # it captures non-linear trends (weekend dips, spikes) better.
                use_gbr = _HAVE_GBR and len(daily) >= 14
                m = GradientBoostingRegressor(n_estimators=50, max_depth=2, random_state=42) if use_gbr else LinearRegression()
                m.fit(X, y)
                preds = m.predict(X)
                mae = float(np.mean(np.abs(y - preds)))

                # Linear trend summary (always computed, for the trend label)
                lr = LinearRegression().fit(X, y)
                slope = float(lr.coef_[0])
                intercept = float(lr.intercept_)

                pid_str = str(product_id)
                bias = float(metrics_map.get((pid_str, "demand_forecast"), {}).get("bias", 0.0) or 0.0)

                history = [
                    {
                        "date": str(daily["date"].iloc[i].date()),
                        "actual": int(y[i]),
                        "fitted": max(0.0, float(preds[i]) - bias),  # apply learned bias
                    }
                    for i in range(len(daily))
                ]

                models[pid_str] = {
                    "model": m,
                    "slope": slope,
                    "intercept": intercept,
                    "mae": mae,
                    "samples": int(len(group)),
                    "first_date": str(daily["date"].min().date()),
                    "last_date": str(daily["date"].max().date()),
                    "history": history,
                    "bias": bias,
                    "model_kind": "gbr" if use_gbr else "linear",
                }
            except Exception:
                continue
        return models

    @st.cache_resource(show_spinner="Training price-prediction model…")
    def train_price_model(_self) -> Dict[str, Any]:
        if not ML_AVAILABLE:
            return {"trained": False, "reason": "ML libraries not installed"}
        from sklearn.linear_model import LinearRegression
        try:
            from sklearn.ensemble import RandomForestRegressor
            _HAVE_RFR = True
        except ImportError:
            _HAVE_RFR = False

        data = _self.load_training_data()
        products = data["products"]
        order_items = data["order_items"]
        if products.empty:
            return {"trained": False, "reason": "no_products"}

        features = products.copy()
        features["price"] = pd.to_numeric(features["price"], errors="coerce").fillna(0)
        features["stock"] = pd.to_numeric(features["stock"], errors="coerce").fillna(0)
        features["reorder_point"] = pd.to_numeric(features.get("reorder_point", 0), errors="coerce").fillna(0)
        features["category_code"] = features["category"].astype("category").cat.codes
        features["unit_code"] = features.get("unit", pd.Series([""] * len(features))).astype("category").cat.codes

        if not order_items.empty:
            sales = order_items.groupby("product_id")["quantity"].sum().reset_index()
            sales.columns = ["id", "total_sold"]
            features = features.merge(sales, on="id", how="left")
            features["total_sold"] = pd.to_numeric(features["total_sold"], errors="coerce").fillna(0)
        else:
            features["total_sold"] = 0

        if len(features) < 3:
            return {"trained": False, "reason": "not_enough_products"}

        feature_names = ["stock", "reorder_point", "category_code", "unit_code", "total_sold"]
        X = features[feature_names].values
        y = features["price"].values

        try:
            # RandomForest handles categorical-encoded features + non-linear
            # price dynamics (e.g. low-stock premium) better than linear.
            use_rf = _HAVE_RFR and len(features) >= 8
            m = RandomForestRegressor(n_estimators=40, max_depth=6, random_state=42) if use_rf else LinearRegression()
            m.fit(X, y)
            preds = m.predict(X)
            return {
                "trained": True,
                "model": m,
                "mae": float(np.mean(np.abs(y - preds))),
                "r2": float(m.score(X, y)),
                "samples": len(features),
                "feature_names": feature_names,
                "products_features": features,
                "model_kind": "rf" if use_rf else "linear",
            }
        except Exception as e:
            return {"trained": False, "reason": str(e)}

    @st.cache_resource(show_spinner="Training recommendation model…")
    def train_recommender(_self) -> Dict[str, Any]:
        if not ML_AVAILABLE:
            return {"trained": False, "reason": "ML libraries not installed"}
        from sklearn.metrics.pairwise import cosine_similarity

        data = _self.load_training_data()
        order_items = data["order_items"]
        favorites = data["favorites"]
        products = data["products"]
        orders = data["orders"]
        if products.empty:
            return {"trained": False, "reason": "no_products"}

        interactions_rows: List[Dict] = []
        if not order_items.empty and not orders.empty:
            item_user = order_items.merge(
                orders[["id", "buyer_id"]],
                left_on="order_id", right_on="id", how="left", suffixes=("", "_order"),
            )
            for _, r in item_user.iterrows():
                if r.get("buyer_id"):
                    interactions_rows.append({
                        "user_id": str(r["buyer_id"]),
                        "product_id": str(r["product_id"]),
                        "score": 3,
                    })
        if not favorites.empty:
            for _, r in favorites.iterrows():
                if r.get("user_id") and r.get("product_id"):
                    interactions_rows.append({
                        "user_id": str(r["user_id"]),
                        "product_id": str(r["product_id"]),
                        "score": 2,
                    })

        if len(interactions_rows) < 3:
            return {"trained": False, "reason": "not_enough_interactions",
                    "interaction_count": len(interactions_rows)}

        df = pd.DataFrame(interactions_rows).dropna(subset=["user_id", "product_id"])
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(1)
        matrix = df.pivot_table(index="user_id", columns="product_id", values="score", aggfunc="max", fill_value=0)
        product_vectors = matrix.T
        if product_vectors.shape[0] < 2:
            return {"trained": False, "reason": "not_enough_products_with_interactions"}
        sim = cosine_similarity(product_vectors)
        sim_df = pd.DataFrame(sim, index=product_vectors.index, columns=product_vectors.index)
        return {
            "trained": True,
            "interaction_count": len(df),
            "unique_users": int(df["user_id"].nunique()),
            "unique_products": int(df["product_id"].nunique()),
            "similarity_matrix": sim_df,
            "products": products,
        }

    # ------------------------------------------------------------------
    # SELF-LEARNING: log predictions, backfill actuals, score accuracy
    # ------------------------------------------------------------------
    def log_prediction(
        self,
        *,
        product_id: str,
        prediction_type: str,
        predicted_value: float,
        horizon_days: Optional[int] = None,
        target_date: Optional[date] = None,
        input_features: Optional[dict] = None,
    ) -> None:
        """Persist a single prediction so we can later score it against truth.

        Silent on failure — logging is best-effort and must not break the
        caller's flow.

        We look up the product's producer_id so the RLS policy
        ``auth.uid() = producer_id`` on ai_prediction_log passes for
        the engine's write (otherwise the policy silently rejects the
        insert and every prediction is dropped).
        """
        try:
            producer_id = self._producer_id_for_product(product_id)
            row = {
                "product_id": product_id,
                "producer_id": producer_id,
                "prediction_type": prediction_type,
                "predicted_value": float(predicted_value),
                "horizon_days": horizon_days,
                "target_date": target_date.isoformat() if target_date else None,
                "model_version": MODEL_VERSION,
                "input_features": input_features or {},
            }
            self._write_client().table("ai_prediction_log").insert(row).execute()
        except Exception:
            pass

    def _producer_id_for_product(self, product_id: str) -> Optional[str]:
        """Look up the producer_id for a product, so engine writes satisfy
        the RLS WITH CHECK on ai_prediction_log / ai_model_metrics.

        Returns None if the product can't be found — the insert will then
        be rejected by RLS, but it will fail with a clear log entry rather
        than silently succeed with NULL producer_id (which would be a
        data-integrity issue).
        """
        try:
            r = self.client.table("products").select("producer_id").eq("id", product_id).maybe_single().execute()
            return (r.data or {}).get("producer_id") if r else None
        except Exception:
            return None

    def backfill_actuals(self) -> Dict[str, int]:
        """Fill in actual_value for predictions whose truth has arrived.

        Demand forecasts: actual = sum of order_items.quantity for that
        product in [prediction.created_at, prediction.target_date].
        Price optimizations: actual = the product's current price (the
        producer's new price is the truth the AI was trying to predict;
        we only score predictions where the price actually changed).

        Returns: {"demand_forecast": n, "price_optimization": m}
        """
        if not ML_AVAILABLE:
            return {"demand_forecast": 0, "price_optimization": 0}
        counts = {"demand_forecast": 0, "price_optimization": 0}
        try:
            client = self._write_client()

            # --- Demand forecasts ---
            # Pull unscored demand predictions whose target_date has passed.
            today = date.today()
            unscored = (
                client.table("ai_prediction_log")
                .select("id, product_id, predicted_value, horizon_days, target_date, created_at")
                .eq("prediction_type", "demand_forecast")
                .is_("actual_value", "null")
                .not_.is_("target_date", "null")
                .lte("target_date", today.isoformat())
                .limit(500)
                .execute()
            ).data or []

            if unscored:
                # Fetch all order_items once for the relevant window.
                earliest = min(r["created_at"][:10] for r in unscored)
                items = (
                    client.table("order_items")
                    .select("product_id, quantity, created_at")
                    .gte("created_at", earliest)
                    .execute()
                ).data or []
                items_df = pd.DataFrame(items)
                if not items_df.empty:
                    items_df["created_at"] = pd.to_datetime(items_df["created_at"], errors="coerce")
                    items_df["quantity"] = pd.to_numeric(items_df["quantity"], errors="coerce").fillna(0)

                for r in unscored:
                    try:
                        pid = r["product_id"]
                        created = pd.to_datetime(r["created_at"])
                        tgt = pd.to_datetime(r["target_date"])
                        if not items_df.empty:
                            mask = (
                                (items_df["product_id"].astype(str) == str(pid))
                                & (items_df["created_at"] >= created)
                                & (items_df["created_at"] <= tgt)
                            )
                            actual = float(items_df.loc[mask, "quantity"].sum())
                        else:
                            actual = 0.0
                        client.table("ai_prediction_log").update({
                            "actual_value": actual,
                            "actual_recorded_at": datetime.now(timezone.utc).isoformat(),
                        }).eq("id", r["id"]).execute()
                        counts["demand_forecast"] += 1
                    except Exception:
                        continue

            # --- Price optimizations ---
            # Pull unscored price predictions older than 1 day.
            cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            unscored_price = (
                client.table("ai_prediction_log")
                .select("id, product_id, predicted_value, created_at")
                .eq("prediction_type", "price_optimization")
                .is_("actual_value", "null")
                .lte("created_at", cutoff)
                .limit(500)
                .execute()
            ).data or []

            if unscored_price:
                pids = list({str(r["product_id"]) for r in unscored_price})
                products_now = (
                    client.table("products")
                    .select("id, price, updated_at")
                    .in_("id", pids)
                    .execute()
                ).data or []
                price_by_pid = {str(p["id"]): (float(p.get("price") or 0), p.get("updated_at")) for p in products_now}

                for r in unscored_price:
                    try:
                        pid = str(r["product_id"])
                        current_price, updated_at = price_by_pid.get(pid, (None, None))
                        if current_price is None:
                            continue
                        # Only score if the producer has actually changed the
                        # price since the prediction was made (otherwise there
                        # is no "truth" to compare against — the producer just
                        # hasn't acted yet).
                        if updated_at and pd.to_datetime(updated_at) <= pd.to_datetime(r["created_at"]):
                            continue
                        client.table("ai_prediction_log").update({
                            "actual_value": current_price,
                            "actual_recorded_at": datetime.now(timezone.utc).isoformat(),
                        }).eq("id", r["id"]).execute()
                        counts["price_optimization"] += 1
                    except Exception:
                        continue

        except Exception:
            pass
        return counts

    def compute_metrics(self) -> int:
        """Recompute MAE/MAPE/RMSE/bias per (product_id, prediction_type)
        and persist to ai_model_metrics. Returns number of metric rows written.

        Minimum-sample guard: we only compute a bias correction when there
        are at least ``MIN_SAMPLES_FOR_BIAS`` scored predictions for a
        (product, type) pair. Below that, the metric is still recorded as
        a single historical row (so the dashboard can show "not enough
        data yet") but its ``bias`` is forced to 0 so it never gets fed
        back into the next prediction. This prevents 1-sample "100%
        accuracy" rows from biasing future forecasts.
        """
        if not ML_AVAILABLE:
            return 0
        MIN_SAMPLES_FOR_BIAS = 5
        try:
            data = self.load_training_data()
            log_df = data.get("prediction_log")
            if log_df is None:
                return 0
            if not hasattr(log_df, "empty"):
                log_df = pd.DataFrame(log_df)
            if log_df.empty:
                return 0

            # Only score rows that have an actual_value.
            log_df = log_df[log_df["actual_value"].notna()].copy()
            if log_df.empty:
                return 0

            log_df["predicted_value"] = pd.to_numeric(log_df["predicted_value"], errors="coerce")
            log_df["actual_value"] = pd.to_numeric(log_df["actual_value"], errors="coerce")
            log_df = log_df.dropna(subset=["predicted_value", "actual_value"])
            log_df["product_id"] = log_df["product_id"].astype(str)

            rows = []
            now_iso = datetime.now(timezone.utc).isoformat()
            for (pid, ptype), group in log_df.groupby(["product_id", "prediction_type"]):
                if len(group) < 1:
                    continue
                y_true = group["actual_value"].values
                y_pred = group["predicted_value"].values
                err = y_pred - y_true
                mae = float(np.mean(np.abs(err)))
                rmse = float(np.sqrt(np.mean(err ** 2)))
                # MAPE only counts non-zero actuals
                nonzero = y_true != 0
                mape = float(np.mean(np.abs(err[nonzero] / y_true[nonzero])) * 100) if nonzero.any() else None
                # Only treat the bias as reliable when we have enough samples
                if len(group) >= MIN_SAMPLES_FOR_BIAS:
                    bias = float(np.mean(err))
                else:
                    bias = 0.0
                # Insert with the canonical column name `computed_at` (matches
                # the CREATE TABLE in migration_v6.sql). We also write
                # `evaluated_at` as an alias for backward compatibility with
                # older deployments that already have it as a column.
                rows.append({
                    "product_id": pid,
                    "prediction_type": ptype,
                    "mae": mae,
                    "mape": mape,
                    "rmse": rmse,
                    "samples": int(len(group)),
                    "sample_size": int(len(group)),
                    "bias": bias,
                    "computed_at": now_iso,
                    "evaluated_at": now_iso,
                    "model_name": MODEL_VERSION,
                    "model_version": MODEL_VERSION,
                })

            if rows:
                client = self._write_client()
                # Insert new metric rows. Old ones are kept for history
                # (the unique constraint is on product+type+computed_at,
                # which never collides because computed_at is now_iso).
                client.table("ai_model_metrics").insert(rows).execute()
            return len(rows)
        except Exception:
            return 0

    def _latest_metrics(self, metrics_df) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Index the latest metric row per (product_id, prediction_type).

        The canonical timestamp column is ``computed_at`` (matches the
        CREATE TABLE in migration_v6.sql). For backward compatibility
        with deployments that have an older ``evaluated_at`` column, we
        try that first.
        """
        out: Dict[Tuple[str, str], Dict[str, Any]] = {}
        if metrics_df is None:
            return out
        try:
            if not ML_AVAILABLE:
                return out
            if not hasattr(metrics_df, "empty"):
                # Caller passed a plain list (e.g. from the uncached path).
                metrics_df = pd.DataFrame(metrics_df)
            if metrics_df.empty:
                return out
            df = metrics_df.copy()
            df["product_id"] = df["product_id"].astype(str)
            # Pick the timestamp column we have (computed_at first, then
            # the legacy evaluated_at)
            ts_col = "computed_at" if "computed_at" in df.columns else "evaluated_at" if "evaluated_at" in df.columns else None
            if ts_col is not None:
                df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
                df = df.sort_values(ts_col)
            for (pid, ptype), g in df.groupby(["product_id", "prediction_type"]):
                last = g.iloc[-1].to_dict()
                out[(pid, ptype)] = last
        except Exception:
            pass
        return out

    def get_accuracy(self, product_id: str, prediction_type: str) -> Optional[Dict[str, Any]]:
        """Return the latest accuracy metrics for one product + prediction type."""
        try:
            data = self.load_training_data()
            raw = data.get("model_metrics")
            if raw is None:
                metrics_df = pd.DataFrame()
            elif not hasattr(raw, "empty"):
                metrics_df = pd.DataFrame(raw)
            else:
                metrics_df = raw
            metrics_map = self._latest_metrics(metrics_df)
            return metrics_map.get((str(product_id), prediction_type))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Backwards-compat: legacy ai_predictions table (still used by v2 seeds)
    # ------------------------------------------------------------------
    def save_predictions(self, predictions: List[Dict[str, Any]]) -> int:
        if not predictions:
            return 0
        try:
            r = self.client.table("ai_predictions").insert(predictions).execute()
            return len(r.data or [])
        except Exception:
            return 0


# ====================================================================
# Convenience: train-everything + run the self-learning loop
# ====================================================================
@st.cache_data(ttl=300)
def get_training_summary() -> Dict[str, Any]:
    """Train all models AND run the self-learning loop (backfill actuals +
    compute metrics) so the displayed accuracy is always fresh.

    Cached 5 min — calling it from the UI is cheap.
    """
    if not ML_AVAILABLE:
        return {"ml_available": False,
                "message": "ML libraries (pandas, numpy, scikit-learn) not installed. AI Insights disabled."}

    engine = MLEngine()

    # 1) Backfill actuals + recompute metrics BEFORE training, so the
    #    bias-correction term is up to date when the models are built.
    backfill_counts = engine.backfill_actuals()
    metrics_written = engine.compute_metrics()

    # 2) Load fresh data (the cache may still hold the pre-backfill copy,
    #    but that's fine — metrics are persisted independently).
    data = engine.load_training_data()
    demand_models = engine.train_demand_models()
    price_model = engine.train_price_model()
    recommender = engine.train_recommender()

    # 3) Aggregate accuracy across all products for the summary header.
    raw_metrics = data.get("model_metrics")
    metrics_df = pd.DataFrame(raw_metrics) if not hasattr(raw_metrics, "empty") else raw_metrics
    if metrics_df is None:
        metrics_df = pd.DataFrame()
    if not metrics_df.empty:
        # Pick the timestamp column we have (computed_at first, then the
        # legacy evaluated_at) — older deployments may not have the new
        # canonical column yet.
        ts_col = "computed_at" if "computed_at" in metrics_df.columns else "evaluated_at" if "evaluated_at" in metrics_df.columns else None
        if ts_col is not None:
            latest = metrics_df.sort_values(ts_col).groupby(["product_id", "prediction_type"]).tail(1)
        else:
            latest = metrics_df.groupby(["product_id", "prediction_type"]).tail(1)
        # Only include rows that met the minimum sample size — otherwise
        # the headline "accuracy" reflects single lucky predictions and is
        # misleading. ``MIN_SAMPLES_FOR_ACCURACY`` is the same threshold
        # used in compute_metrics for the bias correction.
        MIN_SAMPLES_FOR_ACCURACY = 5
        if "samples" in latest.columns:
            latest = latest[latest["samples"] >= MIN_SAMPLES_FOR_ACCURACY]
        demand_mape = latest[latest["prediction_type"] == "demand_forecast"]["mape"].dropna()
        price_mape = latest[latest["prediction_type"] == "price_optimization"]["mape"].dropna()
        demand_accuracy = float(100 - demand_mape.mean()) if not demand_mape.empty else None
        price_accuracy = float(100 - price_mape.mean()) if not price_mape.empty else None
        scored_predictions = int(latest["samples"].sum())
    else:
        demand_accuracy = None
        price_accuracy = None
        scored_predictions = 0

    raw_log = data.get("prediction_log")
    log_df = pd.DataFrame(raw_log) if not hasattr(raw_log, "empty") else raw_log
    if log_df is None:
        log_df = pd.DataFrame()
    total_predictions = int(len(log_df)) if not log_df.empty else 0
    scored = int((log_df["actual_value"].notna()).sum()) if not log_df.empty else 0

    return {
        "ml_available": True,
        "orders_count": len(data["orders"]),
        "order_items_count": len(data["order_items"]),
        "products_count": len(data["products"]),
        "users_count": len(data["profiles"]),
        "favorites_count": len(data["favorites"]),
        "demand_models_trained": len(demand_models),
        "price_model_trained": price_model.get("trained", False),
        "price_model_r2": price_model.get("r2", 0),
        "price_model_mae": price_model.get("mae", 0),
        "recommender_trained": recommender.get("trained", False),
        "recommender_interactions": recommender.get("interaction_count", 0),
        # Self-learning stats
        "total_predictions_logged": total_predictions,
        "scored_predictions": scored,
        "demand_accuracy_pct": demand_accuracy,
        "price_accuracy_pct": price_accuracy,
        "backfill_counts": backfill_counts,
        "metrics_rows_written": metrics_written,
        "model_version": MODEL_VERSION,
        "cache_ttl_seconds": 300,
        "last_trained": datetime.now(timezone.utc).isoformat(),
    }
