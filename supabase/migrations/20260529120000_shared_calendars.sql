-- Agendas compartilhadas: vários utilizadores por calendário (convite por e-mail).

create table if not exists public.shared_calendars (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now()
);

create index if not exists shared_calendars_owner_idx
  on public.shared_calendars (owner_user_id);

create table if not exists public.shared_calendar_members (
  id uuid primary key default gen_random_uuid(),
  calendar_id uuid not null references public.shared_calendars (id) on delete cascade,
  user_id uuid references auth.users (id) on delete cascade,
  invited_email text not null,
  role text not null default 'member'
    check (role in ('owner', 'member')),
  status text not null default 'active'
    check (status in ('active', 'pending')),
  created_at timestamptz not null default now(),
  unique (calendar_id, invited_email)
);

create index if not exists shared_calendar_members_user_idx
  on public.shared_calendar_members (user_id)
  where user_id is not null;

create index if not exists shared_calendar_members_calendar_idx
  on public.shared_calendar_members (calendar_id);

create table if not exists public.shared_calendar_events (
  id uuid primary key default gen_random_uuid(),
  calendar_id uuid not null references public.shared_calendars (id) on delete cascade,
  created_by_user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  scheduled_at timestamptz not null,
  announce text,
  dismissed boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists shared_calendar_events_calendar_sched_idx
  on public.shared_calendar_events (calendar_id, scheduled_at);

-- Membro ativo do calendário (para RLS).
create or replace function public.is_shared_calendar_member(p_calendar_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.shared_calendar_members m
    where m.calendar_id = p_calendar_id
      and m.user_id = auth.uid()
      and m.status = 'active'
  );
$$;

create or replace function public.is_shared_calendar_owner(p_calendar_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.shared_calendars c
    where c.id = p_calendar_id
      and c.owner_user_id = auth.uid()
  );
$$;

alter table public.shared_calendars enable row level security;
alter table public.shared_calendar_members enable row level security;
alter table public.shared_calendar_events enable row level security;

-- shared_calendars
drop policy if exists "shared_calendars_select_member" on public.shared_calendars;
create policy "shared_calendars_select_member"
  on public.shared_calendars for select
  using (
    owner_user_id = auth.uid()
    or public.is_shared_calendar_member(id)
  );

drop policy if exists "shared_calendars_insert_owner" on public.shared_calendars;
create policy "shared_calendars_insert_owner"
  on public.shared_calendars for insert
  with check (owner_user_id = auth.uid());

drop policy if exists "shared_calendars_update_owner" on public.shared_calendars;
create policy "shared_calendars_update_owner"
  on public.shared_calendars for update
  using (owner_user_id = auth.uid())
  with check (owner_user_id = auth.uid());

drop policy if exists "shared_calendars_delete_owner" on public.shared_calendars;
create policy "shared_calendars_delete_owner"
  on public.shared_calendars for delete
  using (owner_user_id = auth.uid());

-- shared_calendar_members
drop policy if exists "shared_members_select" on public.shared_calendar_members;
create policy "shared_members_select"
  on public.shared_calendar_members for select
  using (public.is_shared_calendar_member(calendar_id));

drop policy if exists "shared_members_insert_owner" on public.shared_calendar_members;
create policy "shared_members_insert_owner"
  on public.shared_calendar_members for insert
  with check (public.is_shared_calendar_owner(calendar_id));

drop policy if exists "shared_members_delete_owner_or_self" on public.shared_calendar_members;
create policy "shared_members_delete_owner_or_self"
  on public.shared_calendar_members for delete
  using (
    public.is_shared_calendar_owner(calendar_id)
    or user_id = auth.uid()
  );

-- shared_calendar_events
drop policy if exists "shared_events_select" on public.shared_calendar_events;
create policy "shared_events_select"
  on public.shared_calendar_events for select
  using (public.is_shared_calendar_member(calendar_id));

drop policy if exists "shared_events_insert_member" on public.shared_calendar_events;
create policy "shared_events_insert_member"
  on public.shared_calendar_events for insert
  with check (
    public.is_shared_calendar_member(calendar_id)
    and created_by_user_id = auth.uid()
  );

drop policy if exists "shared_events_update_member" on public.shared_calendar_events;
create policy "shared_events_update_member"
  on public.shared_calendar_events for update
  using (public.is_shared_calendar_member(calendar_id))
  with check (public.is_shared_calendar_member(calendar_id));

drop policy if exists "shared_events_delete_member" on public.shared_calendar_events;
create policy "shared_events_delete_member"
  on public.shared_calendar_events for delete
  using (public.is_shared_calendar_member(calendar_id));
