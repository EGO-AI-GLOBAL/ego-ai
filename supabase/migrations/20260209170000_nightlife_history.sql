-- EGO-AI: histórico de buscas «Bares e restaurantes» (mapa / Nominatim).

create table if not exists public.nightlife_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  query text not null default '',
  city text not null default '',
  country text not null default '',
  options jsonb not null default '[]'::jsonb,
  price_tier text not null default '',
  venue_category text not null default '',
  created_at timestamptz not null default now()
);

alter table public.nightlife_history
  add column if not exists venue_category text not null default '';

alter table public.nightlife_history
  add column if not exists price_tier text not null default '';

create index if not exists nightlife_history_user_id_created_at_idx
  on public.nightlife_history (user_id, created_at desc);

alter table public.nightlife_history enable row level security;

drop policy if exists "nightlife_history_select_own" on public.nightlife_history;
create policy "nightlife_history_select_own"
  on public.nightlife_history for select
  using (auth.uid() = user_id);

drop policy if exists "nightlife_history_insert_own" on public.nightlife_history;
create policy "nightlife_history_insert_own"
  on public.nightlife_history for insert
  with check (auth.uid() = user_id);
