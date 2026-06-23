-- Plano Total para conta de teste (Supabase → SQL Editor → Run)
-- Email: reidasacolapersonalizada@uol.com.br

-- Se der erro "column plan_tier does not exist", execute isto primeiro:
alter table public.profiles
  add column if not exists plan_tier text not null default 'essential';
alter table public.profiles
  add column if not exists daily_tts_count integer not null default 0;
alter table public.profiles
  add column if not exists daily_usage_date text not null default '';

UPDATE public.profiles
SET
  plan_tier = 'total',
  is_pro = true,
  monthly_tokens_used = 0,
  monthly_tokens_period = to_char(now() AT TIME ZONE 'utc', 'YYYY-MM'),
  daily_tts_count = 0,
  daily_usage_date = to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD'),
  ui_state = COALESCE(ui_state, '{}'::jsonb) - 'daily_messages'
WHERE lower(email) = lower('reidasacolapersonalizada@uol.com.br');

-- Conferir:
SELECT id, email, plan_tier, is_pro
FROM public.profiles
WHERE lower(email) = lower('reidasacolapersonalizada@uol.com.br');
