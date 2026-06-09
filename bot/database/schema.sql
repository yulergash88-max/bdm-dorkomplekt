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
