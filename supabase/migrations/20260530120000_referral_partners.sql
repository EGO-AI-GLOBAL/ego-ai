-- Programa de indicação (influenciadores): código no cadastro, comissão no 1º pagamento.

create table if not exists public.referral_partners (
  id uuid primary key default gen_random_uuid(),
  code text not null,
  display_name text not null default '',
  contact_email text,
  payout_pix text,
  notes text,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  constraint referral_partners_code_unique unique (code)
);

create index if not exists referral_partners_code_lower_idx
  on public.referral_partners (lower(code));

alter table public.profiles
  add column if not exists referred_by_partner_id uuid references public.referral_partners (id) on delete set null,
  add column if not exists referral_first_paid_at timestamptz;

create table if not exists public.referral_commissions (
  id uuid primary key default gen_random_uuid(),
  partner_id uuid not null references public.referral_partners (id) on delete cascade,
  referred_user_id uuid not null references auth.users (id) on delete cascade,
  stripe_session_id text,
  amount_cents integer not null default 1000,
  currency text not null default 'brl',
  status text not null default 'pending',
  payout_month text not null default '',
  created_at timestamptz not null default now(),
  paid_out_at timestamptz,
  constraint referral_commissions_user_unique unique (referred_user_id)
);

create index if not exists referral_commissions_partner_month_idx
  on public.referral_commissions (partner_id, payout_month);

alter table public.referral_partners enable row level security;
alter table public.referral_commissions enable row level security;

-- Sem políticas para clientes: leitura/escrita só via service role (API/webhook).

comment on table public.referral_partners is 'Influenciadores com código de indicação (ex.: MARIA10).';
comment on table public.referral_commissions is 'R$ 10 no primeiro pagamento de cada indicado (status pending/paid).';
