-- Anti-abuso free: identidades persistem após apagar conta (trial_used / soft-delete lógico).
-- Só service role (API Railway). Executar no Supabase SQL Editor se migração não correr sozinha.

create table if not exists public.ego_free_identity_guard (
  id uuid primary key default gen_random_uuid(),
  identity_kind text not null check (identity_kind in ('email', 'phone', 'oauth')),
  identity_key text not null,
  trial_used_at timestamptz not null default now(),
  last_deleted_user_id uuid,
  daily_usage_date date,
  daily_text_used int not null default 0,
  daily_voice_used int not null default 0,
  daily_tts_used int not null default 0,
  delete_count int not null default 1,
  updated_at timestamptz not null default now(),
  constraint ego_free_identity_guard_kind_key unique (identity_kind, identity_key)
);

create index if not exists ego_free_identity_guard_updated_idx
  on public.ego_free_identity_guard (updated_at desc);

alter table public.ego_free_identity_guard enable row level security;

comment on table public.ego_free_identity_guard is
  'Identidades que já consumiram o free — sobrevivem ao delete_user (anti-abuso recriar conta).';
