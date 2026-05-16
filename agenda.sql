-- EGO-AI: agenda recorrente. Cole no Supabase → SQL Editor (uma vez por projeto).
-- Conteúdo espelha supabase/migrations/20260515180000_agenda_recurring.sql

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

create policy "agenda_select_own"
  on public.agenda for select
  using (auth.uid() = user_id);

create policy "agenda_insert_own"
  on public.agenda for insert
  with check (auth.uid() = user_id);

create policy "agenda_update_own"
  on public.agenda for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "agenda_delete_own"
  on public.agenda for delete
  using (auth.uid() = user_id);
