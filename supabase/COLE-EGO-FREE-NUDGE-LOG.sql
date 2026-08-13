-- Colar no SQL Editor do Supabase (EGO-AI)
-- Log da campanha WhatsApp: lembrete contas grátis até 30/09/2026

create table if not exists public.ego_free_nudge_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  phone text not null,
  kind text not null check (kind in ('reminder', 'planos_reply')),
  ok boolean not null default true,
  error text,
  provider text,
  sent_at timestamptz not null default now()
);

create index if not exists ego_free_nudge_log_phone_day
  on public.ego_free_nudge_log (phone, kind, sent_at desc);

alter table public.ego_free_nudge_log enable row level security;

-- Sem policies para anon/authenticated: só service_role (API Railway) escreve/lê.
