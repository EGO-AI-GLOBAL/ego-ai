-- Descarrego da noite (rascunhos) + lista de compras ligada a compromissos

create table if not exists public.agenda_drafts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  source text not null default 'night_dump',
  comfort_reply text,
  items jsonb not null default '[]'::jsonb,
  status text not null default 'pending',
  created_at timestamptz not null default now(),
  expires_at timestamptz
);

create index if not exists agenda_drafts_user_status_idx
  on public.agenda_drafts (user_id, status, created_at desc);

alter table public.agenda_drafts enable row level security;

drop policy if exists "agenda_drafts_select_own" on public.agenda_drafts;
create policy "agenda_drafts_select_own"
  on public.agenda_drafts for select using (auth.uid() = user_id);

drop policy if exists "agenda_drafts_insert_own" on public.agenda_drafts;
create policy "agenda_drafts_insert_own"
  on public.agenda_drafts for insert with check (auth.uid() = user_id);

drop policy if exists "agenda_drafts_update_own" on public.agenda_drafts;
create policy "agenda_drafts_update_own"
  on public.agenda_drafts for update using (auth.uid() = user_id);

drop policy if exists "agenda_drafts_delete_own" on public.agenda_drafts;
create policy "agenda_drafts_delete_own"
  on public.agenda_drafts for delete using (auth.uid() = user_id);

create table if not exists public.shopping_list_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  reminder_id uuid references public.reminders (id) on delete cascade,
  title text not null,
  category text not null default 'mercado',
  done boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists shopping_list_user_reminder_idx
  on public.shopping_list_items (user_id, reminder_id, done);

alter table public.shopping_list_items enable row level security;

drop policy if exists "shopping_select_own" on public.shopping_list_items;
create policy "shopping_select_own"
  on public.shopping_list_items for select using (auth.uid() = user_id);

drop policy if exists "shopping_insert_own" on public.shopping_list_items;
create policy "shopping_insert_own"
  on public.shopping_list_items for insert with check (auth.uid() = user_id);

drop policy if exists "shopping_update_own" on public.shopping_list_items;
create policy "shopping_update_own"
  on public.shopping_list_items for update using (auth.uid() = user_id);

drop policy if exists "shopping_delete_own" on public.shopping_list_items;
create policy "shopping_delete_own"
  on public.shopping_list_items for delete using (auth.uid() = user_id);
