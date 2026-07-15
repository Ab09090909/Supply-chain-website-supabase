-- ============================================================================
-- AI Supply Chain Platform — v3 Migration
-- ----------------------------------------------------------------------------
-- Run AFTER schema.sql + migration_v2.sql in Supabase SQL Editor.
-- Adds:
--   1. user_preferences table (for merchant + customer preferences)
--   2. New product columns: quality_grade, model, brand, origin, certifications
--   3. Expands unit options (no constraint change — TEXT column)
--   4. Updates seed product prices to ETB-equivalent values
-- ============================================================================

-- --------------------------------------------------------------------------
-- 1. USER_PREFERENCES table (for merchants + customers)
-- --------------------------------------------------------------------------
create table if not exists public.user_preferences (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid not null references public.profiles (id) on delete cascade,
  preferred_categories  text[] default '{}'::text[],
  preferred_producers   uuid[] default '{}'::uuid[],
  max_price_range       numeric(12, 2),
  typical_order_size    integer default 1,
  payment_terms         text default 'Net 30',
  dietary_restrictions  text[] default '{}'::text[],
  preferred_units       text[] default '{}'::text[],
  notification_email    boolean not null default true,
  notification_push     boolean not null default true,
  newsletter_opt_in     boolean not null default false,
  notes                 text,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (user_id)
);

drop trigger if exists user_preferences_updated_at on public.user_preferences;
create trigger user_preferences_updated_at before update on public.user_preferences
  for each row execute function public.handle_updated_at();

create index if not exists idx_user_prefs_user on public.user_preferences (user_id);

alter table public.user_preferences enable row level security;

create policy "Users manage own preferences"
  on public.user_preferences for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Admins can view all preferences"
  on public.user_preferences for select
  using (public.is_admin());

-- --------------------------------------------------------------------------
-- 2. Add new product columns (idempotent)
-- --------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='products' and column_name='quality_grade') then
    alter table public.products add column quality_grade text;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='products' and column_name='model') then
    alter table public.products add column model text;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='products' and column_name='brand') then
    alter table public.products add column brand text;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='products' and column_name='origin') then
    alter table public.products add column origin text;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='products' and column_name='certifications') then
    alter table public.products add column certifications text[] default '{}'::text[];
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='products' and column_name='production_date') then
    alter table public.products add column production_date date;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='products' and column_name='expiry_date') then
    alter table public.products add column expiry_date date;
  end if;
end $$;

-- --------------------------------------------------------------------------
-- 3. Backfill new columns for existing products with sample values
-- --------------------------------------------------------------------------
update public.products set quality_grade = 'Grade A', brand = 'Green Valley', origin = 'Ethiopia', certifications = array['Organic','Fair Trade']
where sku = 'AGR-001' and quality_grade is null;

update public.products set quality_grade = 'Grade A', brand = 'Green Valley', origin = 'Ethiopia', certifications = array['Pasteurized']
where sku = 'AGR-002' and quality_grade is null;

update public.products set quality_grade = 'Premium', brand = 'Green Valley', origin = 'Ethiopia', certifications = array['Organic']
where sku = 'AGR-003' and quality_grade is null;

update public.products set quality_grade = 'Grade A', brand = 'Green Valley', origin = 'Ethiopia'
where sku = 'AGR-004' and quality_grade is null;

update public.products set quality_grade = 'Grade A', brand = 'Sundar Organic', origin = 'Ethiopia', certifications = array['Organic']
where sku = 'AGR-005' and quality_grade is null;

update public.products set quality_grade = 'Premium', brand = 'Sundar Organic', origin = 'Ethiopia', certifications = array['Raw','Unfiltered']
where sku = 'AGR-006' and quality_grade is null;

update public.products set quality_grade = 'Grade A', brand = 'Green Valley', origin = 'Ethiopia'
where sku = 'AGR-007' and quality_grade is null;

update public.products set quality_grade = 'Grade A', brand = 'Green Valley', origin = 'Ethiopia'
where sku = 'AGR-008' and quality_grade is null;

update public.products set quality_grade = 'Premium', brand = 'Sundar Organic', origin = 'Ethiopia'
where sku = 'AGR-009' and quality_grade is null;

update public.products set quality_grade = 'Grade A', brand = 'Sundar Organic', origin = 'Ethiopia'
where sku = 'AGR-010' and quality_grade is null;

update public.products set quality_grade = 'Premium', brand = 'Green Valley', origin = 'Ethiopia', certifications = array['Aged 6 months']
where sku = 'AGR-011' and quality_grade is null;

update public.products set quality_grade = 'Premium', brand = 'Sundar Organic', origin = 'Ethiopia', certifications = array['Extra Virgin']
where sku = 'AGR-012' and quality_grade is null;

update public.products set quality_grade = 'Grade A', brand = 'Green Valley', origin = 'Ethiopia'
where sku = 'AGR-013' and quality_grade is null;

update public.products set quality_grade = 'Premium', brand = 'Sundar Organic', origin = 'Ethiopia'
where sku = 'AGR-014' and quality_grade is null;

-- --------------------------------------------------------------------------
-- 4. Convert prices to ETB (approximate USD × 130 conversion)
-- --------------------------------------------------------------------------
update public.products set price = 546.00 where sku = 'AGR-001';  -- 4.20 USD → ~546 ETB
update public.products set price = 455.00 where sku = 'AGR-002';  -- 3.50 USD
update public.products set price = 1560.00 where sku = 'AGR-003'; -- 12.00 USD
update public.products set price = 715.00 where sku = 'AGR-004';  -- 5.50 USD
update public.products set price = 1040.00 where sku = 'AGR-005'; -- 8.00 USD
update public.products set price = 1949.00 where sku = 'AGR-006'; -- 14.99 USD
update public.products set price = 325.00 where sku = 'AGR-007';  -- 2.50 USD
update public.products set price = 909.00 where sku = 'AGR-008';  -- 6.99 USD
update public.products set price = 1495.00 where sku = 'AGR-009'; -- 11.50 USD
update public.products set price = 260.00 where sku = 'AGR-010';  -- 2.00 USD
update public.products set price = 3120.00 where sku = 'AGR-011'; -- 24.00 USD
update public.products set price = 2469.00 where sku = 'AGR-012'; -- 18.99 USD
update public.products set price = 780.00 where sku = 'AGR-013';  -- 6.00 USD
update public.products set price = 649.00 where sku = 'AGR-014';  -- 4.99 USD

-- Update existing orders to ETB too (multiply by ~130)
update public.orders set subtotal = subtotal * 130, tax = tax * 130, shipping_cost = shipping_cost * 130, total = total * 130;
update public.order_items set unit_price = unit_price * 130;

-- --------------------------------------------------------------------------
-- 5. Update existing cart_items and favorites counts via sample prefs
-- --------------------------------------------------------------------------
insert into public.user_preferences (user_id, preferred_categories, max_price_range, typical_order_size, payment_terms, notification_email, notification_push)
values
  ('a0000000-0000-0000-0000-000000000002', array['Grains','Dairy','Pantry'], 50000.00, 100, 'Net 30', true, true),
  ('a0000000-0000-0000-0000-000000000003', array['Fruits','Vegetables','Dairy'], 5000.00, 5, 'Cash on Delivery', true, true),
  ('a0000000-0000-0000-0000-000000000006', array['Vegetables','Pantry'], 3000.00, 3, 'Cash on Delivery', true, false)
on conflict (user_id) do nothing;

select 'v3 migration complete: user_preferences table + 7 new product columns + ETB prices + sample preferences.' as result;
