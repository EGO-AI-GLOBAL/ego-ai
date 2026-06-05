-- Plano TOTAL para reidasacolapersonalizada@uol.com.br
-- Supabase SQL Editor: Ctrl+A aqui, Ctrl+C, colar, RUN

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS plan_tier text NOT NULL DEFAULT 'essential';
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS daily_tts_count integer NOT NULL DEFAULT 0;
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS daily_usage_date text NOT NULL DEFAULT '';

UPDATE public.profiles
SET
  plan_tier = 'total',
  is_pro = true,
  monthly_tokens_used = 0,
  monthly_tokens_period = to_char(now() AT TIME ZONE 'utc', 'YYYY-MM'),
  daily_tts_count = 0,
  daily_usage_date = to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD'),
  ui_state = COALESCE(ui_state, '{}'::jsonb)
    || jsonb_build_object(
      'persona_chosen_at',
      to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')
    )
WHERE lower(trim(email)) = lower(trim('reidasacolapersonalizada@uol.com.br'));

SELECT id, email, plan_tier, is_pro, monthly_tokens_used
FROM public.profiles
WHERE lower(trim(email)) = lower(trim('reidasacolapersonalizada@uol.com.br'));
