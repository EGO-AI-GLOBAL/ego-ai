-- EGO-AI: coluna JSON para estado da UI + pdf_context (autosave em app.py).
-- Idempotente: seguro reexecutar no `supabase db push` ou SQL Editor.

alter table public.profiles
  add column if not exists ui_state jsonb not null default '{}'::jsonb;

comment on column public.profiles.ui_state is
  'EGO-AI: JSON com ego_nav, pdf_context (pode truncar), gemini_model_preference, user_name — ver app.py (UI_STATE_VERSION).';
