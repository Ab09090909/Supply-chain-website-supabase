"""
Reviews & ratings UI components.
"""
from __future__ import annotations

import streamlit as st
from typing import Dict, Any, List
from datetime import datetime
from utils.reviews import (
    list_reviews_for_product,
    has_user_purchased,
    create_review,
    delete_review,
    mark_helpful,
)


def _render_stars(rating: float, max_stars: int = 5) -> str:
    """Return a unicode star-rating string like '★★★★☆'."""
    full = int(round(rating))
    full = max(0, min(max_stars, full))
    return "★" * full + "☆" * (max_stars - full)


def render_product_reviews(product_id: str, product: Dict[str, Any], current_user: Dict[str, Any]):
    """Render the full reviews block: aggregate, form, list."""
    reviews = list_reviews_for_product(product_id, limit=20)
    avg = float(product.get("avg_rating") or 0)
    count = int(product.get("review_count") or 0)

    st.markdown("##### ⭐ Reviews & Ratings")

    # Aggregate
    c1, c2 = st.columns([1, 3])
    with c1:
        st.metric("Average Rating", f"{avg:.1f} / 5", delta=_render_stars(avg))
    with c2:
        st.metric("Total Reviews", count)
        # Distribution
        if reviews:
            dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for r in reviews:
                dist[int(r.get("rating") or 0)] = dist.get(int(r.get("rating") or 0), 0) + 1
            for star in (5, 4, 3, 2, 1):
                st.caption(f"{'★' * star}{'☆' * (5 - star)}  {dist.get(star, 0)}")

    st.markdown("---")

    # Leave-a-review form (verified buyers only)
    if current_user:
        already_reviewed = any(str(r.get("reviewer_id")) == str(current_user.get("id")) for r in reviews)
        if already_reviewed:
            st.info("✅ You've already reviewed this product. Thanks!")
        else:
            purchased = has_user_purchased(current_user.get("id"), product_id)
            if not purchased:
                st.caption("🔒 Only verified buyers can leave a review. Purchase this product to review it.")
            else:
                with st.form(f"review_form_{product_id}"):
                    st.markdown("**Leave a review**")
                    rating = st.slider("Rating", 1, 5, 5, key=f"rev_rating_{product_id}")
                    title = st.text_input("Title (optional)", key=f"rev_title_{product_id}")
                    body = st.text_area("Your review", key=f"rev_body_{product_id}", height=100)
                    if st.form_submit_button("Post review", type="primary"):
                        if not body.strip() and not title.strip():
                            st.error("Please add a title or some text.")
                        else:
                            ok, msg = create_review(
                                product_id=product_id,
                                reviewer_id=current_user.get("id"),
                                rating=rating,
                                title=title.strip(),
                                body=body.strip(),
                            )
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

    # Reviews list
    if not reviews:
        st.caption("No reviews yet. Be the first to review this product!")
        return

    st.markdown(f"##### All reviews ({count})")
    for r in reviews:
        profile = r.get("profiles") or {}
        author = profile.get("full_name", "Anonymous")
        created = (r.get("created_at") or "")[:10]
        verified = " ✅ Verified buyer" if r.get("is_verified") else ""

        with st.container(border=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{_render_stars(float(r.get('rating') or 0))}** {r.get('title') or ''}".strip())
                st.caption(f"by {author} on {created}{verified}")
            with col2:
                if current_user and str(r.get("reviewer_id")) == str(current_user.get("id")):
                    if st.button("🗑️", key=f"del_rev_{r.get('id')}"):
                        ok, msg = delete_review(r.get("id"), current_user.get("id"))
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                if st.button(f"👍 {r.get('helpful_count', 0)}", key=f"helpful_{r.get('id')}"):
                    mark_helpful(r.get("id"))
                    st.rerun()
            if r.get("body"):
                st.markdown(r.get("body"))


def render_product_card_stars(product: Dict[str, Any]):
    """Render a small star rating for a product card."""
    avg = float(product.get("avg_rating") or 0)
    count = int(product.get("review_count") or 0)
    if count == 0:
        return
    stars = _render_stars(avg)
    st.caption(f"{stars} {avg:.1f} ({count})")
