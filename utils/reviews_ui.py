"""
Reviews & ratings UI components.
"""
from __future__ import annotations

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.reviews import (
    list_reviews_for_product,
    has_user_purchased,
    create_review,
    delete_review,
    mark_helpful,
    get_review_for_order,
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
    """Render a small star rating for a product card.

    Always shows something — either the real rating, or "No ratings yet"
    in muted text. Producers and buyers asked for the rating to be visible
    on every product card, not only after a review was left.
    """
    avg = float(product.get("avg_rating") or 0)
    count = int(product.get("review_count") or 0)
    if count == 0:
        st.markdown(
            "<div style='font-size:0.72rem; color:#94a3b8; margin:2px 0 4px 0;'>"
            "☆☆☆☆☆ &nbsp;·&nbsp; <i>No ratings yet</i>"
            "</div>",
            unsafe_allow_html=True,
        )
        return
    stars = _render_stars(avg)
    label = (
        f"<span style='color:#f59e0b;'>{stars}</span> "
        f"<b style='color:#0f172a;'>{avg:.1f}</b>"
        f" <span style='color:#94a3b8; font-size:0.7rem;'>({count} rating{'s' if count != 1 else ''})</span>"
    )
    st.markdown(label, unsafe_allow_html=True)


def render_order_rating_widget(
    order: Dict[str, Any],
    item: Dict[str, Any],
    product: Optional[Dict[str, Any]],
    current_user: Dict[str, Any],
) -> None:
    """Inline rating widget for a single order item.

    Shown on customer / merchant order pages once the order is delivered.
    Buyers can rate the product (1-5 stars) and leave an optional comment
    straight from the order page — no need to navigate to the product
    detail page.

    Renders a small "Rate this product" expander. If the user has already
    rated this order, shows their existing review and offers a delete
    action.
    """
    order_id = order.get("id")
    product_id = item.get("product_id")
    if not order_id or not product_id or not current_user:
        return

    # Pre-fetch any existing review to short-circuit duplicate inserts
    existing = get_review_for_order(order_id, current_user.get("id"))

    product_name = item.get("name") or (product or {}).get("name") or "this product"

    if existing:
        rating_val = int(existing.get("rating") or 0)
        stars = _render_stars(float(rating_val))
        title = existing.get("title") or ""
        body = existing.get("body") or ""
        created = (existing.get("created_at") or "")[:10]

        st.markdown(
            f"""
            <div style='background:#f0fdf4; border:1px solid #bbf7d0;
                        border-radius:10px; padding:10px 14px; margin:6px 0;'>
              <div style='font-size:0.85rem; color:#166534; font-weight:600;'>
                ✅ You rated {product_name}
              </div>
              <div style='font-size:1.05rem; color:#f59e0b; margin:4px 0;'>{stars}
                <span style='color:#0f172a; font-size:0.85rem; font-weight:600;'>{rating_val}/5</span>
              </div>
              {f"<div style='font-size:0.85rem; color:#0f172a; font-weight:600;'>{title}</div>" if title else ""}
              {f"<div style='font-size:0.8rem; color:#475569; margin-top:2px;'>{body}</div>" if body else ""}
              <div style='font-size:0.7rem; color:#94a3b8; margin-top:4px;'>Posted on {created}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Let the user delete their review if they want to re-rate
        with st.expander("✏️ Edit / delete your review", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                with st.form(f"update_review_{order_id}_{product_id}"):
                    new_rating = st.slider(
                        "Update rating",
                        1, 5, rating_val,
                        key=f"upd_rating_{order_id}_{product_id}",
                    )
                    new_title = st.text_input(
                        "Title (optional)",
                        value=title,
                        key=f"upd_title_{order_id}_{product_id}",
                    )
                    new_body = st.text_area(
                        "Your review",
                        value=body,
                        key=f"upd_body_{order_id}_{product_id}",
                        height=80,
                    )
                    if st.form_submit_button("💾 Update review", type="primary"):
                        # Use create_review semantics: delete + insert to keep
                        # the implementation simple and idempotent.
                        try:
                            from database.connection import get_supabase_client
                            from utils.reviews import delete_review
                            ok, msg = delete_review(existing.get("id"), current_user.get("id"))
                            if not ok:
                                st.error(f"Couldn't clear old review: {msg}")
                            else:
                                ok2, msg2 = create_review(
                                    product_id=product_id,
                                    reviewer_id=current_user.get("id"),
                                    rating=new_rating,
                                    title=new_title.strip(),
                                    body=new_body.strip(),
                                    order_id=order_id,
                                )
                                if ok2:
                                    st.success("✅ Review updated!")
                                    st.rerun()
                                else:
                                    st.error(msg2)
                        except Exception as e:
                            st.error(f"Failed: {e}")
            with col_b:
                if st.button(
                    "🗑️ Delete review",
                    key=f"del_review_{order_id}_{product_id}",
                    use_container_width=True,
                ):
                    try:
                        from utils.reviews import delete_review
                        ok, msg = delete_review(existing.get("id"), current_user.get("id"))
                        if ok:
                            st.success("Review removed.")
                            st.rerun()
                        else:
                            st.error(msg)
                    except Exception as e:
                        st.error(f"Failed: {e}")
        return

    # No existing review yet — show a clean "Rate this product" expander
    with st.expander(f"⭐ Rate this product — {product_name}", expanded=False):
        st.caption(
            "Your rating helps other buyers and the producer. "
            "Only verified buyers can leave reviews."
        )
        with st.form(f"order_rate_{order_id}_{product_id}"):
            rating = st.slider(
                "How would you rate this product?",
                1, 5, 5,
                key=f"order_rating_{order_id}_{product_id}",
                help="1 = poor, 5 = excellent",
            )
            title = st.text_input(
                "Title (optional)",
                key=f"order_title_{order_id}_{product_id}",
                placeholder="What stood out?",
            )
            body = st.text_area(
                "Your review (optional)",
                key=f"order_body_{order_id}_{product_id}",
                placeholder="Tell other buyers about your experience with this product.",
                height=100,
            )
            submitted = st.form_submit_button("🌟 Submit rating", type="primary")
            if submitted:
                ok, msg = create_review(
                    product_id=product_id,
                    reviewer_id=current_user.get("id"),
                    rating=rating,
                    title=title.strip(),
                    body=body.strip(),
                    order_id=order_id,
                )
                if ok:
                    st.success("✅ Thanks for rating this product!")
                    st.rerun()
                else:
                    st.error(msg)
