-- ============================================================
-- EGO-AI: COPIE TODO ESTE FICHEIRO no Supabase SQL Editor → Run
-- NAO cole o nome do ficheiro (ex: supabase/VERIFICAR...) — so o SQL abaixo
-- Pode executar varias vezes (idempotente)
-- ============================================================

-- --- Parte A: colunas de plano / uso ---
alter table public.profiles
  add column if not exists plan_tier text not null default 'essential';
alter table public.profiles
  add column if not exists daily_tts_count integer not null default 0;
alter table public.profiles
  add column if not exists daily_usage_date text not null default '';

-- --- Parte B: telefone + convites por telefone ---
alter table public.profiles
  add column if not exists phone text;

create unique index if not exists profiles_phone_unique_idx
  on public.profiles (phone)
  where phone is not null and phone <> '';

alter table public.shared_calendar_members
  add column if not exists invited_phone text;

create unique index if not exists shared_calendar_members_calendar_phone_uq
  on public.shared_calendar_members (calendar_id, invited_phone)
  where invited_phone is not null and invited_phone <> '';

-- --- Verificacao: deve listar 5 tabelas ---
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'profiles',
    'user_personas',
    'shared_calendars',
    'shared_calendar_members',
    'shared_calendar_events'
  )
order by table_name;
