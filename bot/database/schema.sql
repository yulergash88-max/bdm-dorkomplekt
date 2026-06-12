-- Supabase/PostgreSQL schema for the delivery confirmation & accounting bot
-- Run this in the Supabase SQL editor.

create table if not exists users (
    telegram_id bigint primary key,
    full_name text not null,
    phone text,
    role text not null check (role in ('supplier', 'buyer', 'admin')),
    is_approved boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists deliveries (
    id bigserial primary key,
    supplier_id bigint not null references users (telegram_id),
    buyer_id bigint references users (telegram_id),
    product_name text not null,

    -- Declared by supplier when the delivery is created
    supplier_kub numeric(12, 3) not null,

    -- Filled in by the buyer after weighing on the scale
    buyer_tonnage numeric(12, 3),

    -- Conversion factor taken from the laboratory conclusion (tonnage -> kub).
    -- NOTE: exact formula/coefficient meaning to be confirmed by the customer.
    lab_coefficient numeric(12, 6),

    -- Calculated: buyer_kub = buyer_tonnage * lab_coefficient (placeholder formula)
    buyer_kub numeric(12, 3),

    -- Calculated: buyer_kub - supplier_kub
    kub_difference numeric(12, 3),

    status text not null default 'new' check (
        status in ('new', 'sent_to_buyer', 'accepted', 'weighed', 'completed', 'rejected')
    ),

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_deliveries_supplier on deliveries (supplier_id);
create index if not exists idx_deliveries_buyer on deliveries (buyer_id);
create index if not exists idx_deliveries_status on deliveries (status);

-- Migration: admin can block a user without deleting their row (deliveries FK forbids deletion).
alter table users add column if not exists is_blocked boolean not null default false;

-- Migration: buyer-side companies — group buyer accounts by firm and mark the company manager.
-- company_name is also matched against "Мижоз: ..." in external sales-feed messages.
alter table users add column if not exists company_name text;
alter table users add column if not exists is_buyer_admin boolean not null default false;

-- Migration: admin-added users without a known Telegram ID — held here until the person
-- starts the bot and shares a matching phone number, at which point they're claimed into `users`.
create table if not exists pending_invites (
    id bigserial primary key,
    phone text not null,
    normalized_phone text not null,
    full_name text not null,
    role text not null check (role in ('supplier', 'buyer')),
    company_name text,
    created_at timestamptz not null default now()
);
create index if not exists idx_pending_invites_normalized_phone on pending_invites (normalized_phone);

-- Migration: financial figures parsed from the sales-feed "Тип: Савдо" message.
--   price  — "Цена"  (price per m³)
--   amount — "Сумма" (value of goods sold — drives the running balance)
--   paid   — "Туланди" (paid at point of sale; informational only)
alter table deliveries add column if not exists price numeric(14, 2);
alter table deliveries add column if not exists amount numeric(14, 2);
alter table deliveries add column if not exists paid numeric(14, 2);

-- Buyer balance ledger.
-- balance = initial_balance + Σ(deliveries.amount) − Σ(payments.amount)
--   initial_balance — starting debt entered by the admin when adding/editing a buyer
--   deliveries.amount — goods sold ("Тип: Савдо" → "Сумма"), increases debt
--   payments.amount   — money received ("Тип: Тўлов" → "Пул олинди"), decreases debt
alter table users add column if not exists initial_balance numeric(14, 2) not null default 0;
alter table pending_invites add column if not exists initial_balance numeric(14, 2) not null default 0;

create table if not exists payments (
    id bigserial primary key,
    buyer_id bigint references users (telegram_id),
    client_name text,
    amount numeric(14, 2) not null,
    sale_datetime text,
    created_at timestamptz not null default now()
);
create index if not exists idx_payments_buyer on payments (buyer_id);

-- Buyer sites ("объект"). A buyer company has objects; each receiver employee is
-- tied to one object. The group message carries no object, so a delivery is
-- broadcast to all company employees and tagged with the accepter's object_name.
create table if not exists objects (
    id bigserial primary key,
    company_name text not null,
    name text not null,
    created_at timestamptz not null default now()
);
create index if not exists idx_objects_company on objects (company_name);

alter table users add column if not exists object_name text;            -- employee's site
alter table pending_invites add column if not exists object_name text;
alter table deliveries add column if not exists object_name text;       -- site it was received at
