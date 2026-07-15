"""
Reusable search & filter UI components for marketplace pages.
"""
from __future__ import annotations

import streamlit as st
from typing import List, Dict, Any, Optional


def render_search_filter_bar(
    *,
    categories: Optional[List[str]] = None,
    show_rating_filter: bool = True,
    show_in_stock: bool = True,
    key_prefix: str = "search",
) -> Dict[str, Any]:
    """Render a search + filter bar and return the selected filter values.

    Returns a dict with keys: query, category, min_price, max_price,
    min_rating, in_stock_only, sort_by.
    """
    cols = st.columns([3, 2, 1, 1, 1])
    with cols[0]:
        query = st.text_input(
            "🔍 Search by name, SKU, brand…",
            placeholder="e.g. wheat, organic, AGR-001",
            key=f"{key_prefix}_q",
        )
    with cols[1]:
        cat_options = ["All"] + (categories or [])
        category = st.selectbox(
            "Category",
            options=cat_options,
            key=f"{key_prefix}_cat",
        )
        if category == "All":
            category = ""
    with cols[2]:
        min_price = st.number_input(
            "Min (Br)",
            min_value=0.0,
            value=0.0,
            step=10.0,
            key=f"{key_prefix}_min",
        )
    with cols[3]:
        max_price = st.number_input(
            "Max (Br)",
            min_value=0.0,
            value=0.0,
            step=100.0,
            key=f"{key_prefix}_max",
        )
    with cols[4]:
        sort_by = st.selectbox(
            "Sort by",
            options=[
                "newest",
                "price_asc",
                "price_desc",
                "rating",
                "popular",
                "name",
            ],
            format_func=lambda x: {
                "newest": "Newest",
                "price_asc": "Price ↑",
                "price_desc": "Price ↓",
                "rating": "Top rated",
                "popular": "Most sold",
                "name": "Name (A–Z)",
            }.get(x, x),
            key=f"{key_prefix}_sort",
        )

    row2 = st.columns([2, 2, 2, 4])
    with row2[0]:
        if show_in_stock:
            in_stock_only = st.checkbox("In stock only", value=False, key=f"{key_prefix}_stock")
        else:
            in_stock_only = False
    with row2[1]:
        if show_rating_filter:
            min_rating = st.slider(
                "Min rating",
                min_value=0.0,
                max_value=5.0,
                value=0.0,
                step=0.5,
                key=f"{key_prefix}_rating",
            )
        else:
            min_rating = None
    with row2[2]:
        # Reset button
        if st.button("🔄 Clear filters", use_container_width=True, key=f"{key_prefix}_reset"):
            for k in [
                f"{key_prefix}_q", f"{key_prefix}_cat", f"{key_prefix}_min",
                f"{key_prefix}_max", f"{key_prefix}_sort",
                f"{key_prefix}_stock", f"{key_prefix}_rating",
            ]:
                st.session_state.pop(k, None)
            st.rerun()
    return {
        "query": query,
        "category": category,
        "min_price": min_price if min_price > 0 else None,
        "max_price": max_price if max_price > 0 else None,
        "min_rating": min_rating,
        "in_stock_only": in_stock_only,
        "sort_by": sort_by,
    }
