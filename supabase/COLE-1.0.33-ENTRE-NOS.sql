-- EGO-AI 1.0.33 — Entre Nós (cole no Supabase SQL Editor)
-- Seguro re-executar (IF NOT EXISTS)

-- 1) Convites manuais: confirmar / recusar
alter table public.shared_calendar_events
  add column if not exists invite_status text not null default 'none'
    check (invite_status in ('none', 'pending', 'confirmed', 'declined'));

alter table public.shared_calendar_events
  add column if not exists responded_by_user_id uuid references auth.users (id) on delete set null;

alter table public.shared_calendar_events
  add column if not exists responded_at timestamptz;

create index if not exists shared_calendar_events_invite_pending_idx
  on public.shared_calendar_events (calendar_id, invite_status)
  where invite_status = 'pending' and dismissed = false;

-- 2) Delegação / rascunhos (1.0.32 — ignore se já aplicou)
create table if not exists public.delegation_requests (
  id uuid primary key default gen_random_uuid(),
  from_user_id uuid not null references auth.users (id) on delete cascade,
  to_user_id uuid not null references auth.users (id) on delete cascade,
  title text not null default '',
  scheduled_at timestamptz,
  task_description text,
  assignee_label text,
  assistant_name text,
  requester_name text,
  draft_id uuid,
  calendar_id uuid references public.shared_calendars (id) on delete set null,
  status text not null default 'pending'
    check (status in ('pending', 'confirmed', 'dismissed')),
  created_at timestamptz not null default now()
);

create index if not exists delegation_requests_to_pending_idx
  on public.delegation_requests (to_user_id, status)
  where status = 'pending';
