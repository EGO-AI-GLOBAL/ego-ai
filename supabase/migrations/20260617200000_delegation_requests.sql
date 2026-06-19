-- Piloto automático família: pedidos de delegação entre membros da agenda compartilhada
create table if not exists public.delegation_requests (
  id uuid primary key default gen_random_uuid(),
  from_user_id uuid not null references auth.users (id) on delete cascade,
  to_user_id uuid not null references auth.users (id) on delete cascade,
  draft_id uuid references public.agenda_drafts (id) on delete set null,
  calendar_id uuid references public.shared_calendars (id) on delete set null,
  title text not null,
  scheduled_at timestamptz,
  task_description text,
  assignee_label text,
  assistant_name text not null default 'Luna',
  requester_name text,
  status text not null default 'pending',
  created_at timestamptz not null default now(),
  confirmed_at timestamptz
);

create index if not exists delegation_requests_to_status_idx
  on public.delegation_requests (to_user_id, status, created_at desc);

create index if not exists delegation_requests_from_idx
  on public.delegation_requests (from_user_id, created_at desc);

alter table public.delegation_requests enable row level security;

drop policy if exists "delegation_select_parties" on public.delegation_requests;
create policy "delegation_select_parties"
  on public.delegation_requests for select
  using (auth.uid() = from_user_id or auth.uid() = to_user_id);

drop policy if exists "delegation_insert_own" on public.delegation_requests;
create policy "delegation_insert_own"
  on public.delegation_requests for insert
  with check (auth.uid() = from_user_id);

drop policy if exists "delegation_update_target" on public.delegation_requests;
create policy "delegation_update_target"
  on public.delegation_requests for update
  using (auth.uid() = to_user_id)
  with check (auth.uid() = to_user_id);
