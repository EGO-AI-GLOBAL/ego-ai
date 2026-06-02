# Monitoramento de erros — EGO-AI

**Guia completo (comece aqui):** [`SETUP-MONITORAMENTO-PASSO-A-PASSO.md`](SETUP-MONITORAMENTO-PASSO-A-PASSO.md)

Você recebe aviso quando algo quebra; os erros ficam guardados para corrigir (manual ou com o assistente no Cursor).

## Camadas (o que avisa)

| Camada | O que captura | Como avisa |
|--------|----------------|------------|
| **Sentry** (app + API) | Crash, exceção, erro 500 | E-mail / app Sentry |
| **Supabase `error_reports`** | Cópia de cada erro | Tabela no painel |
| **Webhook** (opcional) | Mesmo erro | **Discord ou Slack** no celular |
| **UptimeRobot** | API fora do ar | E-mail |
| **Google Play Vitals** | Crash Android (build Play) | Play Console |

**Correção automática pelo Cursor:** não existe sozinha — quando chegar alerta, abra o chat, cole o link do Sentry ou o erro, e peça o fix. Opcional: [Cursor Automations](https://cursor.com/automations) para rodar checagens periódicas.

---

## Passo 1 — Sentry (15 min)

1. Crie conta em [sentry.io](https://sentry.io) (plano Developer grátis).
2. Crie **dois projetos**:
   - `ego-ai-mobile` (React Native)
   - `ego-ai-api` (Python / Flask)
3. Copie os **DSN** de cada um.

### Railway (API)

```env
SENTRY_DSN=https://....@....ingest.sentry.io/....
SENTRY_ENVIRONMENT=production
```

Redeploy do serviço API.

### App (EAS / build)

Em `app/.env` ou secrets do EAS:

```env
EXPO_PUBLIC_SENTRY_DSN=https://....@....ingest.sentry.io/....
```

No app:

```bash
cd app
npm install
eas build --platform android --profile production
```

### Alertas no Sentry

Em cada projeto → **Alerts** → New Alert → “Issues” → Notify by **e-mail** (e Slack se quiser).

---

## Passo 2 — Webhook Discord/Slack (alerta instantâneo)

1. Discord: canal → Integrações → Webhook → copiar URL.  
2. Railway:

```env
ERROR_ALERT_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Cada erro grave do app ou API manda mensagem no canal.

---

## Passo 3 — Supabase

Rode no SQL Editor:

`supabase/migrations/20260604120000_error_reports.sql`

Ver erros: Table Editor → `error_reports` (ordenar por `created_at` desc).

---

## Passo 4 — API no ar (UptimeRobot)

1. [uptimerobot.com](https://uptimerobot.com) → monitor HTTP.  
2. URL: `https://ego-ai-production-a2c2.up.railway.app/api/v1/health`  
3. Intervalo 5 min → alerta e-mail se cair.

---

## Passo 5 — Google Play (testadores)

Play Console → **Qualidade** → **Android vitals** → crashes e ANRs do `.aab`.

---

## O que já está no código

- App: `ErrorBoundary`, Sentry (se DSN), envio para `POST /api/v1/report-error`
- API: Sentry Flask, grava `error_reports`, webhook opcional
- Erros de API **5xx** no app também são reportados

Teste health:

```text
GET /api/v1/health
```

Campo `monitoring.sentry: true` = Sentry ativo no servidor.

---

## Quando der erro — o que fazer

1. Olhe **Discord/e-mail Sentry** ou tabela `error_reports`.  
2. Abra o Cursor neste projeto e envie:  
   *“Corrigir erro: [cole mensagem ou link Sentry]”*  
3. Depois do fix: novo deploy Railway + novo `.aab` se mudou o app.

---

## Fase testadores (congelar código?)

- Use **teste interno** com build fixo (`1.0.2`).  
- Só **correções críticas** até estabilizar.  
- Não pare de monitorar — congelar features ≠ parar alertas.

---

## Variáveis (.env resumo)

| Variável | Onde |
|----------|------|
| `SENTRY_DSN` | Railway (API) |
| `EXPO_PUBLIC_SENTRY_DSN` | app / EAS |
| `ERROR_ALERT_WEBHOOK_URL` | Railway (opcional) |
| `SUPABASE_SERVICE_ROLE_KEY` | Railway (gravar `error_reports`) |
