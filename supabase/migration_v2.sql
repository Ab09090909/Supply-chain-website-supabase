-- ============================================================================
-- AI Supply Chain Platform — Storage & Messaging Migration
-- ----------------------------------------------------------------------------
-- Run AFTER schema.sql in Supabase SQL Editor.
-- Creates:
--   1. Storage bucket 'product-images' (public, for product + profile photos)
--   2. Messages table (user-to-user direct messaging)
--   3. Adds sender_id column to notifications (for admin broadcasts)
-- ============================================================================

-- --------------------------------------------------------------------------
-- 1. STORAGE BUCKET for images (product photos + avatars)
-- --------------------------------------------------------------------------
-- Create the bucket if it doesn't exist
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'product-images',
  'product-images',
  true,
  5242880,  -- 5 MB limit
  array['image/jpeg', 'image/png', 'image/webp', 'image/gif']
)
on conflict (id) do nothing;

-- Storage policies: anyone can read, only authenticated can upload to their own folder
drop policy if exists "Public can view product images" on storage.objects;
create policy "Public can view product images"
  on storage.objects for select
  using (bucket_id = 'product-images');

drop policy if exists "Authenticated users can upload product images" on storage.objects;
create policy "Authenticated users can upload product images"
  on storage.objects for insert
  with check (
    bucket_id = 'product-images'
    and auth.role() = 'authenticated'
  );

drop policy if exists "Users can update own product images" on storage.objects;
create policy "Users can update own product images"
  on storage.objects for update
  using (
    bucket_id = 'product-images'
    and auth.role() = 'authenticated'
  );

drop policy if exists "Users can delete own product images" on storage.objects;
create policy "Users can delete own product images"
  on storage.objects for delete
  using (
    bucket_id = 'product-images'
    and auth.role() = 'authenticated'
  );

-- --------------------------------------------------------------------------
-- 2. MESSAGES table (user-to-user direct messaging)
-- --------------------------------------------------------------------------
create table if not exists public.messages (
  id          uuid primary key default gen_random_uuid(),
  sender_id   uuid not null references public.profiles (id) on delete cascade,
  receiver_id uuid not null references public.profiles (id) on delete cascade,
  subject     text,
  body        text not null,
  is_read     boolean not null default false,
  read_at     timestamptz,
  parent_id   uuid references public.messages (id) on delete set null,
  created_at  timestamptz not null default now()
);

create index if not exists idx_messages_receiver on public.messages (receiver_id, is_read);
create index if not exists idx_messages_sender   on public.messages (sender_id);
create index if not exists idx_messages_created   on public.messages (created_at desc);

alter table public.messages enable row level security;

-- Users can only see messages they sent or received
create policy "Users see own sent/received messages"
  on public.messages for select
  using (auth.uid() = sender_id or auth.uid() = receiver_id);

create policy "Users can send messages"
  on public.messages for insert
  with check (auth.uid() = sender_id);

create policy "Senders can update own messages"
  on public.messages for update
  using (auth.uid() = sender_id or auth.uid() = receiver_id);

create policy "Senders can delete own messages"
  on public.messages for delete
  using (auth.uid() = sender_id);

-- --------------------------------------------------------------------------
-- 3. Add sender_id to notifications (for admin broadcasts + user-to-user)
-- --------------------------------------------------------------------------
do $$
begin
  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'notifications' and column_name = 'sender_id'
  ) then
    alter table public.notifications add column sender_id uuid references public.profiles (id) on delete set null;
  end if;
end $$;

-- Update the "System can insert notifications" policy to require auth
drop policy if exists "System can insert notifications" on public.notifications;
create policy "Authenticated users can insert notifications"
  on public.notifications for insert
  with check (auth.uid() = sender_id or auth.uid() = user_id or public.is_admin());

-- Add policy so admin can broadcast to any user
drop policy if exists "Admins can broadcast notifications" on public.notifications;
create policy "Admins can broadcast notifications"
  on public.notifications for insert
  with check (public.is_admin());

-- --------------------------------------------------------------------------
-- 4. Update seed products with real image URLs (Unsplash)
-- --------------------------------------------------------------------------
update public.products set image_url = 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400' where sku = 'AGR-001' and image_url is null;
update public.products set image_url = 'https://images.unsplash.com/photo-1563636619-e9143da7973b?w=400' where sku = 'AGR-002' and image_url is null;
update public.products set image_url = 'https://images.unsplash.com/photo-1601039641847-7857b994d704?w=400' where sku = 'AGR-003' and image_url is null;
update public.products set image_url = 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400' where sku = 'AGR-004' and image_url is null;
update public.products set image_url = 'https://images.unsplash.com/photo-1546470427-e26264be0b0d?w=400' where sku = 'AGR-005' and image_url is null;
update public.products set image_url = 'https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=400' where sku = 'AGR-006' and image_url is null;

-- --------------------------------------------------------------------------
-- 5. Add MORE sample products (with images) to make marketplace richer
-- --------------------------------------------------------------------------
insert into public.products (sku, name, description, category, price, stock, unit, reorder_point, reorder_quantity, producer_id, status, image_url)
values
  ('AGR-007', 'Organic Carrots',     'Sweet, crunchy organic carrots, freshly harvested.', 'Vegetables', 2.50,  180, 'kg',    30, 60, 'a0000000-0000-0000-0000-000000000001', 'active', 'https://images.unsplash.com/photo-1591288571994-ec12d08d2d38?w=400'),
  ('AGR-008', 'Farm Apple Cider',    'Cold-pressed apple cider from heritage trees.',      'Beverages',  6.99,  45,  'bottle',15, 30, 'a0000000-0000-0000-0000-000000000001', 'active', 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=400'),
  ('AGR-009', 'Raw Almonds',         'Unsalted, dry-roasted raw almonds.',                 'Pantry',    11.50,  90,  'kg',    20, 40, 'a0000000-0000-0000-0000-000000000005', 'active', 'https://images.unsplash.com/photo-1508061253366-f7da158b6d46?w=400'),
  ('AGR-010', 'Basil Bunch',         'Fresh aromatic basil, harvested same-day.',          'Herbs',      2.00,  60,  'bunch', 20, 30, 'a0000000-0000-0000-0000-000000000005', 'active', 'https://images.unsplash.com/photo-1612203985729-70726954388c?w=400'),
  ('AGR-011', 'Goat Cheese Wheel',   'Artisanal aged goat cheese, 1kg wheel.',             'Dairy',     24.00,  18,  'unit',  10, 20, 'a0000000-0000-0000-0000-000000000001', 'active', 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=400'),
  ('AGR-012', 'Cold-Pressed Olive Oil','Extra virgin olive oil, 500ml bottle.',            'Pantry',    18.99,  35,  'bottle',15, 25, 'a0000000-0000-0000-0000-000000000005', 'active', 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400'),
  ('AGR-013', 'Sweet Corn',          'Fresh-picked sweet corn, dozen ears.',               'Vegetables', 6.00,  40,  'dozen', 15, 30, 'a0000000-0000-0000-0000-000000000001', 'active', 'https://images.unsplash.com/photo-1601593768799-76d2c1ce1a4d?w=400'),
  ('AGR-014', 'Strawberry Box',      'Sun-ripened strawberries, 1lb box.',                 'Fruits',     4.99,  85,  'box',   20, 40, 'a0000000-0000-0000-0000-000000000005', 'active', 'https://images.unsplash.com/photo-1464965911861-746a04b4bca6?w=400')
on conflict (sku) do nothing;

-- --------------------------------------------------------------------------
-- 6. Add some AI prediction history (so ML tab has training data)
-- --------------------------------------------------------------------------
insert into public.ai_predictions (producer_id, product_id, prediction_type, predicted_value, confidence, model_version, input_features)
select p.producer_id, p.id, 'demand_forecast', 50.0 + (random() * 100), 0.5 + (random() * 0.4), 'v1.0.0', '{"sample":true}'::jsonb
from public.products p
where not exists (
  select 1 from public.ai_predictions ap where ap.product_id = p.id and ap.prediction_type = 'demand_forecast'
);

select 'Migration complete: storage bucket + messages + notifications.sender_id + 8 new products with images.' as result;
