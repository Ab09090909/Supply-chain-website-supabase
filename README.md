# 📦 AI Supply Chain Platform — Supabase Edition

A clean, maintainable rebuild of the [AI Supply Chain Platform](https://github.com/Ab09090909/AI-supply-chain-) using **Streamlit + Supabase**.

This version fixes the common pain points of the original repo:
- ✅ **No SQLite "relation does not exist" errors** — schema lives in Supabase SQL files
- ✅ **No scattered DB helper duplicates** — one `database/` package
- ✅ **Professional auth pages** — login, signup, forgot-password, reset-password (via Supabase Auth)
- ✅ **Row-Level Security** — every table is RLS-protected
- ✅ **Clear role separation** — `pages/{producer,merchant,customer,admin}/`
- ✅ **Sample seed data** — run one SQL file and you're ready to demo

---

## 🎯 Tech Stack

| Layer       | Technology                                     |
|-------------|------------------------------------------------|
| Frontend    | Streamlit ≥ 1.39                               |
| Database    | Supabase (PostgreSQL + Auth + RLS)             |
| Auth        | Supabase Auth (email + password, reset emails) |
| Language    | Python 3.10+                                   |
| Config      | `.env` + `.streamlit/secrets.toml`             |

---

## 📁 Folder Structure

```
ai-supply-chain-supabase/
├── app.py                          # MAIN ENTRY - run this with streamlit
├── requirements.txt                # Python deps
├── .env.example                    # Copy to .env and fill in
├── .gitignore
├── README.md                       # This file
├── SETUP.md                        # Step-by-step setup guide
│
├── .streamlit/
│   ├── config.toml                 # Streamlit theme + server config
│   └── secrets.toml.example        # Copy to secrets.toml
│
├── supabase/                       # ← All SQL lives here
│   ├── schema.sql                  # Creates all 10 tables + enums + triggers
│   ├── policies.sql                # Row-Level Security policies
│   ├── seed.sql                    # Sample data for every table
│   └── config.toml                 # Local Supabase CLI config (optional)
│
├── database/                       # ← Supabase client wrapper
│   ├── __init__.py
│   └── connection.py               # get_supabase_client() + get_supabase_admin_client()
│
├── auth/                           # ← Authentication module
│   ├── __init__.py
│   ├── session.py                  # st.session_state helpers
│   ├── service.py                  # sign_up / sign_in / sign_out / reset_password
│   └── pages.py                    # Login / Signup / Forgot-password / Reset-password UI
│
├── pages/                          # ← Role-specific pages
│   ├── __init__.py
│   ├── producer/
│   │   ├── __init__.py
│   │   ├── dashboard.py            # KPIs, inventory snapshot, recent orders
│   │   ├── inventory.py            # Add / view / edit products
│   │   ├── orders.py               # View orders from buyers
│   │   └── profile.py              # Edit producer profile
│   ├── merchant/
│   │   ├── __init__.py
│   │   ├── dashboard.py            # Spend, open orders, agreements
│   │   ├── orders.py               # Orders placed with producers
│   │   └── profile.py
│   ├── customer/
│   │   ├── __init__.py
│   │   ├── marketplace.py          # Browse + favorite + add to cart
│   │   ├── cart.py                 # Checkout + place order
│   │   ├── orders.py               # Order history
│   │   └── profile.py
│   └── admin/
│       ├── __init__.py
│       ├── dashboard.py            # Platform-wide stats
│       ├── users.py                # Manage users (activate/deactivate)
│       ├── fraud.py                # Review fraud alerts
│       └── profile.py
│
├── utils/                          # ← Shared helpers
│   ├── __init__.py
│   ├── ui.py                       # page_header, metric_card, role_badge, ...
│   ├── constants.py                # ROLE_OPTIONS, ROLE_DESCRIPTIONS, ROLE_COLORS
│   └── helpers.py                  # format_currency, format_datetime, generate_order_number
│
└── docs/
    └── SCHEMA.md                   # Table reference
```

---

## 🗄️ Database Tables (10 total)

| Table             | Purpose                                          |
|-------------------|--------------------------------------------------|
| `profiles`        | Extends `auth.users` with role + business fields |
| `products`        | Producer inventory items                         |
| `orders`          | Purchase orders (buyer ↔ seller)                 |
| `order_items`     | Normalized line items per order                  |
| `agreements`      | B2B supply contracts (producer ↔ merchant)       |
| `fraud_logs`      | AI fraud-detection alerts                        |
| `favorites`       | Customer wishlist                                |
| `cart_items`      | Customer shopping cart                           |
| `ai_predictions`  | ML model outputs (demand, price, spoilage)       |
| `notifications`   | Per-user in-app notifications                    |

Full column-level reference: see [`docs/SCHEMA.md`](docs/SCHEMA.md).

---

## 🚀 Quick Start

> Full step-by-step guide: [`SETUP.md`](SETUP.md)

```bash
# 1. Unzip
unzip ai-supply-chain-supabase.zip
cd ai-supply-chain-supabase

# 2. Install deps
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env and paste your Supabase URL + anon key + service role key

# 4. Set up database (in Supabase Dashboard > SQL Editor, run in order):
#    a. supabase/schema.sql
#    b. supabase/policies.sql
#    c. supabase/seed.sql

# 5. Run
streamlit run app.py
```

Open <http://localhost:8501>.

---

## 🔐 Demo Accounts

After running `supabase/seed.sql`, these profiles exist in the `profiles` table. To make them login-able, either:

1. **Recommended:** Sign up new users via the **Signup page** in the app (the trigger will create matching profiles automatically), OR
2. Use **Supabase Dashboard > Authentication > Users > Add User** with the demo emails below, then run:
   ```sql
   update public.profiles set id = '<auth-user-uuid>'
   where email = 'producer@demo.com';
   ```

| Role      | Email              | Demo Password |
|-----------|--------------------|---------------|
| Producer  | producer@demo.com  | (set on signup) |
| Merchant  | merchant@demo.com  | (set on signup) |
| Customer  | customer@demo.com  | (set on signup) |
| Admin     | admin@demo.com     | (set on signup) |

---

## 🆚 What Changed vs the Original Repo

| Original Repo Issue                     | This Version's Fix                                |
|-----------------------------------------|----------------------------------------------------|
| SQLite-only, breaks on Supabase         | Pure Supabase from day 1                          |
| `db.py` duplicated in 4 role folders    | Single `database/connection.py`                   |
| Plain-text password comparison in app.py| Real auth via Supabase Auth (bcrypt-hashed)       |
| No forgot-password flow                 | Full reset email flow                             |
| No RLS — any user could read any row    | RLS on every table; users see only their data     |
| `init_db.py` + `init.py` + `create_models.py` overlapped | One `schema.sql` + one `seed.sql`   |
| Hard-coded user IDs (`self.customer_id = 3`) | Uses `auth.uid()` from session                |

---

## 📝 License

MIT
