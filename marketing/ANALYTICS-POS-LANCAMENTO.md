# EGO-AI — Quem baixou e quem usa (ativar **depois** do lançamento)

**Status:** preparado, **não é prioridade agora** (teste interno + Play + site UOL).

Objetivo: nas **duas plataformas** (Google Play + App Store), saber **instalações**, **contas criadas** e **uso real** sem depender de planilha manual.

---

## O que já existe hoje (sem código novo)

| Métrica | Onde ver | Limitação |
|--------|----------|-----------|
| **Downloads / instalações (totais)** | Play Console → Estatísticas; App Store Connect → Analytics | Não lista e-mail de cada pessoa |
| **Conta criada (e-mail)** | Supabase → Authentication → Users; tabela `profiles` | Só quem **completou cadastro** no app |
| **Último acesso** | `profiles.last_login_at` (atualizado no login) | Quem abriu app autenticado |
| **Uso real (chat)** | `chat_history` com `role = 'user'` nos últimos 7 dias | Melhor indicador de “está testando” |
| **Erros / crashes** | Sentry + Discord + `error_reports` | Não é funil de uso |

**Importante:** a Play **não** informa quem fez login no app — só convites ao teste e instalações agregadas.

---

## No dia do lançamento público (checklist ~30 min)

### 1. Lojas (downloads agregados)

- **Android:** Play Console → **Estatísticas** (instalações, desinstalações, países).
- **iPhone:** App Store Connect → **App Analytics** (unidades, retenção).

Anote semanalmente numa linha (planilha ou Notion): data | Play installs | iOS units.

### 2. Supabase (quem é utilizador)

No **SQL Editor**, executar (ou usar `scripts/usage_report.py`):

```sql
-- Contas
SELECT COUNT(*) AS contas_auth FROM auth.users;
SELECT COUNT(*) AS perfis FROM public.profiles;

-- Ativos últimos 7 dias (login)
SELECT COUNT(*) AS login_7d
FROM public.profiles
WHERE last_login_at > NOW() - INTERVAL '7 days';

-- A usar o chat (melhor “uso real”)
SELECT COUNT(DISTINCT user_id) AS chat_7d
FROM public.chat_history
WHERE role = 'user'
  AND created_at > NOW() - INTERVAL '7 days';

-- Lista útil (e-mail + último login + plano)
SELECT email, created_at, last_login_at, plan_tier
FROM public.profiles
ORDER BY last_login_at DESC NULLS LAST;
```

### 3. Relatório local (opcional)

Com `SUPABASE_SERVICE_ROLE_KEY` no `.env`:

```bash
python scripts/usage_report.py
python scripts/usage_report.py --days 30
```

---

## Melhoria opcional pós-lançamento (1 build + 1 migration)

Quando quiser **plataforma** (android/ios) e **versão do app** por utilizador:

1. Executar migration: `supabase/migrations/20260610120000_profiles_usage_tracking.sql`
2. No app: enviar `platform` + `app_version` no `POST /api/v1/app/bootstrap` (ver `o-que-precisa-fazer/POS-LANCAMENTO-ANALYTICS-CODIGO.md`)
3. API grava `last_platform`, `last_app_version`, `first_app_open_at` em `profiles`

Até lá, **login + chat** já respondem “quem usa”.

---

## O que **não** fazer agora

- Firebase / Mixpanel / GA4 completos (custo + GDPR + tempo)
- Dashboard custom no site
- Contar testadores Play como “utilizadores do produto” (lista ≠ uso)

---

## Resumo para você

| Pergunta | Resposta hoje | Depois do lançamento |
|----------|---------------|---------------------|
| Quantos baixaram? | Play + App Store (totais) | Mesmo + export mensal |
| Quem se registou? | Supabase `profiles` / Auth | SQL ou `usage_report.py` |
| Quem está usando? | `last_login_at` + `chat_history` 7d | + plataforma/versão se ativar migration |

**Ficheiros deste pacote**

- Este guia: `marketing/ANALYTICS-POS-LANCAMENTO.md`
- Script: `scripts/usage_report.py`
- Migration (só no lançamento): `supabase/migrations/20260610120000_profiles_usage_tracking.sql`
- Implementação app/API (futuro): `o-que-precisa-fazer/POS-LANCAMENTO-ANALYTICS-CODIGO.md`
