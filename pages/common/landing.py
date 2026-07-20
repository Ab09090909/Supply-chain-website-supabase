"""
Public landing page — shown when a visitor is not logged in.

Modern SaaS marketing site design with:
  • Hero section with gradient title + dual CTAs
  • Feature grid showcasing platform capabilities
  • "How it works" 3-step section
  • Social proof / role-specific benefits
  • Trust badges (security, support, etc.)
  • Footer with links

Inspired by modern sites like Linear, Stripe, Vercel — clean, focused,
and conversion-optimized.

The page is rendered ABOVE the auth forms (login/signup), so the
visitor sees the marketing pitch before being asked to sign in.
"""
from __future__ import annotations

import streamlit as st

from utils.ui import (
    hero_section, feature_grid, card, tag, FONT_STACK,
    _html, COLORS, GRADIENTS,
)
from utils.app_url import get_app_url


# ---------------------------------------------------------------------------
# Marketing copy — single source of truth so it's easy to update
# ---------------------------------------------------------------------------
HERO_EYEBROW = "AI-Powered Supply Chain Platform"
HERO_TITLE = "Move products. Match merchants. Forecast demand."
HERO_SUBTITLE = (
    "EthioChain is the smart marketplace connecting producers, merchants, "
    "and customers — with AI demand forecasts, real-time matching, secure "
    "ordering, and end-to-end tracking. Built for modern African supply chains."
)
HERO_PRIMARY_CTA = ("Get started — it's free", "?page=signup")
HERO_SECONDARY_CTA = ("Sign in to your account", "?page=login")


FEATURES = [
    {
        "icon": "🤖",
        "title": "AI Demand Forecast",
        "description": "Per-product 30-day demand predictions with confidence scores. Know what to stock, when.",
        "color": "indigo",
    },
    {
        "icon": "💰",
        "title": "Smart Pricing",
        "description": "Bounded ±15% price recommendations based on category, demand, and stock pressure. Never absurd.",
        "color": "emerald",
    },
    {
        "icon": "🤝",
        "title": "Merchant Matchmaking",
        "description": "Find the right merchant for your products using weighted scoring across 7 dimensions: category, quality, brand, price, location, payment, history.",
        "color": "blue",
    },
    {
        "icon": "📦",
        "title": "Order Tracking",
        "description": "End-to-end order lifecycle: pending → confirmed → processing → shipped → delivered. Real-time status updates.",
        "color": "teal",
    },
    {
        "icon": "⭐",
        "title": "Reviews & Ratings",
        "description": "Trust system with 1-5 star reviews, written feedback, and average rating per producer.",
        "color": "amber",
    },
    {
        "icon": "🔒",
        "title": "Verified Producers",
        "description": "ID verification before you can sell. KYC built-in. Trade with confidence.",
        "color": "blue",
    },
    {
        "icon": "📈",
        "title": "Live Analytics",
        "description": "Interactive Plotly dashboards for page views, QR scans, downloads. Export as CSV/JSON.",
        "color": "purple",
    },
    {
        "icon": "💼",
        "title": "Digital Business Card",
        "description": "Beautiful shareable business card with QR code. Public link — no login required to view.",
        "color": "pink",
    },
    {
        "icon": "🎯",
        "title": "Personalized Recommendations",
        "description": "Collaborative filtering engine suggests products based on what similar users order.",
        "color": "rose",
    },
]


HOW_IT_WORKS = [
    {
        "step": "1",
        "title": "Sign up in 60 seconds",
        "description": "Pick your role (producer, merchant, or customer), verify your email, and you're in.",
        "icon": "🚀",
    },
    {
        "step": "2",
        "title": "List or browse products",
        "description": "Producers add inventory with photos. Merchants discover and order. AI helps you find the right matches.",
        "icon": "📦",
    },
    {
        "step": "3",
        "title": "Track, rate, grow",
        "description": "Orders flow through confirmed → shipped → delivered. AI forecasts help you plan. Reviews build trust.",
        "icon": "📈",
    },
]


ROLE_BENEFITS = [
    {
        "role": "Producer",
        "icon": "🌱",
        "color": "emerald",
        "title": "Sell smarter, not harder",
        "benefits": [
            "AI demand forecasts for your products",
            "Smart pricing recommendations (bounded ±15%)",
            "Auto-match with merchants who want your products",
            "Real-time order tracking + customer reviews",
            "Live analytics dashboard for your store",
        ],
    },
    {
        "role": "Merchant",
        "icon": "🛒",
        "color": "blue",
        "title": "Source products that sell",
        "benefits": [
            "Discover producers in your category",
            "Order in bulk with transparent pricing",
            "Track orders from confirmation to delivery",
            "Save favorites + get AI recommendations",
            "Direct messaging with producers",
        ],
    },
    {
        "role": "Customer",
        "icon": "🛍️",
        "color": "purple",
        "title": "Buy direct, save money",
        "benefits": [
            "Browse products from verified producers",
            "Read reviews from real buyers",
            "Track your orders in real-time",
            "Save your favorites for later",
            "Direct line to sellers",
        ],
    },
]


TRUST_BADGES = [
    ("🔒", "End-to-end encrypted", "Your data is protected"),
    ("🌍", "Built for Africa", "Local payment terms, local logistics"),
    ("⚡", "AI-first", "Smart forecasts from day one"),
    ("🆓", "Free to start", "No credit card required"),
]


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------
def render_landing_page() -> None:
    """Render the public landing page (above the auth forms)."""
    # Inject Inter font (no Streamlit theme change needed)
    _html("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        .landing-root, .landing-root * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }
    </style>
    """)

    # Hide the auth form's max-width for the landing page only
    _html("""
    <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="stSidebarCollapsedControl"] { display: none; }
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            max-width: 1100px !important;
        }
    </style>
    """)

    # ---- HERO ----
    hero_section(
        eyebrow=HERO_EYEBROW,
        title=HERO_TITLE,
        subtitle=HERO_SUBTITLE,
        primary_cta=HERO_PRIMARY_CTA,
        secondary_cta=HERO_SECONDARY_CTA,
        badge_icon="✨",
    )

    # ---- TRUST BADGES (compact row) ----
    _html(f"""
    <div style='display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;
        margin:0 0 2.5rem 0;'>
        {''.join([
            f"""<div style='background:white;border:1px solid {COLORS['slate_200']};
                border-radius:12px;padding:0.7rem 0.85rem;display:flex;align-items:center;gap:8px;
                box-shadow:0 1px 3px rgba(0,0,0,0.04);'>
                <div style='font-size:1.15rem;'>{icon}</div>
                <div>
                    <div style='font-size:0.78rem;font-weight:700;color:{COLORS['slate_900']};line-height:1.2;'>{title}</div>
                    <div style='font-size:0.68rem;color:{COLORS['slate_500']};line-height:1.2;'>{desc}</div>
                </div>
            </div>"""
            for icon, title, desc in TRUST_BADGES
        ])}
    </div>
    """)

    # ---- FEATURES GRID ----
    _html(f"""
    <div style='text-align:center;margin:2.5rem 0 1rem 0;'>
        <div style='display:inline-block;background:linear-gradient(135deg,#ecfdf5 0%,#d1fae5 100%);
            color:#047857;padding:0.3rem 0.75rem;border-radius:9999px;font-size:0.7rem;
            font-weight:700;letter-spacing:0.06em;text-transform:uppercase;
            border:1px solid #a7f3d0;'>Features</div>
        <h2 style='font-size:2rem;font-weight:800;color:{COLORS['slate_900']};margin:0.75rem 0 0.5rem 0;
            letter-spacing:-0.025em;line-height:1.2;'>Everything you need, built in.</h2>
        <p style='font-size:1rem;color:{COLORS['slate_600']};max-width:560px;margin:0 auto;line-height:1.5;'>
            No third-party integrations required. No monthly fees. Just sign up and start trading.
        </p>
    </div>
    """)
    feature_grid(FEATURES, columns=3)

    # ---- HOW IT WORKS ----
    _html(f"""
    <div style='text-align:center;margin:3rem 0 1.25rem 0;'>
        <div style='display:inline-block;background:linear-gradient(135deg,#dbeafe 0%,#bfdbfe 100%);
            color:#1e40af;padding:0.3rem 0.75rem;border-radius:9999px;font-size:0.7rem;
            font-weight:700;letter-spacing:0.06em;text-transform:uppercase;
            border:1px solid #93c5fd;'>How it works</div>
        <h2 style='font-size:1.85rem;font-weight:800;color:{COLORS['slate_900']};margin:0.75rem 0 0.5rem 0;
            letter-spacing:-0.025em;'>Three steps. That's it.</h2>
    </div>
    """)
    _html(f"""
    <div style='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;margin:1.5rem 0 2.5rem 0;'>
        {''.join([
            f"""<div style='background:white;border:1px solid {COLORS['slate_200']};
                border-radius:18px;padding:1.75rem 1.5rem;position:relative;
                box-shadow:0 2px 8px rgba(0,0,0,0.04);'>
                <div style='position:absolute;top:-18px;left:24px;
                    background:linear-gradient(135deg,#10b981 0%,#059669 100%);
                    color:white;width:36px;height:36px;border-radius:50%;
                    display:flex;align-items:center;justify-content:center;
                    font-weight:800;font-size:0.95rem;box-shadow:0 4px 12px rgba(16,185,129,0.3);'>
                    {step['step']}
                </div>
                <div style='font-size:1.85rem;margin:0.5rem 0 0.75rem 0;'>{step['icon']}</div>
                <div style='font-size:1.05rem;font-weight:700;color:{COLORS['slate_900']};
                    margin-bottom:0.4rem;letter-spacing:-0.015em;'>{step['title']}</div>
                <div style='font-size:0.85rem;color:{COLORS['slate_600']};line-height:1.5;'>{step['description']}</div>
            </div>"""
            for step in HOW_IT_WORKS
        ])}
    </div>
    """)

    # ---- ROLE-BASED BENEFITS ----
    _html(f"""
    <div style='text-align:center;margin:3rem 0 1.25rem 0;'>
        <div style='display:inline-block;background:linear-gradient(135deg,#ede9fe 0%,#ddd6fe 100%);
            color:#5b21b6;padding:0.3rem 0.75rem;border-radius:9999px;font-size:0.7rem;
            font-weight:700;letter-spacing:0.06em;text-transform:uppercase;
            border:1px solid #c4b5fd;'>For everyone</div>
        <h2 style='font-size:1.85rem;font-weight:800;color:{COLORS['slate_900']};margin:0.75rem 0 0.5rem 0;
            letter-spacing:-0.025em;'>Built for producers, merchants, and customers.</h2>
    </div>
    """)
    _html(f"""
    <div style='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin:1.5rem 0;'>
        {''.join([
            f"""<div style='background:linear-gradient(135deg,#ffffff 0%,{COLORS['slate_50']} 100%);
                border:1px solid {COLORS['slate_200']};border-radius:18px;padding:1.75rem 1.5rem;
                box-shadow:0 2px 8px rgba(0,0,0,0.04);'>
                <div style='display:inline-flex;align-items:center;gap:10px;margin-bottom:0.85rem;'>
                    <div style='display:inline-flex;align-items:center;justify-content:center;
                        width:42px;height:42px;border-radius:12px;background:{GRADIENTS.get(b['color'], GRADIENTS['emerald'])};
                        color:white;font-size:1.3rem;box-shadow:0 4px 12px rgba(0,0,0,0.12);'>{b['icon']}</div>
                    <div>
                        <div style='font-size:0.7rem;color:{COLORS['slate_500']};font-weight:700;
                            text-transform:uppercase;letter-spacing:0.06em;'>For {b['role']}s</div>
                        <div style='font-size:1rem;font-weight:700;color:{COLORS['slate_900']};
                            letter-spacing:-0.015em;line-height:1.2;'>{b['title']}</div>
                    </div>
                </div>
                <ul style='list-style:none;padding:0;margin:0;'>
                    {''.join([
                        f'<li style="display:flex;align-items:flex-start;gap:8px;'
                        f'padding:0.4rem 0;font-size:0.85rem;color:{COLORS["slate_700"]};line-height:1.4;">'
                        f'<span style="color:#10b981;font-weight:700;flex-shrink:0;margin-top:1px;">✓</span>'
                        f'<span>{benefit}</span></li>'
                        for benefit in b['benefits']
                    ])}
                </ul>
            </div>"""
            for b in ROLE_BENEFITS
        ])}
    </div>
    """)

    # ---- BIG CTA ----
    _html(f"""
    <div style='
        text-align:center;
        padding:3rem 1.5rem;
        margin:2.5rem 0 1.5rem 0;
        background:linear-gradient(135deg,#047857 0%,#10b981 50%,#34d399 100%);
        border-radius:24px;
        color:white;
        position:relative;overflow:hidden;
        box-shadow:0 20px 50px rgba(16,185,129,0.3);
    '>
        <div style='position:absolute;top:-50px;right:-50px;width:200px;height:200px;
            background:rgba(255,255,255,0.1);border-radius:50%;'></div>
        <div style='position:absolute;bottom:-30px;left:-30px;width:150px;height:150px;
            background:rgba(255,255,255,0.08);border-radius:50%;'></div>
        <h2 style='font-size:2rem;font-weight:800;margin:0 0 0.5rem 0;letter-spacing:-0.025em;'>
            Ready to modernize your supply chain?
        </h2>
        <p style='font-size:1.05rem;opacity:0.95;max-width:540px;margin:0 auto 1.5rem auto;line-height:1.5;'>
            Join hundreds of producers and merchants already trading on EthioChain.
        </p>
        <div style='display:flex;gap:12px;flex-wrap:wrap;justify-content:center;'>
            <a href='?page=signup' style='display:inline-flex;align-items:center;gap:6px;
                background:white;color:#047857;padding:0.8rem 1.8rem;border-radius:10px;
                font-weight:700;font-size:0.95rem;text-decoration:none;
                box-shadow:0 6px 18px rgba(0,0,0,0.15);letter-spacing:0.01em;'>
                Get started — it's free →
            </a>
            <a href='?page=login' style='display:inline-flex;align-items:center;gap:6px;
                background:rgba(255,255,255,0.15);color:white;padding:0.8rem 1.8rem;
                border-radius:10px;font-weight:700;font-size:0.95rem;text-decoration:none;
                border:1px solid rgba(255,255,255,0.3);letter-spacing:0.01em;'>
                Sign in
            </a>
        </div>
    </div>
    """)

    # ---- FOOTER ----
    try:
        base_url = get_app_url().replace("https://", "").replace("http://", "").rstrip("/")
    except Exception:
        base_url = "eschain.streamlit.app"
    _html(f"""
    <div style='
        margin:1.5rem 0 2.5rem 0;
        padding:1.5rem 0;
        border-top:1px solid {COLORS['slate_200']};
        text-align:center;
        color:{COLORS['slate_500']};
        font-size:0.8rem;
    '>
        <div style='margin-bottom:0.5rem;'>
            <a href='?page=login' style='color:{COLORS['slate_600']};text-decoration:none;margin:0 0.75rem;font-weight:600;'>Sign in</a>·
            <a href='?page=signup' style='color:{COLORS['slate_600']};text-decoration:none;margin:0 0.75rem;font-weight:600;'>Sign up</a>·
            <a href='?page=forgot-password' style='color:{COLORS['slate_600']};text-decoration:none;margin:0 0.75rem;font-weight:600;'>Forgot password</a>
        </div>
        <div>© 2026 {base_url} · AI Supply Chain Platform · Built with ❤️ for Africa</div>
    </div>
    """)
