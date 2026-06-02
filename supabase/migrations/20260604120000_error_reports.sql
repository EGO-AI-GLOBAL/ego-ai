-- Relatórios de erro (app + API) para painel e alertas
create table if not exists public.error_reports (
  id uuid primary key default gen_random_uuid(),
  source text not null default 'app',
  level text not null default 'error',
  message text not null,
  stack text,
  route text,
  user_id uuid,
  app_version text,
  platform text,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists error_reports_created_at_idx
  on public.error_reports (created_at desc);

create index if not exists error_reports_source_idx
  on public.error_reports (source, level);

alter table public.error_reports enable row level security;

comment on table public.error_reports is
  'Erros do app/API; escrita via service role; leitura admin no Supabase.';
