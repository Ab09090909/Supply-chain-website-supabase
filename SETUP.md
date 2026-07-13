# 🛠️ Setup Guide — AI Supply Chain Platform (Supabase Edition)

This guide walks you through every step, from zero to running app. Follow the order exactly.

---

## STEP 1 — Unzip the Project

```bash
unzip ai-supply-chain-supabase.zip
cd ai-supply-chain-supabase
```

You should see this structure:

```
ai-supply-chain-supabase/
├── app.py
├── requirements.txt
├── .env.example
├── .streamlit/
├── supabase/
├── database/
├── auth/
├── pages/
├── utils/
└── docs/
```

---

## STEP 2 — Create a Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate     # macOS / Linux
# venv\Scripts\activate      # Windows
```

You should now see `(venv)` in your shell prompt.

---

## STEP 3 — Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- `streamlit` — UI framework
- `supabase` — official Python client
- `python-dotenv` — loads `.env`
- `pandas` — table rendering
- `pydantic` + `email-validator` — input validation

---

## STEP 4 — Create a Supabase Project

1. Go to <https://supabase.com> and sign in (free tier is fine).
2. Click **New Project**.
3. Fill in:
   - **Name:** `ai-supply-chain`
   - **Database password:** pick a strong one and SAVE it
   - **Region:** closest to you
4. Click **Create new project** and wait ~2 minutes for provisioning.

---

## STEP 5 — Get Your API Keys

1. In your Supabase project, go to **Project Settings** (gear icon, bottom-left).
2. Click **API** in the left sidebar.
3. You'll see three values you need:
   - **Project URL** — `https://xxxxx.supabase.co`
   - **anon public key** — long JWT string
   - **service_role key** — long JWT string (KEEP SECRET!)

Leave this tab open — you'll paste these into `.env` next.

---

## STEP 6 — Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` in your editor and replace the placeholders:

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...your-anon-key...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...your-service-role-key...
APP_URL=http://localhost:8501
```

> **Optional:** You can also use `.streamlit/secrets.toml` instead of `.env` — the code reads either. Don't commit either file (they're in `.gitignore`).

---

## STEP 7 — Create the Database Schema

1. In your Supabase project, click **SQL Editor** (left sidebar).
2. Click **+ New query**.
3. Open the file `supabase/schema.sql` from this project, copy its **entire contents**, paste into the SQL editor.
4. Click **Run** (▶ button).
5. You should see "Success. No rows returned."

This creates:
- 7 ENUM types (user_role, order_status, etc.)
- 10 tables (profiles, products, orders, order_items, agreements, fraud_logs, favorites, cart_items, ai_predictions, notifications)
- Auto-update triggers for `updated_at`
- A trigger that auto-creates a `profiles` row whenever a new auth user signs up

---

## STEP 8 — Enable Row-Level Security Policies

1. In SQL Editor, click **+ New query** again.
2. Copy the entire contents of `supabase/policies.sql`, paste, and **Run**.

This enables RLS on all 10 tables and creates policies like:
- "Users can only see/edit their own profile"
- "Producers can only manage their own products"
- "Customers can only see their own cart"
- "Admins can see everything"

---

## STEP 9 — Insert Sample Data

1. In SQL Editor, click **+ New query**.
2. Copy the entire contents of `supabase/seed.sql`, paste, and **Run**.

This inserts:
- 6 demo users (2 producers, 1 merchant, 2 customers, 1 admin)
- 6 products (wheat, milk, avocados, eggs, tomatoes, honey)
- 4 orders with line items
- 2 B2B agreements
- 2 fraud alerts
- 4 favorites + 2 cart items
- 5 AI predictions
- 5 notifications

You should see the message: `Seed data inserted successfully.`

---

## STEP 10 — Configure Supabase Auth (for password reset emails)

1. In Supabase, go to **Authentication > Providers**.
2. Make sure **Email** is enabled (it is by default).
3. Go to **Authentication > URL Configuration**.
4. Set **Site URL** to `http://localhost:8501`.
5. Add `http://localhost:8501` to **Redirect URLs**.
6. (Optional) For email templates, go to **Authentication > Email Templates** and customize.

> For production, you'd configure SMTP under **Authentication > Settings** so reset emails come from your domain. The dev sandbox email works fine for testing.

---

## STEP 11 — Create Loginable Auth Users

The `seed.sql` script inserts profile rows directly, but those users don't have passwords yet. You have **two options**:

### Option A (Recommended) — Sign up via the app
1. Start the app (Step 12 below).
2. Click **Create one** on the login page.
3. Sign up with a fresh email + password + role.
4. The `handle_new_user` trigger auto-creates a profile for you.

### Option B — Create users in Supabase Dashboard
1. Go to **Authentication > Users > Add user**.
2. Enter email + password, click **Create user**.
3. Copy the new user's UUID.
4. Run this SQL to link the seeded profile to the auth user:
   ```sql
   update public.profiles
   set id = '<paste-auth-user-uuid-here>'
   where email = 'producer@demo.com';
   ```
5. Repeat for each demo email.

---

## STEP 12 — Run the App

```bash
streamlit run app.py
```

You should see:

```
  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Open <http://localhost:8501> in your browser. You'll see the **Login page**.

---

## STEP 13 — Test the Auth Flow

1. **Login page** — should render with a green-themed card, email + password fields, "Forgot password?" link.
2. Click **Create one** — should take you to the **Signup page** with role selection cards (Producer / Merchant / Customer / Admin).
3. Fill in the form and submit — you should be logged in and see the role-specific dashboard.
4. Click **Logout** in the sidebar.
5. On the login page, click **Forgot password?** — enter an email, you'll get a reset link (check Supabase Dashboard > Authentication > Users > click user > "Reset password" if SMTP isn't configured).
6. Click the reset link → lands on the **Reset password** page → set a new password → login.

---

## STEP 14 — Deploy to Production

### Option A — Streamlit Community Cloud (free)
1. Push this folder to a GitHub repo.
2. Go to <https://share.streamlit.io>.
3. Connect your repo, select `app.py` as the entry point.
4. In **Secrets**, paste your `.env` contents in TOML format:
   ```toml
   SUPABASE_URL = "https://xxxxx.supabase.co"
   SUPABASE_ANON_KEY = "..."
   SUPABASE_SERVICE_ROLE_KEY = "..."
   APP_URL = "https://your-app-name.streamlit.app"
   ```
5. Update Supabase **Site URL** and **Redirect URLs** to include the Streamlit URL.

### Option B — Docker / VPS
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## 🧯 Troubleshooting

### "Supabase credentials not found"
→ Your `.env` file is missing or has placeholder values. Re-do Step 6.

### "Profile not found. Please contact admin."
→ The `handle_new_user` trigger didn't fire. Run this manually:
```sql
insert into public.profiles (id, email, full_name, role)
select id, email, split_part(email, '@', 1), 'customer'
from auth.users
where id not in (select id from public.profiles);
```

### "relation public.profiles does not exist"
→ You skipped Step 7. Run `supabase/schema.sql` first.

### Reset password email never arrives
→ In dev, Supabase shows a "reset password" link in **Authentication > Users > click user**. In production, configure SMTP.

### Streamlit shows "ImportError: No module named 'supabase'"
→ Activate your venv (`source venv/bin/activate`) and re-run `pip install -r requirements.txt`.

---

## ✅ You're Done!

You now have a clean, production-ready AI Supply Chain Platform on Supabase. To add new features:
- New table → add to `supabase/schema.sql`, add RLS to `policies.sql`
- New page → drop a file in `pages/<role>/`, import it in `app.py`'s `render_role_content()`
- New role → add to `utils/constants.py` and create `pages/<new_role>/`
