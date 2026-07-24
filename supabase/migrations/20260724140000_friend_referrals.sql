-- Indicação amigo → amigo: 1 mês grátis para quem indica (após 1º pagamento Stripe).

alter table public.profiles
  add column if not exists friend_invite_code text,
  add column if not exists referred_by_user_id uuid references auth.users (id) on delete set null,
  add column if not exists friend_referral_paid_at timestamptz,
  add column if not exists referral_bonus_until timestamptz;

create unique index if not exists profiles_friend_invite_code_unique
  on public.profiles (lower(friend_invite_code))
  where friend_invite_code is not null and friend_invite_code <> '';

create index if not exists profiles_referred_by_user_idx
  on public.profiles (referred_by_user_id)
  where referred_by_user_id is not null;

create table if not exists public.friend_referral_invites (
  id uuid primary key default gen_random_uuid(),
  referrer_user_id uuid not null references auth.users (id) on delete cascade,
  invited_email text not null,
  invited_phone text not null default '',
  status text not null default 'pending',
  referred_user_id uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default now(),
  constraint friend_referral_invites_email_norm_check check (length(trim(invited_email)) >= 5)
);

create unique index if not exists friend_referral_invites_email_pending_unique
  on public.friend_referral_invites (lower(invited_email))
  where status = 'pending';

create index if not exists friend_referral_invites_referrer_idx
  on public.friend_referral_invites (referrer_user_id, created_at desc);

alter table public.friend_referral_invites enable row level security;

comment on column public.profiles.friend_invite_code is 'Código pessoal para indicação de amigos (não parceiro).';
comment on column public.profiles.referral_bonus_until is 'Acesso Premium gratuito por indicação até esta data.';
comment on table public.friend_referral_invites is 'Convites pré-validados (e-mail/telefone ainda sem conta).';
