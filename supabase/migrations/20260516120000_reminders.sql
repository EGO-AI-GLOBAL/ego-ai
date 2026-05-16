-- EGO-AI: lembretes pontuais (alarmes). Liga cada linha a auth.users via user_id.

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
  on public.reminders for select
  using (auth.uid() = user_id);

drop policy if exists "reminders_insert_own" on public.reminders;
create policy "reminders_insert_own"
  on public.reminders for insert
  with check (auth.uid() = user_id);

drop policy if exists "reminders_update_own" on public.reminders;
create policy "reminders_update_own"
  on public.reminders for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "reminders_delete_own" on public.reminders;
create policy "reminders_delete_own"
  on public.reminders for delete
  using (auth.uid() = user_id);

alter table public.reminders add column if not exists google_event_id text;

create unique index if not exists reminders_user_gcal_evt_idx
  on public.reminders (user_id, google_event_id)
  where google_event_id is not null and length(trim(google_event_id)) > 0;
