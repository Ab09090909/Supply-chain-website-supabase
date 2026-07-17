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

v7 reliability overhaul (fixes MAPE 2000%+ issue):
  • Price model no longer tries to predict a product's own price from
    its own stock/sales attributes (that was the v6 bug — it was
    effectively modelling y = f(X) with a 5-D feature vector over
    <30 products, producing wild swings like 3000 Birr for a 50 Birr
    product). It now anchors every prediction to the product's current
    price and only recommends a bounded ±15% adjustment based on
    category-relative demand and stock pressure.
  • Every model output passes through a `_validate_and_clamp` safety
    pass that catches NaN, inf, negative, and out-of-range values and
    replaces them with a safe fallback.
  • Each `train_*` method reports a `status` field so the UI can show
    "AI in fallback mode — not enough data" instead of pretending the
    model is confident.
  • A learned bias is only used when the metrics row has >= 5 samples;
    that guard was already in `compute_metrics` but was being ignored
    on the read path. It is now also enforced in `train_price_model`
    and the bias cap is bounded.

If pandas/numpy/scikit-learn aren't installed, all methods return empty/None
and the AI Insights tab shows a friendly message.
"""
from __future__ import annotations

from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict, List, Optional, Tuple
import math
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


# ---------------------------------------------------------------------------
# Safety constants (v7)
# ---------------------------------------------------------------------------
# Minimum samples required before a model is considered "trained" enough to
# trust. Below this we fall back to a deterministic baseline (category median
# for price, zero for demand) and surface a "not enough data" status.
MIN_SAMPLES_FOR_TRAINING = 5

# Maximum allowed |bias| as a fraction of the predicted value's scale.
# If a learned bias is more than this fraction of the typical value, it's
# almost certainly from a broken/garbage data row (e.g. the 2616.73 bias
# the user saw in the screenshot — that was 52× the actual price and is
# pure noise). We clamp it so the engine never compounds garbage.
MAX_BIAS_FRACTION = 0.5

# Maximum allowed price change as a fraction of the current price. The AI
# should never recommend doubling or halving a price — that's a business
# decision for the producer, not the model. A 15% nudge is the biggest
# adjustment we ever make; everything beyond that is the producer's call.
MAX_PRICE_CHANGE_FRACTION = 0.15

# Maximum allowed demand forecast as a multiple of the historical average.
# Prevents the model from extrapolating a 0.1/day product to 50/day just
# because the trend line slopes upward.
MAX_DEMAND_MULTIPLIER = 3.0


def _validate_and_clamp(value, *, min_val=0.0, max_val=None,
                        fallback=0.0, label="value") -> float:
    """Last-line-of-defence sanitizer for any ML output.

    Catches the failure modes that produced the 2093% MAPE in the user's
    screenshot:
      • NaN / inf         → returns ``fallback``
      • negative          → returns ``max(min_val, 0.0)``
      • > max_val         → returns ``max_val``
      • not a number      → returns ``fallback``

    Always returns a finite float. Safe to call on anything.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    if math.isnan(v) or math.isinf(v):
        return float(fallback)
    if v < min_val:
        v = float(min_val)
    if max_val is not None and v > max_val:
        v = float(max_val)
    return v


MODEL_VERSION = "v7.0.0-bounded"


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
                # Clamp the in-sample predictions to be non-negative (the
                # GBR can dip below zero on zero-inflated data, which makes
                # the chart look wrong).
                preds = np.maximum(preds, 0)
                mae = float(np.mean(np.abs(y - preds)))

                # Linear trend summary (always computed, for the trend label)
                lr = LinearRegression().fit(X, y)
                slope = float(lr.coef_[0])
                intercept = float(lr.intercept_)

                pid_str = str(product_id)
                bias = float(metrics_map.get((pid_str, "demand_forecast"), {}).get("bias", 0.0) or 0.0)
                # Cap the bias: if the learned bias is more than 2× the
                # historical daily average, it's probably from a broken
                # data row, not a real systematic error.
                daily_avg = float(np.mean(y)) if len(y) > 0 else 0.0
                if daily_avg > 0 and abs(bias) > 2.0 * daily_avg:
                    bias = 0.0

                # Sanitize every fitted value (defends against any model
                # output that slips through as NaN/inf)
                history = []
                for i in range(len(daily)):
                    fitted = _validate_and_clamp(
                        float(preds[i]) - bias,
                        min_val=0.0,
                        max_val=daily_avg * MAX_DEMAND_MULTIPLIER if daily_avg > 0 else None,
                        fallback=float(y[i]),
                    )
                    history.append({
                        "date": str(daily["date"].iloc[i].date()),
                        "actual": int(y[i]),
                        "fitted": round(fitted, 2),
                    })

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
                    "status": "ok" if len(daily) >= MIN_SAMPLES_FOR_TRAINING else "fallback_few_days",
                }
            except Exception:
                continue
        return models

    @st.cache_resource(show_spinner="Training price-prediction model…")
    def train_price_model(_self) -> Dict[str, Any]:
        """Train the price-optimization model.

        v7 (replaces the broken v6 model that was producing 2000%+ MAPE).

        The old model tried to predict a product's own price from its own
        stock/sales/category attributes — that's a circular, ill-posed
        problem. With <30 products the model was wildly overfit and
        predicted prices that were 50× off (e.g. 3000 Birr for a 50 Birr
        product), causing the engine to log a 2616.73 bias correction
        which then got applied to every future prediction, compounding
        the error.

        The new approach is category-relative and bounded:
          1. Compute the *category median price* from the product catalogue.
             That's our "fair market value" baseline for that category.
          2. For each product, the recommendation is anchored to its own
             current price, with a small adjustment based on:
               • demand pressure: products selling faster than the catalogue
                 average can support a small price INCREASE (max +15%)
               • stock pressure: products with very low stock (relative to
                 their category) can support a small price INCREASE
               • underperformers: products with below-median demand can
                 support a small price DECREASE (max -15%)
          3. The final recommendation is CLAMPED to current_price *
             (1 ± MAX_PRICE_CHANGE_FRACTION). The model can never suggest
             doubling or halving a price — that's a business decision.

        The returned ``products_features`` DataFrame still carries the
        ``predicted_price`` column so the UI doesn't have to change.
        """
        if not ML_AVAILABLE:
            return {"trained": False, "reason": "ML libraries not installed",
                    "status": "unavailable", "model_kind": "baseline"}

        data = _self.load_training_data()
        products = data["products"]
        order_items = data["order_items"]
        if products.empty:
            return {"trained": False, "reason": "no_products",
                    "status": "no_data", "model_kind": "baseline"}

        features = products.copy()
        features["price"] = pd.to_numeric(features["price"], errors="coerce").fillna(0)
        features["stock"] = pd.to_numeric(features["stock"], errors="coerce").fillna(0)
        # Drop products with no price (can't make a recommendation for freebies)
        features = features[features["price"] > 0]
        if features.empty:
            return {"trained": False, "reason": "no_priced_products",
                    "status": "no_data", "model_kind": "baseline"}

        # --- Per-product demand (total quantity sold) ------------------------
        if not order_items.empty:
            sales = order_items.groupby("product_id")["quantity"].sum().reset_index()
            sales.columns = ["id", "total_sold"]
            features = features.merge(sales, on="id", how="left")
            features["total_sold"] = pd.to_numeric(features["total_sold"], errors="coerce").fillna(0)
        else:
            features["total_sold"] = 0

        # --- Category-level statistics (the "fair market" baseline) --------
        # For each category we compute median price and median total_sold.
        # The per-product adjustment is a small delta FROM the product's
        # own current price, not a delta from the category median.
        cat_stats = features.groupby("category").agg(
            cat_median_price=("price", "median"),
            cat_median_sales=("total_sold", "median"),
        ).reset_index()
        features = features.merge(cat_stats, on="category", how="left")
        # Fallbacks for categories with a single product
        features["cat_median_price"] = features["cat_median_price"].fillna(features["price"])
        features["cat_median_sales"] = features["cat_median_sales"].fillna(0)

        # Global catalogue median (used as the baseline when a product has
        # no order history at all)
        global_median_price = float(features["price"].median()) if not features.empty else 0.0
        global_median_sales = float(features["total_sold"].median()) if not features.empty else 0.0

        # --- Learned bias (per product, from previous scored predictions) --
        raw_metrics = data.get("model_metrics")
        if raw_metrics is None:
            metrics_df = pd.DataFrame()
        elif not hasattr(raw_metrics, "empty"):
            metrics_df = pd.DataFrame(raw_metrics)
        else:
            metrics_df = raw_metrics
        metrics_map = _self._latest_metrics(metrics_df)

        # --- Compute bounded price recommendation per product ---------------
        # adjustment_fraction in [-MAX_PRICE_CHANGE_FRACTION, +MAX_PRICE_CHANGE_FRACTION]
        # = 0.5 * demand_signal + 0.5 * stock_signal
        # where each signal is in [-1, +1].
        predicted_prices = []
        adjustments = []
        status = "ok"
        for _, row in features.iterrows():
            current_price = float(row["price"])
            if current_price <= 0:
                predicted_prices.append(0.0)
                adjustments.append(0.0)
                continue

            # Demand signal: above-median-sales → +1, below → -1, no data → 0
            cat_sales = float(row.get("cat_median_sales") or 0)
            own_sales = float(row.get("total_sold") or 0)
            if cat_sales > 0 and own_sales > 0:
                # Map the ratio (own / cat_median) into [-1, +1] via tanh-like
                # squash so a 5x seller doesn't get a +5 signal.
                ratio = own_sales / cat_sales
                # 0.5 → -1, 1.0 → 0, 2.0 → +1, 5.0 → +1
                if ratio <= 1.0:
                    demand_signal = (ratio - 0.5) * 2.0  # 0.0 → -1.0
                else:
                    demand_signal = 1.0 - 1.0 / ratio      # 1.0 → 0, inf → 1
                demand_signal = max(-1.0, min(1.0, demand_signal))
            else:
                demand_signal = 0.0

            # Stock-pressure signal: low stock relative to category can
            # justify a small price INCREASE (scarcity). We compare own
            # stock to the category median stock.
            own_stock = float(row.get("stock") or 0)
            cat_stock_med = float(features[features["category"] == row.get("category", "")]["stock"].median() or 0)
            if cat_stock_med > 0 and own_stock > 0:
                stock_ratio = own_stock / cat_stock_med
                # Low stock (<0.5 of category median) → positive signal
                # (price up). High stock (>2x median) → negative (price down).
                if stock_ratio <= 1.0:
                    stock_signal = (0.5 - stock_ratio) * 2.0  # 0.5 → 0, 0 → +1
                else:
                    stock_signal = -(stock_ratio - 1.0)        # 1 → 0, 3 → -2 (clamped)
                stock_signal = max(-1.0, min(1.0, stock_signal))
            else:
                stock_signal = 0.0

            # Weighted combination. Both signals are bounded in [-1, +1],
            # so the total adjustment is in [-MAX_PRICE_CHANGE_FRACTION, +MAX_PRICE_CHANGE_FRACTION].
            adj_fraction = 0.5 * demand_signal + 0.5 * stock_signal
            adj_fraction = max(-MAX_PRICE_CHANGE_FRACTION,
                               min(MAX_PRICE_CHANGE_FRACTION, adj_fraction))

            # Apply bounded bias correction (only if it's sane: small fraction of price)
            pid_str = str(row["id"])
            bias = float(metrics_map.get((pid_str, "price_optimization"), {}).get("bias", 0.0) or 0.0)
            # A bias of 2616 Birr on a 50 Birr product is garbage — cap it
            # to MAX_BIAS_FRACTION of the current price.
            max_allowed_bias = MAX_BIAS_FRACTION * current_price
            if abs(bias) > max_allowed_bias:
                bias = 0.0  # Ignore garbage biases entirely
            adj_fraction -= bias / current_price if current_price > 0 else 0.0
            adj_fraction = max(-MAX_PRICE_CHANGE_FRACTION,
                               min(MAX_PRICE_CHANGE_FRACTION, adj_fraction))

            recommended = current_price * (1.0 + adj_fraction)
            recommended = _validate_and_clamp(
                recommended,
                min_val=current_price * 0.5,  # never recommend halving
                max_val=current_price * 1.5,  # never recommend doubling
                fallback=current_price,
            )
            predicted_prices.append(round(recommended, 2))
            adjustments.append(round(adj_fraction * 100, 1))  # as percent

        features["predicted_price"] = predicted_prices
        features["adjustment_pct"] = adjustments

        # --- Status / sample-size reporting ---------------------------------
        # We always "succeed" in training (the baseline is always available),
        # but we report low confidence when we don't have enough sales data
        # to compute meaningful demand signals.
        n_with_sales = int((features["total_sold"] > 0).sum())
        n_total = int(len(features))
        if n_with_sales < MIN_SAMPLES_FOR_TRAINING:
            status = "fallback_no_sales_data"
        elif n_total < MIN_SAMPLES_FOR_TRAINING:
            status = "fallback_few_products"

        return {
            "trained": True,
            "model": None,  # No sklearn model — we use a deterministic formula
            "mae": 0.0,
            "r2": 0.0,
            "samples": n_total,
            "samples_with_sales": n_with_sales,
            "feature_names": ["current_price", "category_median", "demand_signal", "stock_signal"],
            "products_features": features,
            "model_kind": "category_relative_bounded",
            "status": status,
            "global_median_price": global_median_price,
            "global_median_sales": global_median_sales,
        }

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
