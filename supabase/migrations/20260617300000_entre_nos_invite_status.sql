-- Entre Nós: convite manual na agenda compartilhada (parceiro confirma ou recusa).

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
