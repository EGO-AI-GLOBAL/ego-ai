-- EGO-AI: histórico de buscas «Compras online» (produtos em marketplaces / Google Shopping).

create table if not exists public.shopping_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  query text not null default '',
  options jsonb not null default '[]'::jsonb,
  price_tier text not null default '',
  shop_category text not null default '',
  market_region text not null default '',
  created_at timestamptz not null default now()
);

alter table public.shopping_history
  add column if not exists price_tier text not null default '';

alter table public.shopping_history
  add column if not exists shop_category text not null default '';

alter table public.shopping_history
  add column if not exists market_region text not null default '';

create index if not exists shopping_history_user_id_created_at_idx
  on public.shopping_history (user_id, created_at desc);

alter table public.shopping_history enable row level security;

drop policy if exists "shopping_history_select_own" on public.shopping_history;
create policy "shopping_history_select_own"
  on public.shopping_history for select
  using (auth.uid() = user_id);

drop policy if exists "shopping_history_insert_own" on public.shopping_history;
create policy "shopping_history_insert_own"
  on public.shopping_history for insert
  with check (auth.uid() = user_id);
