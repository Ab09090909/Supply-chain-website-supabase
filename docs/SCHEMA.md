# 📋 Database Schema Reference

All 10 tables in the `public` schema, with columns and purposes.

## Enums

| Enum                | Values                                                              |
|---------------------|---------------------------------------------------------------------|
| `user_role`         | `producer`, `merchant`, `customer`, `admin`                         |
| `order_status`      | `pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled` |
| `payment_status`    | `pending`, `paid`, `failed`, `refunded`                             |
| `product_status`    | `active`, `inactive`, `draft`                                       |
| `agreement_status`  | `active`, `pending`, `expired`, `cancelled`                         |
| `fraud_status`      | `pending`, `reviewing`, `confirmed`, `dismissed`                    |
| `notification_type` | `info`, `warning`, `error`, `success`                               |

---

## 1. `profiles` — User profiles (extends `auth.users`)

| Column        | Type         | Notes                                  |
|---------------|--------------|----------------------------------------|
| id            | uuid (PK)    | FK → auth.users.id, ON DELETE CASCADE  |
| email         | text (unique)|                                        |
| full_name     | text         |                                        |
| role          | user_role    | Default `customer`                     |
| phone         | text         |                                        |
| location      | text         |                                        |
| avatar_url    | text         |                                        |
| company       | text         |                                        |
| is_active     | boolean      | Default `true`                         |
| is_verified   | boolean      | Default `false`                        |
| last_login    | timestamptz  |                                        |
| created_at    | timestamptz  | Default `now()`                        |
| updated_at    | timestamptz  | Auto-updated by trigger                |

---

## 2. `products` — Producer inventory items

| Column            | Type           | Notes                          |
|-------------------|----------------|--------------------------------|
| id                | uuid (PK)      | Auto-generated                 |
| sku               | text (unique)  |                                |
| name              | text           |                                |
| description       | text           |                                |
| category          | text           |                                |
| price             | numeric(10,2)  | ≥ 0                            |
| stock             | integer        | ≥ 0                            |
| unit              | text           | Default `'unit'`               |
| reorder_point     | integer        |                                |
| reorder_quantity  | integer        |                                |
| image_url         | text           |                                |
| producer_id       | uuid (FK)      | → profiles.id                  |
| status            | product_status | Default `'active'`             |
| metadata          | jsonb          |                                |
| created_at        | timestamptz    |                                |
| updated_at        | timestamptz    | Auto-updated                   |

---

## 3. `orders` — Purchase orders

| Column           | Type            | Notes                          |
|------------------|-----------------|--------------------------------|
| id               | uuid (PK)       |                                |
| order_number     | text (unique)   | e.g. `ORD-CUST-20240101-...`   |
| buyer_id         | uuid (FK)       | → profiles.id                  |
| buyer_role       | user_role       |                                |
| seller_id        | uuid (FK)       | → profiles.id                  |
| seller_role      | user_role       |                                |
| subtotal         | numeric(12,2)   |                                |
| tax              | numeric(12,2)   |                                |
| shipping_cost    | numeric(12,2)   |                                |
| total            | numeric(12,2)   |                                |
| status           | order_status    | Default `'pending'`            |
| payment_status   | payment_status  | Default `'pending'`            |
| shipping_address | jsonb           |                                |
| notes            | text            |                                |
| placed_at        | timestamptz     | Default `now()`                |
| confirmed_at     | timestamptz     |                                |
| shipped_at       | timestamptz     |                                |
| delivered_at     | timestamptz     |                                |
| created_at       | timestamptz     |                                |
| updated_at       | timestamptz     | Auto-updated                   |

---

## 4. `order_items` — Line items per order

| Column      | Type           | Notes                              |
|-------------|----------------|------------------------------------|
| id          | uuid (PK)      |                                    |
| order_id    | uuid (FK)      | → orders.id, ON DELETE CASCADE     |
| product_id  | uuid (FK)      | → products.id, ON DELETE SET NULL  |
| sku         | text           | Snapshot at order time             |
| name        | text           | Snapshot                           |
| unit_price  | numeric(10,2)  | Snapshot                           |
| quantity    | integer        | > 0                                |
| subtotal    | numeric(12,2)  | **Generated column** = price × qty |
| created_at  | timestamptz    |                                    |

---

## 5. `agreements` — B2B supply contracts

| Column          | Type              | Notes                       |
|-----------------|-------------------|-----------------------------|
| id              | uuid (PK)         |                             |
| producer_id     | uuid (FK)         | → profiles.id               |
| merchant_id     | uuid (FK)         | → profiles.id               |
| agreement_code  | text (unique)     |                             |
| title           | text              |                             |
| terms           | text              |                             |
| start_date      | date              |                             |
| end_date        | date              |                             |
| status          | agreement_status  | Default `'pending'`         |
| metadata        | jsonb             |                             |
| created_at      | timestamptz       |                             |
| updated_at      | timestamptz       | Auto-updated                |

---

## 6. `fraud_logs` — AI fraud-detection alerts

| Column            | Type          | Notes                                |
|-------------------|---------------|--------------------------------------|
| id                | uuid (PK)     |                                      |
| user_id           | uuid (FK)     | → profiles.id, ON DELETE SET NULL    |
| order_id          | uuid (FK)     | → orders.id, ON DELETE SET NULL      |
| risk_score        | numeric(4,3)  | 0.000 – 1.000                        |
| fraud_type        | text          |                                      |
| status            | fraud_status  | Default `'pending'`                  |
| transaction_data  | jsonb         |                                      |
| risk_factors      | jsonb         | Array of strings                     |
| reviewed_by       | uuid (FK)     | → profiles.id                        |
| reviewed_at       | timestamptz   |                                      |
| review_notes      | text          |                                      |
| created_at        | timestamptz   |                                      |

---

## 7. `favorites` — Customer wishlist

| Column     | Type      | Notes                            |
|------------|-----------|----------------------------------|
| id         | uuid (PK) |                                  |
| user_id    | uuid (FK) | → profiles.id, ON DELETE CASCADE |
| product_id | uuid (FK) | → products.id, ON DELETE CASCADE |
| created_at | timestamptz |                                |

Unique constraint: `(user_id, product_id)`

---

## 8. `cart_items` — Customer shopping cart

| Column     | Type        | Notes                            |
|------------|-------------|----------------------------------|
| id         | uuid (PK)   |                                  |
| user_id    | uuid (FK)   | → profiles.id, ON DELETE CASCADE |
| product_id | uuid (FK)   | → products.id, ON DELETE CASCADE |
| quantity   | integer     | > 0, default 1                   |
| created_at | timestamptz |                                  |
| updated_at | timestamptz | Auto-updated                     |

Unique constraint: `(user_id, product_id)`

---

## 9. `ai_predictions` — ML model outputs

| Column           | Type          | Notes                              |
|------------------|---------------|------------------------------------|
| id               | uuid (PK)     |                                    |
| producer_id      | uuid (FK)     | → profiles.id, ON DELETE SET NULL  |
| product_id       | uuid (FK)     | → products.id, ON DELETE SET NULL  |
| prediction_type  | text          | e.g. `demand_forecast`             |
| predicted_value  | numeric(12,2) |                                    |
| confidence       | numeric(4,3)  | 0.000 – 1.000                      |
| model_version    | text          |                                    |
| input_features   | jsonb         |                                    |
| created_at       | timestamptz   |                                    |

---

## 10. `notifications` — In-app notifications

| Column     | Type               | Notes                            |
|------------|--------------------|----------------------------------|
| id         | uuid (PK)          |                                  |
| user_id    | uuid (FK)          | → profiles.id, ON DELETE CASCADE |
| title      | text               |                                  |
| message    | text               |                                  |
| type       | notification_type  | Default `'info'`                 |
| is_read    | boolean            | Default `false`                  |
| link       | text               | Optional deep-link               |
| created_at | timestamptz        |                                  |

---

## Relationships Diagram (text)

```
auth.users (Supabase-managed)
    │ 1:1
    ▼
profiles ────────┬──── products ──── order_items ──── orders
    │            │         ▲                              ▲
    │            │         │                              │
    │            └──── favorites                         │
    │            └──── cart_items                        │
    │                                                  │
    ├─── agreements (producer_id) ──── profiles (merchant_id)
    ├─── fraud_logs (user_id, reviewed_by, order_id)
    ├─── ai_predictions (producer_id, product_id)
    └─── notifications (user_id)
```
