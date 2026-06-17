# EGO-AI — E-mail automático após cadastro (contato@egoai.com.br)

## O que faz (100% automático — você não precisa fazer nada)

1. **Na hora do cadastro** — a API envia sozinha o e-mail de boas-vindas (thread em background).
2. **Se o SMTP falhar** — até 3 tentativas; depois o job interno reenvia em até 4 h.
3. **24 h depois** — se a pessoa nunca fez login, envia lembrete (cron **dentro** da API, sem cron externo).

Remetente: **contato@egoai.com.br** (SMTP UOL).

**Você só configurou uma vez** as variáveis no Railway. Depois disso, cada novo cadastro no app dispara o e-mail sem você clicar em nada.

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

**Se der `timed out` no Railway** (comum na 465), volte para **587 + TLS**:

- `EGO_SMTP_PORT=587`
- `EGO_SMTP_USE_TLS=1`
- `EGO_SMTP_USE_SSL=0`
- apague ou defina `EGO_SMTP_USE_SSL=0`

Opcional: `EGO_SMTP_TIMEOUT=90` (segundos; padrão 60).

## Supabase (uma vez)

No **SQL Editor**, rode:

`supabase/migrations/20260612120000_profiles_signup_email_tracking.sql`

## Lembrete 24 h

**Automático** — a API roda um job interno a cada 4 h (não precisa cron externo).

Opcional (manual): `POST /api/v1/admin/cron/signup-reminders` com `X-Admin-Key`.

## Teste rápido (sem criar conta)

**Não use** os textos `SUA_REFERRAL_ADMIN_SECRET` ou `VALOR_DO_REFERRAL_ADMIN_SECRET_NO_RAILWAY` — são só exemplos.

1. Railway → serviço **API** → **Variables**
2. Variável **`REFERRAL_ADMIN_SECRET`** (ou **`EGO_ADMIN_API_KEY`**) → ícone **olho** → **copiar valor**
3. Duplo clique: **`TESTAR-EMAIL-CADASTRO.bat`** → cole a chave quando pedir

Ou PowerShell manual (troque `COLE_A_CHAVE_REAL` pelo valor copiado do Railway):

```powershell
$headers = @{
  "X-Admin-Key" = "COLE_A_CHAVE_REAL"
  "Content-Type" = "application/json"
}
$body = '{"email":"seu@gmail.com","full_name":"Iury"}'
Invoke-RestMethod -Method POST `
  -Uri "https://ego-ai-production-a2c2.up.railway.app/api/v1/admin/test-signup-email" `
  -Headers $headers -Body $body
```

Se a variável **não existir** no Railway, crie `REFERRAL_ADMIN_SECRET` com uma senha longa → salve → aguarde redeploy.

Resposta OK: `ok : True` — verifique a caixa de entrada (e spam).

## Confirmar que está automático em produção

Abra no browser:

`https://ego-ai-production-a2c2.up.railway.app/api/v1/health`

Deve aparecer:

```json
"signup_emails": {
  "enabled": true,
  "smtp_configured": true,
  "automatic_on_signup": true,
  "background_jobs": true
}
```

Se `smtp_configured` for `false`, cadastros **não** recebem e-mail — corrija `EGO_SMTP_PASSWORD` no Railway.

## Teste com cadastro real

1. Crie conta no app com e-mail real.
2. Verifique caixa de entrada em ~1 minuto.
3. No Supabase: `welcome_email_sent_at` preenchido no perfil.
