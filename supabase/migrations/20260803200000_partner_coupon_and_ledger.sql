-- Parceiros B2B genéricos (academia, clínica, consultório, empresa…)
-- Alias partner_coupon_code ↔ gym_code · ledger do split Connect 30/70
-- Colar no SQL Editor Supabase EGO (idempotente).

-- 1) Código de rastreio no perfil (plaquinha / QR)
alter table public.profiles
  add column if not exists partner_coupon_code text;

-- Backfill a partir de gym_code
update public.profiles
set partner_coupon_code = upper(trim(gym_code))
where gym_code is not null
  and gym_code <> ''
  and (partner_coupon_code is null or partner_coupon_code = '');

create index if not exists profiles_partner_coupon_code_idx
  on public.profiles (partner_coupon_code)
  where partner_coupon_code is not null;

comment on column public.profiles.gym_code is
  'Legado: mesmo valor que partner_coupon_code (parceiro B2B).';
comment on column public.profiles.partner_coupon_code is
  'Código único do parceiro (ex. GYM_MURIAE_01). QR/plaquinha → Stripe Connect 30%% parceiro / 70%% EGO. Sem código = IAP orgânico.';

-- 2) Alias stripe_account_id (opcional — espelho de stripe_connect_account_id)
alter table public.gym_partners
  add column if not exists stripe_account_id text;

update public.gym_partners
set stripe_account_id = stripe_connect_account_id
where stripe_connect_account_id is not null
  and stripe_connect_account_id <> ''
  and (stripe_account_id is null or stripe_account_id = '');

comment on table public.gym_partners is
  'Parceiros B2B (academia, clínica, médico, empresa…). Connect destination: 30%% parceiro / 70%% EGO.';
comment on column public.gym_partners.stripe_connect_account_id is
  'Conta Connect acct_… do parceiro (canónico).';
comment on column public.gym_partners.stripe_account_id is
  'Alias de stripe_connect_account_id.';

-- 3) Ledger de auditoria (NÃO cria Transfer — o Stripe Connect já faz o split na assinatura)
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

comment on table public.partner_revenue_ledger is
  'Auditoria do split 30/70. O pagamento real ao parceiro é automático via Stripe Connect (application_fee_percent + transfer_data).';
