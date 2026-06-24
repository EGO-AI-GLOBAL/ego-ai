# EGO-AI — Playbook de incidente de segurança

Use quando suspeitar de abuso, custo anormal ou chave comprometida.

## 1. Contenção imediata (5 min)

1. **Railway** → Variables:
   - `EGO_MAINTENANCE=1` (pausa funcionalidades; `/health` mostra `maintenance: true`)
   - Ou escale tráfego a zero se necessário
2. **Google Cloud / OpenAI** → desactivar ou rotacionar `GOOGLE_API_KEY` / `OPENAI_API_KEY`
3. **Stripe** → modo teste ou revogar chave se webhook comprometido

## 2. Rotacionar segredos (15 min)

| Segredo | Onde |
|---------|------|
| `GOOGLE_API_KEY` | Google AI Studio |
| `OPENAI_API_KEY` | OpenAI dashboard |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API |
| `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` | Stripe → Developers |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google Cloud IAM (Play Integrity) |

Actualizar **só** no Railway (nunca no app). Redeploy.

## 3. Revogar sessões abusivas

- Supabase → Authentication → Users → banir contas suspeitas
- Ou SQL: invalidar refresh tokens do utilizador abusivo (suporte Supabase)

## 4. Investigar

```powershell
cd "raiz do projeto"
python scripts/list_recent_errors.py
python scripts/usage_report.py
```

Railway logs: procurar `play_integrity fail`, picos 402/429, IPs repetidos.

## 5. Reativar

1. Remover `EGO_MAINTENANCE`
2. `python scripts/regression_guard.py`
3. `python scripts/smoke_test_api.py`
4. Testar login → chat → voz com conta real paga

## Alertas contínuos (configurar uma vez)

| Canal | Variável Railway | O quê |
|-------|------------------|-------|
| Sentry | `SENTRY_DSN` | Erros 500, excepções |
| Discord/Slack | `ERROR_ALERT_WEBHOOK_URL` | Erros críticos API |
| Google Cloud | Billing → Budget alert | Custo Gemini |
| OpenAI | Usage limits | Custo Realtime |
| Railway | Metrics → Notifications | CPU/memória/tráfego |

## Play Integrity — escalação

1. `EGO_PLAY_INTEGRITY=1` + `EGO_PLAY_INTEGRITY_MODE=monitor` (só regista)
2. Após APK Play + JSON Google configurados: `EGO_PLAY_INTEGRITY_MODE=enforce`

Ver [PLAY_INTEGRITY_SETUP.md](./PLAY_INTEGRITY_SETUP.md).
