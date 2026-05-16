-- Supabase SQL Editor: coluna de último login em public.profiles.
-- Executar uma vez por projeto (ou usar supabase db push com a migração equivalente).
--
-- Migração equivalente: supabase/migrations/20260515120000_profiles_last_login_at.sql

alter table public.profiles
  add column if not exists last_login_at timestamptz;

comment on column public.profiles.last_login_at is
  'EGO-AI: atualizado em login bem-sucedido (ver app.py touch_last_login).';
