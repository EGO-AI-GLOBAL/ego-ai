-- EGO-AI: Supabase → SQL Editor → cole e Run.
-- Pode executar várias vezes (tabelas/policies idempotentes).

-- ========== profiles ==========
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text,
  email text,
  country text,
  document_type text,
  is_pro boolean not null default false,
  created_at timestamptz not null default now(),
  monthly_tokens_used bigint not null default 0,
  monthly_tokens_period text default '',
  ui_state jsonb not null default '{}'::jsonb,
  last_login_at timestamptz
);

alter table public.profiles enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
  on public.profiles for select using (auth.uid() = id);

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own"
  on public.profiles for insert with check (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
  on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);

-- ========== chat_history ==========
create table if not exists public.chat_history (
  id bigserial primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null default '',
  created_at timestamptz not null default now(),
  ego_msg_id uuid default gen_random_uuid()
);

create unique index if not exists chat_history_ego_msg_uidx on public.chat_history (ego_msg_id);
create index if not exists chat_history_user_created_idx on public.chat_history (user_id, created_at);

alter table public.chat_history enable row level security;

drop policy if exists "chat_history_select_own" on public.chat_history;
create policy "chat_history_select_own"
  on public.chat_history for select using (auth.uid() = user_id);

drop policy if exists "chat_history_insert_own" on public.chat_history;
create policy "chat_history_insert_own"
  on public.chat_history for insert with check (auth.uid() = user_id);

-- ========== user_personas ==========
create table if not exists public.user_personas (
  user_id uuid primary key references auth.users (id) on delete cascade,
  avatar_id text not null default 'f1',
  voice_id text not null default 'vf1',
  updated_at timestamptz not null default now()
);

alter table public.user_personas enable row level security;

drop policy if exists "personas_select_own" on public.user_personas;
create policy "personas_select_own"
  on public.user_personas for select using (auth.uid() = user_id);

drop policy if exists "personas_insert_own" on public.user_personas;
create policy "personas_insert_own"
  on public.user_personas for insert with check (auth.uid() = user_id);

drop policy if exists "personas_update_own" on public.user_personas;
create policy "personas_update_own"
  on public.user_personas for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ========== agenda (compromissos recorrentes) ==========
create table if not exists public.agenda (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  titulo text not null,
  horario time not null,
  dias_da_semana text not null,
  data_criacao timestamptz not null default now()
);

create index if not exists agenda_user_idx on public.agenda (user_id, data_criacao desc);

alter table public.agenda enable row level security;

drop policy if exists "agenda_select_own" on public.agenda;
create policy "agenda_select_own"
  on public.agenda for select using (auth.uid() = user_id);

drop policy if exists "agenda_insert_own" on public.agenda;
create policy "agenda_insert_own"
  on public.agenda for insert with check (auth.uid() = user_id);

drop policy if exists "agenda_update_own" on public.agenda;
create policy "agenda_update_own"
  on public.agenda for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "agenda_delete_own" on public.agenda;
create policy "agenda_delete_own"
  on public.agenda for delete using (auth.uid() = user_id);

-- ========== reminders (lembretes pontuais / alarmes) ==========
create table if not exists public.reminders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  scheduled_at timestamptz not null,
  announce text,
  dismissed boolean not null default false,
  snooze_until timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists reminders_user_scheduled_idx
  on public.reminders (user_id, scheduled_at desc);

alter table public.reminders enable row level security;

drop policy if exists "reminders_select_own" on public.reminders;
create policy "reminders_select_own"
  on public.reminders for select using (auth.uid() = user_id);

drop policy if exists "reminders_insert_own" on public.reminders;
create policy "reminders_insert_own"
  on public.reminders for insert with check (auth.uid() = user_id);

drop policy if exists "reminders_update_own" on public.reminders;
create policy "reminders_update_own"
  on public.reminders for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "reminders_delete_own" on public.reminders;
create policy "reminders_delete_own"
  on public.reminders for delete using (auth.uid() = user_id);

alter table public.reminders add column if not exists google_event_id text;

create unique index if not exists reminders_user_gcal_evt_idx
  on public.reminders (user_id, google_event_id)
  where google_event_id is not null and length(trim(google_event_id)) > 0;

-- Opcional: supabase/trigger_profile_on_signup.sql
