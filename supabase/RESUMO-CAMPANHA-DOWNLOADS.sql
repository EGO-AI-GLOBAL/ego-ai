-- ============================================================
-- EGO-AI — QUANTOS BAIXARAM / USAM (Supabase SQL Editor → RUN)
-- Cole TUDO e execute. Rode de novo a qualquer dia.
--
-- IMPORTANTE:
--   • Instalações REAIS (APK/IPA baixado): Play Console + TestFlight
--   • Supabase = quem CRIOU CONTA e quem FEZ LOGIN (melhor proxy)
-- ============================================================

-- ── A) NÚMEROS DE HOJE (painel rápido) ───────────────────────
SELECT
  (SELECT count(*) FROM auth.users) AS contas_auth_total,
  (SELECT count(*) FROM public.profiles) AS perfis_total,
  (SELECT count(*) FROM public.profiles WHERE last_login_at IS NOT NULL) AS ja_logaram_alguma_vez,
  (SELECT count(*) FROM public.profiles
   WHERE created_at >= date_trunc('day', now())) AS cadastros_hoje,
  (SELECT count(*) FROM public.profiles
   WHERE last_login_at >= date_trunc('day', now())) AS login_hoje,
  (SELECT count(*) FROM public.profiles
   WHERE created_at >= now() - interval '5 days') AS cadastros_ultimos_5_dias,
  (SELECT count(*) FROM public.profiles
   WHERE last_login_at >= now() - interval '5 days') AS login_ultimos_5_dias,
  (SELECT count(*) FROM public.profiles
   WHERE created_at >= now() - interval '7 days') AS cadastros_7_dias,
  (SELECT count(DISTINCT user_id) FROM public.chat_history
   WHERE role = 'user' AND created_at >= now() - interval '7 days') AS usaram_chat_7_dias;

-- ── B) CADASTROS POR DIA (últimos 14 dias) ───────────────────
SELECT
  created_at::date AS dia,
  count(*) AS novos_cadastros,
  count(*) FILTER (WHERE last_login_at IS NOT NULL) AS destes_que_logaram
FROM public.profiles
WHERE created_at >= current_date - interval '14 days'
GROUP BY 1
ORDER BY 1 DESC;

-- ── C) ANDROID vs iOS (preenchido após API 15/07 + abrir o app) ─
-- last_platform vinha vazio: o app enviava X-EGO-Platform mas a API não gravava.
-- Depois do deploy: quem abrir o app passa a ter ios | android | web.
SELECT
  coalesce(nullif(trim(last_platform), ''), 'desconhecido') AS plataforma,
  count(*) AS usuarios
FROM public.profiles
WHERE last_login_at IS NOT NULL
  AND last_login_at >= now() - interval '14 days'
GROUP BY 1
ORDER BY usuarios DESC;

-- iOS recente (cruzar com App Store unidades)
SELECT
  email,
  created_at::timestamptz AT TIME ZONE 'America/Sao_Paulo' AS cadastro_br,
  last_login_at::timestamptz AT TIME ZONE 'America/Sao_Paulo' AS ultimo_login_br,
  last_platform,
  last_app_version,
  coalesce(plan_tier, 'essential') AS plano
FROM public.profiles
WHERE last_platform = 'ios'
   OR (created_at >= now() - interval '7 days' AND coalesce(last_platform, '') = '')
ORDER BY coalesce(last_login_at, created_at) DESC
LIMIT 40;

-- ── D) VERSÃO DO APP (quem está em 1.0.34?) ─────────────────
SELECT
  coalesce(nullif(trim(last_app_version), ''), 'desconhecido') AS versao,
  count(*) AS usuarios
FROM public.profiles
WHERE last_login_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY usuarios DESC;

-- ── E) ÚLTIMOS 30 CADASTROS (e-mail + login) ─────────────────
SELECT
  email,
  created_at::timestamptz AT TIME ZONE 'America/Sao_Paulo' AS cadastro_br,
  last_login_at::timestamptz AT TIME ZONE 'America/Sao_Paulo' AS ultimo_login_br,
  coalesce(last_platform, '—') AS plataforma,
  coalesce(last_app_version, '—') AS versao,
  coalesce(plan_tier, 'essential') AS plano
FROM public.profiles
ORDER BY created_at DESC
LIMIT 30;

-- ── F) CADASTRO SEM LOGIN (baixou e não entrou?) ─────────────
SELECT
  email,
  created_at::date AS cadastro,
  (current_date - created_at::date) AS dias_sem_login
FROM public.profiles
WHERE last_login_at IS NULL
ORDER BY created_at DESC
LIMIT 50;

-- ── G) PLANOS + STRIPE (pagantes) ────────────────────────────
SELECT
  coalesce(nullif(trim(plan_tier), ''), 'essential') AS plano,
  count(*) AS usuarios
FROM public.profiles
GROUP BY 1
ORDER BY usuarios DESC;

SELECT
  payment_date,
  plan_tier,
  valor_rs,
  stripe_id
FROM public.stripe_revenue_ledger
ORDER BY payment_date DESC
LIMIT 10;
