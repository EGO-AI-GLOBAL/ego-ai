-- COLE NO SUPABASE EGO (SQL Editor) — complemento parceiro genérico
-- Corre DEPOIS de COLE-GYM-PARTNERS-SHAPESCAN-MIRROR.sql
-- Idempotente. Parceiro = academia, clínica, consultório, empresa…

alter table public.profiles
  add column if not exists partner_coupon_code text;

update public.profiles
set partner_coupon_code = upper(trim(gym_code))
where gym_code is not null
  and gym_code <> ''
  and (partner_coupon_code is null or partner_coupon_code = '');

create index if not exists profiles_partner_coupon_code_idx
  on public.profiles (partner_coupon_code)
  where partner_coupon_code is not null;

comment on column public.profiles.partner_coupon_code is
  'Código único do parceiro (ex. GYM_MURIAE_01). QR/plaquinha → Stripe Connect 30% parceiro / 70% EGO.';

alter table public.gym_partners
  add column if not exists stripe_account_id text;

update public.gym_partners
set stripe_account_id = stripe_connect_account_id
where stripe_connect_account_id is not null
  and stripe_connect_account_id <> ''
  and (stripe_account_id is null or stripe_account_id = '');

create table if not exists public.partner_revenue_ledger (
  id uuid primary key default gen_random_uuid(),
  partner_code text not null,
  stripe_account_id text,
  stripe_invoice_id text,
  stripe_event_id text,
  amount_total_cents integer not null default 0,
  partner_share_cents integer not null default 0,
  platform_share_cents integer not null default 0,
  commission_pct integer not null default 30,
  note text not null default 'connect_destination_auto_split',
  created_at timestamptz not null default now()
);

create unique index if not exists partner_revenue_ledger_invoice_uidx
  on public.partner_revenue_ledger (stripe_invoice_id)
  where stripe_invoice_id is not null;

create index if not exists partner_revenue_ledger_code_idx
  on public.partner_revenue_ledger (partner_code, created_at desc);

alter table public.partner_revenue_ledger enable row level security;
