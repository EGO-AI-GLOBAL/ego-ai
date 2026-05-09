-- Supabase → SQL Editor. Tokens Google Calendar + estado CSRF do OAuth.

create table if not exists public.google_calendar_tokens (
  user_id uuid primary key references auth.users (id) on delete cascade,
  refresh_token text not null,
  updated_at timestamptz not null default now()
);

alter table public.google_calendar_tokens enable row level security;

create policy "gcal_tokens_select_own"
  on public.google_calendar_tokens for select
  using (auth.uid() = user_id);

create policy "gcal_tokens_insert_own"
  on public.google_calendar_tokens for insert
  with check (auth.uid() = user_id);

create policy "gcal_tokens_update_own"
  on public.google_calendar_tokens for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "gcal_tokens_delete_own"
  on public.google_calendar_tokens for delete
  using (auth.uid() = user_id);

-- Estado temporário do OAuth (CSRF); uma linha por tentativa de login.

create table if not exists public.google_oauth_pending (
  state text primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  created_at timestamptz not null default now()
);

create index if not exists google_oauth_pending_user_idx
  on public.google_oauth_pending (user_id);

alter table public.google_oauth_pending enable row level security;

create policy "g_oauth_pending_select_own"
  on public.google_oauth_pending for select
  using (auth.uid() = user_id);

create policy "g_oauth_pending_insert_own"
  on public.google_oauth_pending for insert
  with check (auth.uid() = user_id);

create policy "g_oauth_pending_delete_own"
  on public.google_oauth_pending for delete
  using (auth.uid() = user_id);
