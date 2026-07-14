-- ============================================================================
-- AI Supply Chain Platform — v4 Migration
-- ----------------------------------------------------------------------------
-- Run AFTER schema.sql + migration_v2.sql + migration_v3.sql.
-- Adds:
--   1. merchant_requests table (producer → merchant match requests + agreements)
--   2. New preference columns (preferred_product_names, quality_grades, brands,
--      models, classes, levels, custom_categories)
-- ============================================================================

-- --------------------------------------------------------------------------
-- 1. MERCHANT_REQUESTS table (producer sends match request to merchant)
-- --------------------------------------------------------------------------
create table if not exists public.merchant_requests (
  id                uuid primary key default gen_random_uuid(),
  producer_id       uuid not null references public.profiles (id) on delete cascade,
  merchant_id       uuid not null references public.profiles (id) on delete cascade,
  product_id        uuid references public.products (id) on delete set null,
  match_percentage  numeric(5, 2) not null default 0 check (match_percentage >= 0 and match_percentage <= 100),
  status            text not null default 'pending' check (status in ('pending', 'confirmed', 'cancelled', 'expired')),
  proposed_terms    text,
  agreement_code    text unique,
  producer_message  text,
  merchant_response text,
  created_at        timestamptz not null default now(),
  responded_at      timestamptz,
  unique (producer_id, merchant_id, product_id)
);

create index if not exists idx_mreq_producer on public.merchant_requests (producer_id, status);
create index if not exists idx_mreq_merchant on public.merchant_requests (merchant_id, status);

alter table public.merchant_requests enable row level security;

create policy "Producers see own sent requests"
  on public.merchant_requests for select
  using (auth.uid() = producer_id or auth.uid() = merchant_id or public.is_admin());

create policy "Producers can create requests"
  on public.merchant_requests for insert
  with check (auth.uid() = producer_id);

create policy "Producers can update own requests"
  on public.merchant_requests for update
  using (auth.uid() = producer_id or auth.uid() = merchant_id or public.is_admin());

create policy "Producers can cancel own requests"
  on public.merchant_requests for delete
  using (auth.uid() = producer_id or public.is_admin());

-- --------------------------------------------------------------------------
-- 2. Add new preference columns (idempotent)
-- --------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='user_preferences' and column_name='preferred_product_names') then
    alter table public.user_preferences add column preferred_product_names text[] default '{}'::text[];
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='user_preferences' and column_name='preferred_quality_grades') then
    alter table public.user_preferences add column preferred_quality_grades text[] default '{}'::text[];
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='user_preferences' and column_name='preferred_brands') then
    alter table public.user_preferences add column preferred_brands text[] default '{}'::text[];
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='user_preferences' and column_name='preferred_models') then
    alter table public.user_preferences add column preferred_models text[] default '{}'::text[];
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='user_preferences' and column_name='preferred_classes') then
    alter table public.user_preferences add column preferred_classes text[] default '{}'::text[];
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='user_preferences' and column_name='preferred_levels') then
    alter table public.user_preferences add column preferred_levels text[] default '{}'::text[];
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='user_preferences' and column_name='custom_categories') then
    alter table public.user_preferences add column custom_categories text[] default '{}'::text[];
  end if;
end $$;

select 'v4 migration complete: merchant_requests table + 7 new preference columns.' as result;
