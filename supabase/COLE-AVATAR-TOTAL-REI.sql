-- Troca manual de avatar (teste) — reidasacolapersonalizada@uol.com.br
-- Use se o app ainda não refletir a troca; após deploy da API 1.0.9+ o picker deve funcionar.
-- Supabase SQL Editor: Ctrl+A, Ctrl+C, colar, RUN

-- Plano Total (desbloqueia Sara, Malik, Jordan, etc.)
UPDATE public.profiles
SET
  plan_tier = 'total',
  is_pro = true
WHERE lower(trim(email)) IN (
  lower(trim('reidasacolapersonalizada@uol.com.br')),
  lower(trim('sacolapersonalizada@uol.com.br'))
);

-- Exemplo: Sara (f5 + vf5) — altere avatar_id/voice_id conforme o catálogo
INSERT INTO public.user_personas (user_id, avatar_id, voice_id, updated_at)
SELECT
  p.id,
  'f5',
  'vf5',
  now()
FROM public.profiles p
WHERE lower(trim(p.email)) = lower(trim('reidasacolapersonalizada@uol.com.br'))
ON CONFLICT (user_id) DO UPDATE
SET avatar_id = EXCLUDED.avatar_id,
    voice_id = EXCLUDED.voice_id,
    updated_at = now();

UPDATE public.profiles
SET ui_state = COALESCE(ui_state, '{}'::jsonb)
  || jsonb_build_object(
    'avatar_id', 'f5',
    'voice_id', 'vf5',
    'persona_chosen_at', to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')
  )
WHERE lower(trim(email)) = lower(trim('reidasacolapersonalizada@uol.com.br'));

SELECT p.email, p.plan_tier, up.avatar_id, up.voice_id
FROM public.profiles p
LEFT JOIN public.user_personas up ON up.user_id = p.id
WHERE lower(trim(p.email)) = lower(trim('reidasacolapersonalizada@uol.com.br'));
