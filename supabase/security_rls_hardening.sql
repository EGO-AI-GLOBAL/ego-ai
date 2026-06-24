-- Blindagem RLS: impede utilizador de auto-promover plano (plan_tier / is_pro).
-- Execute no SQL Editor do Supabase (pode correr várias vezes).

-- ========== message_feedback (se ainda não existir) ==========
create table if not exists public.message_feedback (
  id bigserial primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  ego_msg_id uuid,
  rating smallint,
  comment text,
  created_at timestamptz not null default now()
);

alter table public.message_feedback enable row level security;

drop policy if exists "message_feedback_select_own" on public.message_feedback;
create policy "message_feedback_select_own"
  on public.message_feedback for select using (auth.uid() = user_id);

drop policy if exists "message_feedback_insert_own" on public.message_feedback;
create policy "message_feedback_insert_own"
  on public.message_feedback for insert with check (auth.uid() = user_id);

-- ========== bloquear auto-escalação de plano no perfil ==========
create or replace function public.profiles_block_self_plan_escalation()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  -- service_role / postgres (webhook Stripe) pode alterar plano
  if coalesce(auth.role(), '') in ('service_role', 'supabase_admin') then
    return new;
  end if;
  if auth.uid() is null then
    return new;
  end if;
  if auth.uid() = old.id then
    if new.plan_tier is distinct from old.plan_tier then
      new.plan_tier := old.plan_tier;
    end if;
    if new.is_pro is distinct from old.is_pro then
      new.is_pro := old.is_pro;
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists profiles_block_self_plan_escalation on public.profiles;
create trigger profiles_block_self_plan_escalation
  before update on public.profiles
  for each row
  execute function public.profiles_block_self_plan_escalation();

-- ========== auditoria rápida (copiar resultado) ==========
select
  c.relname as table_name,
  c.relrowsecurity as rls_enabled
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in (
    'profiles',
    'chat_history',
    'user_personas',
    'agenda',
    'reminders',
    'message_feedback'
  )
order by c.relname;
