-- EGO-AI: último login (app.py touch_last_login).
-- Idempotente: seguro reexecutar no `supabase db push` ou SQL Editor.

alter table public.profiles
  add column if not exists last_login_at timestamptz;

comment on column public.profiles.last_login_at is
  'EGO-AI: atualizado em login bem-sucedido (ver app.py touch_last_login).';
