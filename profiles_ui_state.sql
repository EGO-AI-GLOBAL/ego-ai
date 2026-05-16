-- Supabase SQL Editor: estado da UI + contexto PDF persistido por utilizador.
-- Executar uma vez por projeto. A app faz UPDATE em profiles.ui_state (jsonb).
--
-- RLS: o utilizador autenticado precisa de poder SELECT/UPDATE na sua linha de
-- public.profiles (a coluna ui_state não exige política separada).
-- Migração equivalente: supabase/migrations/20260511120000_profiles_ui_state.sql

alter table public.profiles
  add column if not exists ui_state jsonb not null default '{}'::jsonb;

comment on column public.profiles.ui_state is
  'EGO-AI: JSON com ego_nav, pdf_context (pode truncar), gemini_model_preference, user_name — ver app.py (UI_STATE_VERSION).';
