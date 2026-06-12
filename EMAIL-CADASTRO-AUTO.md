# E-mail automático após cadastro (contato@egoai.com.br)

## O que faz

1. **Na hora do cadastro** — envia e-mail de boas-vindas com link da Play (teste interno).
2. **24 h depois** — se a pessoa nunca fez login, envia lembrete (cron na API).

Remetente: **contato@egoai.com.br** (SMTP UOL).

## Configurar no Railway

Variáveis no serviço da API:

| Variável | Valor |
|----------|--------|
| `EGO_SIGNUP_EMAIL_ENABLED` | `1` |
| `EGO_SMTP_HOST` | `smtp.uol.com.br` |
| `EGO_SMTP_PORT` | `587` |
| `EGO_SMTP_USE_TLS` | `1` |
| `EGO_SMTP_USER` | `contato@egoai.com.br` |
| `EGO_SMTP_PASSWORD` | senha do e-mail no painel UOL |
| `EGO_SMTP_FROM` | `contato@egoai.com.br` |
| `EGO_SMTP_FROM_NAME` | `Ego-IA` |
| `EGO_PLAY_STORE_URL` | link do teste interno Play |

Se a UOL pedir SSL na porta 465:

- `EGO_SMTP_PORT=465`
- `EGO_SMTP_USE_SSL=1`
- `EGO_SMTP_USE_TLS=0`

## Supabase (uma vez)

No **SQL Editor**, rode:

`supabase/migrations/20260612120000_profiles_signup_email_tracking.sql`

## Lembrete 24 h (cron)

Chame 1–2× por dia (cron externo ou manual):

```http
POST https://ego-ai-production-a2c2.up.railway.app/api/v1/admin/cron/signup-reminders
X-Admin-Key: SUA_REFERRAL_ADMIN_SECRET
```

Resposta exemplo: `{"stats":{"candidates":2,"sent":1,"failed":0,"skipped":0}}`

## Teste rápido (sem criar conta)

Depois do deploy, no PowerShell (troque e-mail e chave admin):

```powershell
$headers = @{
  "X-Admin-Key" = "SUA_REFERRAL_ADMIN_SECRET"
  "Content-Type" = "application/json"
}
$body = '{"email":"seu@gmail.com","full_name":"Iury"}'
Invoke-RestMethod -Method POST `
  -Uri "https://ego-ai-production-a2c2.up.railway.app/api/v1/admin/test-signup-email" `
  -Headers $headers -Body $body
```

Resposta OK: `ok : True` — verifique a caixa de entrada (e spam).

## Teste com cadastro real

1. Crie conta no app com e-mail real.
2. Verifique caixa de entrada em ~1 minuto.
3. No Supabase: `welcome_email_sent_at` preenchido no perfil.
