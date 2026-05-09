-- EGO-AI: histórico de buscas "Comida Perto" e "Bebidas Perto" + RLS.
-- Rode no SQL Editor do Supabase ou via CLI (`supabase db push`).

-- ---------------------------------------------------------------------------
-- food_history
-- ---------------------------------------------------------------------------
create table if not exists public.food_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  query text not null default '',
  city text not null default '',
  country text not null default '',
  options jsonb not null default '[]'::jsonb,
  price_tier text not null default '',
  created_at timestamptz not null default now()
);

alter table public.food_history
  add column if not exists price_tier text not null default '';

create index if not exists food_history_user_id_created_at_idx
  on public.food_history (user_id, created_at desc);

alter table public.food_history enable row level security;

drop policy if exists "food_history_select_own" on public.food_history;
create policy "food_history_select_own"
  on public.food_history for select
  using (auth.uid() = user_id);

drop policy if exists "food_history_insert_own" on public.food_history;
create policy "food_history_insert_own"
  on public.food_history for insert
  with check (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- drink_history (mesma ideia: opções JSON + faixa de preço + tipo de bebida)
-- ---------------------------------------------------------------------------
create table if not exists public.drink_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  query text not null default '',
  city text not null default '',
  country text not null default '',
  options jsonb not null default '[]'::jsonb,
  price_tier text not null default '',
  drink_category text not null default '',
  created_at timestamptz not null default now()
);

alter table public.drink_history
  add column if not exists price_tier text not null default '';

alter table public.drink_history
  add column if not exists drink_category text not null default '';

create index if not exists drink_history_user_id_created_at_idx
  on public.drink_history (user_id, created_at desc);

alter table public.drink_history enable row level security;

drop policy if exists "drink_history_select_own" on public.drink_history;
create policy "drink_history_select_own"
  on public.drink_history for select
  using (auth.uid() = user_id);

drop policy if exists "drink_history_insert_own" on public.drink_history;
create policy "drink_history_insert_own"
  on public.drink_history for insert
  with check (auth.uid() = user_id);
