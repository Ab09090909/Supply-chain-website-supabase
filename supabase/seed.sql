-- ============================================================================
-- AI Supply Chain Platform - Sample Seed Data
-- ----------------------------------------------------------------------------
-- Run AFTER schema.sql AND policies.sql in Supabase SQL Editor.
--
-- NOTE: This script inserts rows directly into public.profiles using fixed
-- demo UUIDs. To make these users fully login-able, you ALSO need to create
-- matching auth.users via the Streamlit Signup page OR via:
--   Supabase Dashboard > Authentication > Users > Add User
-- Then run:
--   update public.profiles set id = '<auth-user-uuid>'
--   where email = 'producer@demo.com';
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. DEMO USERS (profiles)
-- ----------------------------------------------------------------------------
insert into public.profiles (id, email, full_name, role, phone, location, company, is_active, is_verified)
values
  ('a0000000-0000-0000-0000-000000000001', 'producer@demo.com',   'Green Valley Farms',   'producer',  '+1 555-0101', 'California, USA', 'Green Valley Farms LLC',  true, true),
  ('a0000000-0000-0000-0000-000000000002', 'merchant@demo.com',   'Metro Retail Inc',     'merchant',  '+1 555-0102', 'New York, USA',   'Metro Retail Inc',       true, true),
  ('a0000000-0000-0000-0000-000000000003', 'customer@demo.com',   'John Consumer',        'customer',  '+1 555-0103', 'Texas, USA',      null,                     true, true),
  ('a0000000-0000-0000-0000-000000000004', 'admin@demo.com',      'System Admin',         'admin',     '+1 555-0100', 'Remote',          'AI Supply Chain',        true, true),
  ('a0000000-0000-0000-0000-000000000005', 'sundar@demo.com',     'Sundar Organic Farms', 'producer',  '+1 555-0201', 'Oregon, USA',     'Sundar Organic',         true, true),
  ('a0000000-0000-0000-0000-000000000006', 'maria@demo.com',      'Maria Lopez',          'customer',  '+1 555-0203', 'Florida, USA',    null,                     true, true)
on conflict (email) do nothing;

-- ----------------------------------------------------------------------------
-- 2. PRODUCTS (6 items across 2 producers)
-- ----------------------------------------------------------------------------
insert into public.products (sku, name, description, category, price, stock, unit, reorder_point, reorder_quantity, producer_id, status)
values
  ('AGR-001', 'Organic Wheat',        'Premium grade hard red winter wheat, sustainably grown.', 'Grains',     4.20,  450, 'ton',    100, 50,  'a0000000-0000-0000-0000-000000000001', 'active'),
  ('AGR-002', 'Fresh Dairy Milk',     'Farm-fresh whole milk, pasteurized and homogenized.',      'Dairy',      3.50,   35, 'gallon',  50, 100,'a0000000-0000-0000-0000-000000000001', 'active'),
  ('AGR-003', 'Premium Avocados',     'Hass avocados, hand-picked at peak ripeness.',             'Fruits',    12.00,   12, 'unit',    40, 100,'a0000000-0000-0000-0000-000000000001', 'active'),
  ('AGR-004', 'Free Range Eggs',      'Organic free-range eggs, dozen.',                          'Dairy',      5.50,  200, 'dozen',   80, 50, 'a0000000-0000-0000-0000-000000000001', 'active'),
  ('AGR-005', 'Heirloom Tomatoes',    'Heirloom tomato variety pack, vine-ripened.',              'Vegetables', 8.00,   75, 'kg',      30, 60, 'a0000000-0000-0000-0000-000000000005', 'active'),
  ('AGR-006', 'Wildflower Honey',     'Raw, unfiltered wildflower honey, 500g jar.',              'Pantry',    14.99,   60, 'unit',    25, 50, 'a0000000-0000-0000-0000-000000000005', 'active')
on conflict (sku) do nothing;

-- ----------------------------------------------------------------------------
-- 3. ORDERS
-- ----------------------------------------------------------------------------
insert into public.orders (order_number, buyer_id, buyer_role, seller_id, seller_role, subtotal, tax, shipping_cost, total, status, payment_status, shipping_address, notes)
values
  ('ORD-2024-001', 'a0000000-0000-0000-0000-000000000002', 'merchant', 'a0000000-0000-0000-0000-000000000001', 'producer',
   42.00, 3.36, 5.00, 50.36, 'delivered', 'paid',
   '{"name":"Metro Retail","street":"123 Main St","city":"New York","state":"NY","zip":"10001","country":"USA"}'::jsonb,
   'Repeat order - bulk pricing'),
  ('ORD-2024-002', 'a0000000-0000-0000-0000-000000000003', 'customer', 'a0000000-0000-0000-0000-000000000001', 'producer',
   72.00, 5.76, 8.00, 85.76, 'shipped', 'paid',
   '{"name":"John Consumer","street":"456 Oak Ave","city":"Austin","state":"TX","zip":"73301","country":"USA"}'::jsonb,
   null),
  ('ORD-2024-003', 'a0000000-0000-0000-0000-000000000006', 'customer', 'a0000000-0000-0000-0000-000000000005', 'producer',
   32.00, 2.56, 6.00, 40.56, 'processing', 'pending',
   '{"name":"Maria Lopez","street":"789 Palm St","city":"Miami","state":"FL","zip":"33101","country":"USA"}'::jsonb,
   'Gift order - please include note'),
  ('ORD-2024-004', 'a0000000-0000-0000-0000-000000000002', 'merchant', 'a0000000-0000-0000-0000-000000000005', 'producer',
   240.00, 19.20, 12.00, 271.20, 'pending', 'pending',
   '{"name":"Metro Retail","street":"123 Main St","city":"New York","state":"NY","zip":"10001","country":"USA"}'::jsonb,
   null)
on conflict (order_number) do nothing;

-- ----------------------------------------------------------------------------
-- 4. ORDER_ITEMS
-- ----------------------------------------------------------------------------
insert into public.order_items (order_id, product_id, sku, name, unit_price, quantity)
select o.id, p.id, p.sku, p.name, p.price, oi.qty
from (values
  ('ORD-2024-001', 'AGR-001', 10),
  ('ORD-2024-002', 'AGR-003', 6),
  ('ORD-2024-003', 'AGR-005', 4),
  ('ORD-2024-004', 'AGR-006', 16)
) as oi(order_number, sku, qty)
join public.orders o on o.order_number = oi.order_number
join public.products p on p.sku = oi.sku
where not exists (
  select 1 from public.order_items oi2
  where oi2.order_id = o.id and oi2.product_id = p.id
);

-- ----------------------------------------------------------------------------
-- 5. AGREEMENTS
-- ----------------------------------------------------------------------------
insert into public.agreements (producer_id, merchant_id, agreement_code, title, terms, start_date, end_date, status)
values
  ('a0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000002', 'AGR-2024-001',
   'Annual Wheat Supply Contract',
   'Producer agrees to supply up to 5,000 tons of organic wheat per quarter at fixed unit price of $4.20/ton. Payment terms: Net 30.',
   '2024-01-01', '2024-12-31', 'active'),
  ('a0000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000002', 'AGR-2024-002',
   'Honey & Tomato Supply Pilot',
   'Pilot 90-day supply agreement for raw honey and heirloom tomatoes with weekly delivery schedule.',
   '2024-04-01', '2024-06-30', 'active')
on conflict (agreement_code) do nothing;

-- ----------------------------------------------------------------------------
-- 6. FRAUD_LOGS
-- ----------------------------------------------------------------------------
insert into public.fraud_logs (user_id, order_id, risk_score, fraud_type, status, transaction_data, risk_factors)
values
  ('a0000000-0000-0000-0000-000000000003',
   (select id from public.orders where order_number = 'ORD-2024-002'),
   0.820, 'unusual_location',
   'pending',
   '{"ip":"192.168.1.50","country":"NG","device":"unknown"}'::jsonb,
   '["shipping_country_mismatch","new_device","high_value_order"]'::jsonb),
  ('a0000000-0000-0000-0000-000000000006',
   (select id from public.orders where order_number = 'ORD-2024-003'),
   0.340, 'velocity_check',
   'dismissed',
   '{"ip":"73.221.45.10","country":"US","device":"known"}'::jsonb,
   '["first_order"]'::jsonb)
on conflict do nothing;

-- ----------------------------------------------------------------------------
-- 7. FAVORITES
-- ----------------------------------------------------------------------------
insert into public.favorites (user_id, product_id)
select u.id, p.id
from (values
  ('a0000000-0000-0000-0000-000000000003', 'AGR-001'),
  ('a0000000-0000-0000-0000-000000000003', 'AGR-003'),
  ('a0000000-0000-0000-0000-000000000006', 'AGR-005'),
  ('a0000000-0000-0000-0000-000000000006', 'AGR-006')
) as fav(user_uuid, sku)
join public.profiles u on u.id::text = fav.user_uuid
join public.products  p on p.sku = fav.sku
where not exists (
  select 1 from public.favorites f where f.user_id = u.id and f.product_id = p.id
);

-- ----------------------------------------------------------------------------
-- 8. CART_ITEMS
-- ----------------------------------------------------------------------------
insert into public.cart_items (user_id, product_id, quantity)
select u.id, p.id, c.qty
from (values
  ('a0000000-0000-0000-0000-000000000003', 'AGR-002', 2),
  ('a0000000-0000-0000-0000-000000000006', 'AGR-004', 3)
) as c(user_uuid, sku, qty)
join public.profiles u on u.id::text = c.user_uuid
join public.products  p on p.sku = c.sku
where not exists (
  select 1 from public.cart_items ci where ci.user_id = u.id and ci.product_id = p.id
);

-- ----------------------------------------------------------------------------
-- 9. AI_PREDICTIONS
-- ----------------------------------------------------------------------------
insert into public.ai_predictions (producer_id, product_id, prediction_type, predicted_value, confidence, model_version, input_features)
select p.producer_id, p.id, pred.pred_type, pred.value, pred.conf, 'v1.2.0', pred.features::jsonb
from (values
  ('AGR-001', 'demand_forecast',    520.00, 0.89, '{"horizon":"30d","history_days":90}'),
  ('AGR-001', 'reorder_alert',      1.00,   0.95, '{"current_stock":450,"reorder_point":100}'),
  ('AGR-002', 'demand_forecast',    78.00,  0.82, '{"horizon":"30d","history_days":90}'),
  ('AGR-003', 'price_optimization', 13.50,  0.74, '{"competitor_avg":13.20,"demand_elasticity":1.1}'),
  ('AGR-005', 'spoilage_risk',      0.18,   0.91, '{"shelf_life_days":7,"current_stock":75}')
) as pred(sku, pred_type, value, conf, features)
join public.products p on p.sku = pred.sku;

-- ----------------------------------------------------------------------------
-- 10. NOTIFICATIONS
-- ----------------------------------------------------------------------------
insert into public.notifications (user_id, title, message, type, is_read, link)
select u.id, n.title, n.message, n.type::notification_type, n.is_read, n.link
from (values
  ('a0000000-0000-0000-0000-000000000001', 'Low stock alert',         'Organic Wheat stock is below reorder point.',  'warning', false, '/dashboard/inventory'),
  ('a0000000-0000-0000-0000-000000000001', 'New order received',      'You received order ORD-2024-002.',              'success', false, '/dashboard/orders'),
  ('a0000000-0000-0000-0000-000000000002', 'Order delivered',         'Order ORD-2024-001 has been delivered.',        'info',    true,  '/dashboard/orders'),
  ('a0000000-0000-0000-0000-000000000003', 'Fraud check in progress', 'Your order is under review for security.',      'warning', false, null),
  ('a0000000-0000-0000-0000-000000000004', 'New fraud alert',         'Risk score 0.82 detected on ORD-2024-002.',     'error',   false, '/dashboard/fraud')
) as n(user_uuid, title, message, type, is_read, link)
join public.profiles u on u.id::text = n.user_uuid
where not exists (
  select 1 from public.notifications no
  where no.user_id = u.id and no.title = n.title
);

select 'Seed data inserted successfully.' as result;
