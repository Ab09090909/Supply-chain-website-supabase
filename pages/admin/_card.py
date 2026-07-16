"""
Shared admin dashboard card components.

This module provides the green-gradient header card + metric-grid
layout that is used across the admin dashboard pages (Platform
Overview, Users by Role, Orders & Products, AI / ML Engine Status,
User Management summary, Product Management summary).

Centralising the CSS and helpers here means the design is consistent
across every admin page, and a CSS update only needs to happen in
one place.

Usage
-----
    from pages.admin._card import inject_card_css, admin_card, admin_metric_box

    def render_my_page():
        inject_card_css()  # call once at the top of the page
        admin_card(
            icon="👥",
            title="User Management",
            subtitle="Verify users, view documents, activate/deactivate accounts",
            metrics_html=(
                admin_metric_box("12", "Total Users", "👥")
                + admin_metric_box("8",  "Pending",    "⏳", alert=True)
                + admin_metric_box("4",  "Verified",   "✅")
            ),
        )
"""
from __future__ import annotations

import streamlit as st


# ─── CSS (single source of truth for the admin card look) ───────────────────
# This CSS is mobile-safe — every property has explicit fallbacks,
# no flexbox with `flex:1` that could collapse on narrow viewports,
# and no attributes that Streamlit's HTML sanitizer strips.
CARD_CSS = """
<style>
.dash-card {
    background: #ffffff;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}
.dash-card-header {
    background: linear-gradient(135deg, #1a5c2e 0%, #2d8a4e 100%);
    padding: 20px 24px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
}
.dash-card-header-icon {
    font-size: 2rem;
    line-height: 1;
    flex-shrink: 0;
}
.dash-card-header-text h3 {
    margin: 0;
    color: #ffffff;
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.3px;
}
.dash-card-header-text p {
    margin: 2px 0 0;
    color: #a8d5b5;
    font-size: 0.82rem;
}
.dash-card-body {
    padding: 18px 20px;
}
.metric-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}
.metric-box {
    flex: 1 1 130px;
    background: #f7f9f7;
    border: 1px solid #e4ece6;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    min-width: 110px;
    box-sizing: border-box;
}
.metric-box .metric-value {
    font-size: 1.8rem;
    font-weight: 800;
    color: #1a5c2e;
    line-height: 1.1;
    word-break: break-word;
}
.metric-box .metric-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #6b8f72;
    margin-top: 4px;
    word-break: break-word;
}
.metric-box .metric-label-icon {
    margin-right: 4px;
}
.metric-box.alert .metric-value { color: #b85c00; }
.metric-box.alert { background: #fff8f0; border-color: #f5d5b0; }
</style>
"""


def inject_card_css() -> None:
    """Inject the admin card CSS into the page. Call once at the top
    of any admin page that uses admin_card() / admin_metric_box().

    Idempotent: calling it more than once is harmless (the browser
    applies the last <style> block, which has the same selectors).
    """
    st.markdown(CARD_CSS, unsafe_allow_html=True)


def admin_metric_box(value: str, label: str, icon: str = "", alert: bool = False) -> str:
    """Render one metric box as an HTML string.

    Args:
        value:  the large number/text shown in the box (e.g. "12", "ETB 5,200")
        label:  the small uppercase caption under the value (e.g. "Total Users")
        icon:   optional emoji prepended to the label (e.g. "👥")
        alert:  if True, the box is rendered with the amber alert style

    Returns:
        An HTML string. Concatenate multiple boxes with ``+`` to form
        the ``metrics_html`` argument of ``admin_card``.
    """
    cls = "metric-box alert" if alert else "metric-box"
    icon_html = f'<span class="metric-label-icon">{icon}</span>' if icon else ""
    return (
        f'<div class="{cls}">'
        f'  <div class="metric-value">{value}</div>'
        f'  <div class="metric-label">{icon_html}{label}</div>'
        f'</div>'
    )


def admin_card(icon: str, title: str, subtitle: str, metrics_html: str) -> None:
    """Render one admin card (green header + metric grid).

    Args:
        icon:         the large emoji in the header (e.g. "🧠")
        title:        the card title (e.g. "Model Status")
        subtitle:     the small caption under the title
        metrics_html: the pre-built HTML string of metric boxes
    """
    # Use _html() so the multi-line HTML is rendered as raw HTML
    # instead of being mis-interpreted as a Markdown code block (which
    # would show the raw <div> source on the page).
    from utils.ui import _html
    _html(
        f"""
        <div class="dash-card">
          <div class="dash-card-header">
            <div class="dash-card-header-icon">{icon}</div>
            <div class="dash-card-header-text">
              <h3>{title}</h3>
              <p>{subtitle}</p>
            </div>
          </div>
          <div class="dash-card-body">
            <div class="metric-grid">
              {metrics_html}
            </div>
          </div>
        </div>
        """
    )
