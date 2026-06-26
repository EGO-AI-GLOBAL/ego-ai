-- EGO-AI — cole no Supabase SQL Editor e RUN (1x antes do deploy API)
-- Inclui: programa parceiros + lembrete e-mail semanal

-- ========== PARCEIROS / COMISSÕES ==========
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

-- ========== E-MAILS SEMANAIS ==========
alter table public.profiles
  add column if not exists welcome_email_sent_at timestamptz,
  add column if not exists signup_reminder_sent_at timestamptz;

alter table public.profiles
  add column if not exists signup_reminder_count integer not null default 0;

update public.profiles
set signup_reminder_count = 1
where signup_reminder_sent_at is not null
  and coalesce(signup_reminder_count, 0) = 0;

drop index if exists public.profiles_signup_reminder_idx;
drop index if exists public.profiles_signup_reminder_pending_idx;

create index if not exists profiles_signup_reminder_weekly_idx
  on public.profiles (created_at desc)
  where welcome_email_sent_at is not null
    and last_login_at is null
    and coalesce(signup_reminder_count, 0) < 4;

-- Verificação rápida
select 'referral_partners' as tabela, count(*) from public.referral_partners
union all
select 'profiles com cupom', count(*) from public.profiles where referred_by_partner_id is not null;
