"""
Recommendations module — suggests products to users.

Uses collaborative filtering (cosine similarity on user-product interaction
matrix) to find products similar to ones the user has ordered/favorited.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import streamlit as st
import pandas as pd
import numpy as np

from .engine import MLEngine


def get_recommendations(user_id: str, top_n: int = 6) -> List[Dict[str, Any]]:
    """Get top-N product recommendations for a user.

    Strategy:
      1. If collaborative filtering model is trained → use it.
      2. Else fallback to popularity-based (most-ordered products).
      3. Else fallback to random active products.
    """
    engine = MLEngine()
    rec_info = engine.train_recommender()
    data = engine.load_training_data()
    products = data["products"]

    if products.empty:
        return []

    # Convert user_id to string for matching
    user_id_str = str(user_id)

    # ---- Strategy 1: Collaborative filtering ----
    if rec_info.get("trained"):
        sim_df = rec_info["similarity_matrix"]

        # Rebuild interactions DataFrame from the training data
        order_items = data["order_items"]
        orders = data["orders"]
        favorites = data["favorites"]

        interactions_rows = []
        if not order_items.empty and not orders.empty:
            item_user = order_items.merge(orders[["id", "buyer_id"]], left_on="order_id", right_on="id", how="left", suffixes=("", "_order"))
            for _, r in item_user.iterrows():
                if r.get("buyer_id"):
                    interactions_rows.append({"user_id": str(r["buyer_id"]), "product_id": str(r["product_id"]), "score": 3})
        if not favorites.empty:
            for _, r in favorites.iterrows():
                if r.get("user_id") and r.get("product_id"):
                    interactions_rows.append({"user_id": str(r["user_id"]), "product_id": str(r["product_id"]), "score": 2})

        user_products = []
        if interactions_rows:
            interactions = pd.DataFrame(interactions_rows).dropna(subset=["user_id", "product_id"])

            # Get products this user has interacted with
            user_products = interactions[interactions["user_id"] == user_id_str]["product_id"].unique()

        if len(user_products) > 0:
            # Aggregate similarity scores across user's products
            scores: Dict[str, float] = {}
            for pid in user_products:
                if pid in sim_df.index:
                    similar = sim_df[pid].sort_values(ascending=False)
                    for other_pid, score in similar.items():
                        if other_pid not in user_products and other_pid != pid:
                            scores[other_pid] = scores.get(other_pid, 0) + float(score)

            # Sort by score, take top N
            ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
            recommended_ids = [pid for pid, _ in ranked]

            if recommended_ids:
                recommended = products[products["id"].astype(str).isin(recommended_ids)].copy()
                recommended["rec_score"] = recommended["id"].astype(str).map(
                    dict(ranked)
                )
                recommended = recommended.sort_values("rec_score", ascending=False)
                return _format_recommendations(recommended, "collaborative_filtering")

    # ---- Strategy 2: Popularity-based (most ordered) ----
    order_items = data["order_items"]
    if not order_items.empty:
        popular = order_items.groupby("product_id")["quantity"].sum().reset_index()
        popular.columns = ["id", "total_sold"]
        popular["id"] = popular["id"].astype(str)
        products_with_sales = products.copy()
        products_with_sales["id"] = products_with_sales["id"].astype(str)
        merged = products_with_sales.merge(popular, on="id", how="inner")
        merged = merged.sort_values("total_sold", ascending=False).head(top_n)
        if not merged.empty:
            return _format_recommendations(merged, "popularity_based")

    # ---- Strategy 3: Fallback to random active products ----
    active = products[products["status"] == "active"].head(top_n)
    return _format_recommendations(active, "fallback_random")


def _format_recommendations(df: pd.DataFrame, method: str) -> List[Dict[str, Any]]:
    """Convert a DataFrame of products into a list of recommendation dicts."""
    results: List[Dict[str, Any]] = []
    for _, p in df.iterrows():
        results.append({
            "product_id": str(p["id"]),
            "sku": p.get("sku", ""),
            "name": p.get("name", ""),
            "category": p.get("category", ""),
            "price": float(p.get("price", 0)),
            "stock": int(p.get("stock", 0)),
            "image_url": p.get("image_url"),
            "method": method,
            "score": float(p.get("rec_score", p.get("total_sold", 0))) if pd.notna(p.get("rec_score", p.get("total_sold", 0))) else 0,
        })
    return results
