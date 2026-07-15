-- ============================================================================
-- AI Supply Chain Platform - Row Level Security (RLS) Policies
-- ----------------------------------------------------------------------------
-- Run AFTER schema.sql in Supabase SQL Editor.
-- ============================================================================

alter table public.profiles        enable row level security;
alter table public.products        enable row level security;
alter table public.orders          enable row level security;
alter table public.order_items     enable row level security;
alter table public.agreements      enable row level security;
alter table public.fraud_logs      enable row level security;
alter table public.favorites       enable row level security;
alter table public.cart_items      enable row level security;
alter table public.ai_predictions  enable row level security;
alter table public.notifications   enable row level security;

-- Helper functions
create or replace function public.is_admin()
returns boolean as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin' and is_active = true
  );
$$ language sql security definer stable;

-- ----------------------------------------------------------------------------
-- PROFILES
-- ----------------------------------------------------------------------------
create policy "Profiles are viewable by owner or admin"
  on public.profiles for select
  using (auth.uid() = id or public.is_admin());

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

create policy "Admins can update any profile"
  on public.profiles for update
  using (public.is_admin());

-- ----------------------------------------------------------------------------
-- PRODUCTS
-- ----------------------------------------------------------------------------
create policy "Active products are publicly readable"
  on public.products for select
  using (status = 'active' or auth.uid() = producer_id or public.is_admin());

create policy "Producers can create products"
  on public.products for insert
  with check (auth.uid() = producer_id);

create policy "Producers update own products"
  on public.products for update
  using (auth.uid() = producer_id or public.is_admin());

create policy "Producers delete own products"
  on public.products for delete
  using (auth.uid() = producer_id or public.is_admin());

-- ----------------------------------------------------------------------------
-- ORDERS
-- ----------------------------------------------------------------------------
create policy "Users see orders they participate in"
  on public.orders for select
  using (auth.uid() = buyer_id or auth.uid() = seller_id or public.is_admin());

create policy "Authenticated users can create orders"
  on public.orders for insert
  with check (auth.uid() = buyer_id or auth.uid() = seller_id);

create policy "Buyer/seller can update own orders"
  on public.orders for update
  using (auth.uid() = buyer_id or auth.uid() = seller_id or public.is_admin());

-- ----------------------------------------------------------------------------
-- ORDER_ITEMS
-- ----------------------------------------------------------------------------
create policy "Order items viewable by order participants"
  on public.order_items for select
  using (
    exists (
      select 1 from public.orders o
      where o.id = order_items.order_id
        and (o.buyer_id = auth.uid() or o.seller_id = auth.uid() or public.is_admin())
    )
  );

create policy "Order participants can insert items"
  on public.order_items for insert
  with check (
    exists (
      select 1 from public.orders o
      where o.id = order_items.order_id
        and (o.buyer_id = auth.uid() or o.seller_id = auth.uid())
    )
  );

-- ----------------------------------------------------------------------------
-- AGREEMENTS
-- ----------------------------------------------------------------------------
create policy "Agreement parties can view"
  on public.agreements for select
  using (auth.uid() = producer_id or auth.uid() = merchant_id or public.is_admin());

create policy "Agreement parties can create"
  on public.agreements for insert
  with check (auth.uid() = producer_id or auth.uid() = merchant_id);

create policy "Agreement parties can update"
  on public.agreements for update
  using (auth.uid() = producer_id or auth.uid() = merchant_id or public.is_admin());

-- ----------------------------------------------------------------------------
-- FRAUD_LOGS
-- ----------------------------------------------------------------------------
create policy "Users see own fraud logs"
  on public.fraud_logs for select
  using (auth.uid() = user_id or public.is_admin());

create policy "Admins update fraud logs"
  on public.fraud_logs for update
  using (public.is_admin());

create policy "System can insert fraud logs"
  on public.fraud_logs for insert
  with check (true);

-- ----------------------------------------------------------------------------
-- FAVORITES - owner only
-- ----------------------------------------------------------------------------
create policy "Users manage own favorites"
  on public.favorites for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- CART_ITEMS - owner only
-- ----------------------------------------------------------------------------
create policy "Users manage own cart"
  on public.cart_items for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- AI_PREDICTIONS
-- ----------------------------------------------------------------------------
create policy "Producers see predictions for own products"
  on public.ai_predictions for select
  using (
    producer_id = auth.uid()
    or public.is_admin()
    or exists (
      select 1 from public.products p
      where p.id = ai_predictions.product_id
        and p.producer_id = auth.uid()
    )
  );

create policy "Producers/admins insert predictions"
  on public.ai_predictions for insert
  with check (producer_id = auth.uid() or public.is_admin());

-- ----------------------------------------------------------------------------
-- NOTIFICATIONS - owner only
-- ----------------------------------------------------------------------------
create policy "Users see own notifications"
  on public.notifications for select
  using (auth.uid() = user_id);

create policy "Users update own notifications"
  on public.notifications for update
  using (auth.uid() = user_id);

create policy "Users delete own notifications"
  on public.notifications for delete
  using (auth.uid() = user_id);

create policy "System can insert notifications"
  on public.notifications for insert
  with check (true);
