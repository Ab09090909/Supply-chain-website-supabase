-- ============================================================================
-- AI Supply Chain Platform - Supabase Schema
-- ----------------------------------------------------------------------------
-- Run this in: Supabase Dashboard > SQL Editor > New Query
-- Creates: profiles, products, orders, order_items, agreements, fraud_logs,
--          favorites, cart_items, ai_predictions, notifications
-- Uses:    Supabase Auth (auth.users) for password management
-- ============================================================================

create extension if not exists "pgcrypto";

-- ----------------------------------------------------------------------------
-- 1. ENUM types
-- ----------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_type where typname = 'user_role') then
    create type user_role as enum ('producer', 'merchant', 'customer', 'admin');
  end if;
  if not exists (select 1 from pg_type where typname = 'order_status') then
    create type order_status as enum ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled');
  end if;
  if not exists (select 1 from pg_type where typname = 'payment_status') then
    create type payment_status as enum ('pending', 'paid', 'failed', 'refunded');
  end if;
  if not exists (select 1 from pg_type where typname = 'product_status') then
    create type product_status as enum ('active', 'inactive', 'draft');
  end if;
  if not exists (select 1 from pg_type where typname = 'agreement_status') then
    create type agreement_status as enum ('active', 'pending', 'expired', 'cancelled');
  end if;
  if not exists (select 1 from pg_type where typname = 'fraud_status') then
    create type fraud_status as enum ('pending', 'reviewing', 'confirmed', 'dismissed');
  end if;
  if not exists (select 1 from pg_type where typname = 'notification_type') then
    create type notification_type as enum ('info', 'warning', 'error', 'success');
  end if;
end $$;

-- ----------------------------------------------------------------------------
-- 2. PROFILES table (extends auth.users with role + business fields)
-- ----------------------------------------------------------------------------
create table if not exists public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  email       text not null unique,
  full_name   text not null,
  role        user_role not null default 'customer',
  phone       text,
  location    text,
  avatar_url  text,
  company     text,
  is_active   boolean not null default true,
  is_verified boolean not null default false,
  last_login  timestamptz,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create or replace function public.handle_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists profiles_updated_at on public.profiles;
create trigger profiles_updated_at before update on public.profiles
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- 3. PRODUCTS table
-- ----------------------------------------------------------------------------
create table if not exists public.products (
  id                uuid primary key default gen_random_uuid(),
  sku               text unique not null,
  name              text not null,
  description       text,
  category          text,
  price             numeric(10, 2) not null default 0 check (price >= 0),
  stock             integer not null default 0 check (stock >= 0),
  unit              text default 'unit',
  reorder_point     integer not null default 0,
  reorder_quantity  integer not null default 0,
  image_url         text,
  producer_id       uuid not null references public.profiles (id) on delete cascade,
  status            product_status not null default 'active',
  metadata          jsonb default '{}'::jsonb,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index if not exists idx_products_producer on public.products (producer_id);
create index if not exists idx_products_category on public.products (category);
create index if not exists idx_products_status  on public.products (status);

drop trigger if exists products_updated_at on public.products;
create trigger products_updated_at before update on public.products
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- 4. ORDERS table
-- ----------------------------------------------------------------------------
create table if not exists public.orders (
  id                uuid primary key default gen_random_uuid(),
  order_number      text unique not null,
  buyer_id          uuid not null references public.profiles (id) on delete restrict,
  buyer_role        user_role not null,
  seller_id         uuid not null references public.profiles (id) on delete restrict,
  seller_role       user_role not null,
  subtotal          numeric(12, 2) not null default 0,
  tax               numeric(12, 2) not null default 0,
  shipping_cost     numeric(12, 2) not null default 0,
  total             numeric(12, 2) not null default 0,
  status            order_status not null default 'pending',
  payment_status    payment_status not null default 'pending',
  shipping_address  jsonb,
  notes             text,
  placed_at         timestamptz not null default now(),
  confirmed_at      timestamptz,
  shipped_at        timestamptz,
  delivered_at      timestamptz,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index if not exists idx_orders_buyer  on public.orders (buyer_id);
create index if not exists idx_orders_seller on public.orders (seller_id);
create index if not exists idx_orders_status on public.orders (status);

drop trigger if exists orders_updated_at on public.orders;
create trigger orders_updated_at before update on public.orders
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- 5. ORDER_ITEMS table (normalized line items)
-- ----------------------------------------------------------------------------
create table if not exists public.order_items (
  id          uuid primary key default gen_random_uuid(),
  order_id    uuid not null references public.orders (id) on delete cascade,
  product_id  uuid references public.products (id) on delete set null,
  sku         text not null,
  name        text not null,
  unit_price  numeric(10, 2) not null check (unit_price >= 0),
  quantity    integer not null check (quantity > 0),
  subtotal    numeric(12, 2) generated always as (unit_price * quantity) stored,
  created_at  timestamptz not null default now()
);

create index if not exists idx_order_items_order on public.order_items (order_id);

-- ----------------------------------------------------------------------------
-- 6. AGREEMENTS table (B2B contracts)
-- ----------------------------------------------------------------------------
create table if not exists public.agreements (
  id              uuid primary key default gen_random_uuid(),
  producer_id     uuid not null references public.profiles (id) on delete cascade,
  merchant_id     uuid not null references public.profiles (id) on delete cascade,
  agreement_code  text unique not null,
  title           text,
  terms           text,
  start_date      date,
  end_date        date,
  status          agreement_status not null default 'pending',
  metadata        jsonb default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

drop trigger if exists agreements_updated_at on public.agreements;
create trigger agreements_updated_at before update on public.agreements
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- 7. FRAUD_LOGS table
-- ----------------------------------------------------------------------------
create table if not exists public.fraud_logs (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid references public.profiles (id) on delete set null,
  order_id          uuid references public.orders (id) on delete set null,
  risk_score        numeric(4, 3) not null default 0 check (risk_score >= 0 and risk_score <= 1),
  fraud_type        text,
  status            fraud_status not null default 'pending',
  transaction_data  jsonb default '{}'::jsonb,
  risk_factors      jsonb default '[]'::jsonb,
  reviewed_by       uuid references public.profiles (id) on delete set null,
  reviewed_at       timestamptz,
  review_notes      text,
  created_at        timestamptz not null default now()
);

create index if not exists idx_fraud_status on public.fraud_logs (status);

-- ----------------------------------------------------------------------------
-- 8. FAVORITES table
-- ----------------------------------------------------------------------------
create table if not exists public.favorites (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles (id) on delete cascade,
  product_id  uuid not null references public.products (id) on delete cascade,
  created_at  timestamptz not null default now(),
  unique (user_id, product_id)
);

create index if not exists idx_favorites_user on public.favorites (user_id);

-- ----------------------------------------------------------------------------
-- 9. CART_ITEMS table
-- ----------------------------------------------------------------------------
create table if not exists public.cart_items (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles (id) on delete cascade,
  product_id  uuid not null references public.products (id) on delete cascade,
  quantity    integer not null default 1 check (quantity > 0),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (user_id, product_id)
);

drop trigger if exists cart_items_updated_at on public.cart_items;
create trigger cart_items_updated_at before update on public.cart_items
  for each row execute function public.handle_updated_at();

-- ----------------------------------------------------------------------------
-- 10. AI_PREDICTIONS table
-- ----------------------------------------------------------------------------
create table if not exists public.ai_predictions (
  id                uuid primary key default gen_random_uuid(),
  producer_id       uuid references public.profiles (id) on delete set null,
  product_id        uuid references public.products (id) on delete set null,
  prediction_type   text not null,
  predicted_value   numeric(12, 2),
  confidence        numeric(4, 3) check (confidence >= 0 and confidence <= 1),
  model_version     text,
  input_features    jsonb default '{}'::jsonb,
  created_at        timestamptz not null default now()
);

create index if not exists idx_predictions_product on public.ai_predictions (product_id);
create index if not exists idx_predictions_type    on public.ai_predictions (prediction_type);

-- ----------------------------------------------------------------------------
-- 11. NOTIFICATIONS table
-- ----------------------------------------------------------------------------
create table if not exists public.notifications (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles (id) on delete cascade,
  title       text not null,
  message     text,
  type        notification_type not null default 'info',
  is_read     boolean not null default false,
  link        text,
  created_at  timestamptz not null default now()
);

create index if not exists idx_notifications_user on public.notifications (user_id, is_read);

-- ----------------------------------------------------------------------------
-- 12. HELPER: auto-create profile when a new auth user signs up
-- ----------------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name, role, phone, location, company)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
    coalesce((new.raw_user_meta_data->>'role')::user_role, 'customer'),
    new.raw_user_meta_data->>'phone',
    new.raw_user_meta_data->>'location',
    new.raw_user_meta_data->>'company'
  )
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
