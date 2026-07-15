"""
ML Engine — self-learning ML engine (OPTIONAL).

If pandas/numpy/scikit-learn aren't installed, all methods return empty/None
and the AI Insights tab shows a friendly message.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
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


class MLEngine:
    """Loads + caches training data and trained models from Supabase."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from database.connection import get_supabase_client
            self._client = get_supabase_client()
        return self._client

    @st.cache_data(ttl=300, show_spinner="Training ML models on your latest data…")
    def load_training_data(_self) -> Dict[str, Any]:
        """Fetch all relevant tables from Supabase. Cached 5 min."""
        if not ML_AVAILABLE:
            return {"orders": [], "order_items": [], "products": [], "profiles": [], "favorites": [], "cart_items": []}

        client = _self.client

        def fetch(table, select="*"):
            try:
                r = client.table(table).select(select).execute()
                return pd.DataFrame(r.data or [])
            except Exception:
                return pd.DataFrame()

        return {
            "orders":      fetch("orders"),
            "order_items": fetch("order_items"),
            "products":    fetch("products"),
            "profiles":    fetch("profiles"),
            "favorites":   fetch("favorites"),
            "cart_items":  fetch("cart_items"),
        }

    @st.cache_resource(show_spinner="Training demand forecast models…")
    def train_demand_models(_self) -> Dict[str, Dict[str, Any]]:
        if not ML_AVAILABLE:
            return {}
        from sklearn.linear_model import LinearRegression

        data = _self.load_training_data()
        if data["order_items"].empty:
            return {}

        items = data["order_items"].copy()
        items["created_at"] = pd.to_datetime(items["created_at"], errors="coerce")
        items = items.dropna(subset=["created_at"])

        models: Dict[str, Dict[str, Any]] = {}
        for product_id, group in items.groupby("product_id"):
            if len(group) < 2:
                continue
            daily = group.groupby(group["created_at"].dt.date)["quantity"].sum().reset_index()
            daily.columns = ["date", "qty"]
            daily["date"] = pd.to_datetime(daily["date"])
            daily["day_num"] = (daily["date"] - daily["date"].min()).dt.days
            X = daily[["day_num"]].values
            y = daily["qty"].values
            try:
                m = LinearRegression()
                m.fit(X, y)
                preds = m.predict(X)
                mae = float(np.mean(np.abs(y - preds)))
                models[product_id] = {
                    "model": m, "slope": float(m.coef_[0]), "intercept": float(m.intercept_),
                    "mae": mae, "samples": len(group),
                    "first_date": str(daily["date"].min().date()), "last_date": str(daily["date"].max().date()),
                }
            except Exception:
                continue
        return models

    @st.cache_resource(show_spinner="Training price-prediction model…")
    def train_price_model(_self) -> Dict[str, Any]:
        if not ML_AVAILABLE:
            return {"trained": False, "reason": "ML libraries not installed"}
        from sklearn.linear_model import LinearRegression

        data = _self.load_training_data()
        products = data["products"]
        order_items = data["order_items"]
        if products.empty:
            return {"trained": False, "reason": "no_products"}

        features = products.copy()
        features["price"] = pd.to_numeric(features["price"], errors="coerce").fillna(0)
        features["stock"] = pd.to_numeric(features["stock"], errors="coerce").fillna(0)
        features["reorder_point"] = pd.to_numeric(features["reorder_point"], errors="coerce").fillna(0)
        features["category_code"] = features["category"].astype("category").cat.codes

        if not order_items.empty:
            sales = order_items.groupby("product_id")["quantity"].sum().reset_index()
            sales.columns = ["id", "total_sold"]
            features = features.merge(sales, on="id", how="left")
            features["total_sold"] = features["total_sold"].fillna(0)
        else:
            features["total_sold"] = 0

        if len(features) < 3:
            return {"trained": False, "reason": "not_enough_products"}

        X = features[["stock", "reorder_point", "category_code", "total_sold"]].values
        y = features["price"].values
        try:
            m = LinearRegression()
            m.fit(X, y)
            preds = m.predict(X)
            return {"trained": True, "model": m, "mae": float(np.mean(np.abs(y - preds))),
                    "r2": float(m.score(X, y)), "samples": len(features),
                    "feature_names": ["stock", "reorder_point", "category_code", "total_sold"],
                    "products_features": features}
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
            item_user = order_items.merge(orders[["id", "buyer_id"]], left_on="order_id", right_on="id", how="left", suffixes=("", "_order"))
            for _, r in item_user.iterrows():
                if r.get("buyer_id"):
                    interactions_rows.append({"user_id": str(r["buyer_id"]), "product_id": str(r["product_id"]), "score": 3})
        if not favorites.empty:
            for _, r in favorites.iterrows():
                if r.get("user_id") and r.get("product_id"):
                    interactions_rows.append({"user_id": str(r["user_id"]), "product_id": str(r["product_id"]), "score": 2})

        if len(interactions_rows) < 3:
            return {"trained": False, "reason": "not_enough_interactions", "interaction_count": len(interactions_rows)}

        df = pd.DataFrame(interactions_rows).dropna(subset=["user_id", "product_id"])
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(1)
        matrix = df.pivot_table(index="user_id", columns="product_id", values="score", aggfunc="max", fill_value=0)
        product_vectors = matrix.T
        if product_vectors.shape[0] < 2:
            return {"trained": False, "reason": "not_enough_products_with_interactions"}
        sim = cosine_similarity(product_vectors)
        sim_df = pd.DataFrame(sim, index=product_vectors.index, columns=product_vectors.index)
        return {"trained": True, "interaction_count": len(df), "unique_users": int(df["user_id"].nunique()),
                "unique_products": int(df["product_id"].nunique()), "similarity_matrix": sim_df, "products": products}

    def save_predictions(self, predictions: List[Dict[str, Any]]) -> int:
        if not predictions:
            return 0
        try:
            r = self.client.table("ai_predictions").insert(predictions).execute()
            return len(r.data or [])
        except Exception:
            return 0


@st.cache_data(ttl=300)
def get_training_summary() -> Dict[str, Any]:
    if not ML_AVAILABLE:
        return {"ml_available": False, "message": "ML libraries (pandas, numpy, scikit-learn) not installed. AI Insights disabled."}
    engine = MLEngine()
    data = engine.load_training_data()
    demand_models = engine.train_demand_models()
    price_model = engine.train_price_model()
    recommender = engine.train_recommender()
    return {
        "ml_available": True,
        "orders_count": len(data["orders"]), "order_items_count": len(data["order_items"]),
        "products_count": len(data["products"]), "users_count": len(data["profiles"]),
        "favorites_count": len(data["favorites"]),
        "demand_models_trained": len(demand_models),
        "price_model_trained": price_model.get("trained", False),
        "price_model_r2": price_model.get("r2", 0), "price_model_mae": price_model.get("mae", 0),
        "recommender_trained": recommender.get("trained", False),
        "recommender_interactions": recommender.get("interaction_count", 0),
        "cache_ttl_seconds": 300, "last_trained": datetime.now(timezone.utc).isoformat(),
    }
