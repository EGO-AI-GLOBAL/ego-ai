# E-mail de cadastro — `timed out` no Railway

## Por que falha

A **chave admin está OK** (`EgoIndica2026Maria`). O erro `timed out` significa:

**O Railway não consegue ligar ao `smtp.uol.com.br`** (porta 587 ou 465).

Isso é comum em servidores na nuvem. **Não é senha errada** — é bloqueio/lentidão de rede até a UOL.

---

## Solução A — Brevo SMTP (só Railway, sem código novo)

Funciona com o código **já em produção**.

1. Crie conta grátis: https://www.brevo.com
2. **Transactional** → **SMTP & API** → **SMTP**
3. Copie:
   - Servidor: `smtp-relay.brevo.com`
   - Porta: `587`
   - Login: seu e-mail Brevo
   - Chave SMTP: (senha longa gerada lá)
4. **Senders** → adicione `contato@egoai.com.br` (confirme por e-mail)

### Railway → Variables

| Variável | Valor |
|----------|--------|
| `EGO_SMTP_HOST` | `smtp-relay.brevo.com` |
| `EGO_SMTP_PORT` | `587` |
| `EGO_SMTP_USE_TLS` | `1` |
| `EGO_SMTP_USE_SSL` | `0` |
| `EGO_SMTP_USER` | e-mail da conta Brevo |
| `EGO_SMTP_PASSWORD` | chave SMTP do Brevo |
| `EGO_SMTP_FROM` | `contato@egoai.com.br` |
| `EGO_SMTP_FROM_NAME` | `Ego-IA` |

Salve → redeploy → teste com `TESTAR-EMAIL-CADASTRO.bat`

Use **seu Gmail real** — não `SEU-GMAIL@gmail.com`.

---

## Solução B — Resend HTTPS (após push do código)

Melhor a longo prazo (porta 443, não bloqueia).

1. https://resend.com → API Key
2. Railway:

| Variável | Valor |
|----------|--------|
| `EGO_EMAIL_PROVIDER` | `resend` |
| `RESEND_API_KEY` | `re_...` |
| `EGO_RESEND_FROM` | `Ego-IA <contato@egoai.com.br>` |

3. Resend → **Domains** → `egoai.com.br` → registros DNS na UOL

Teste rápido (antes do DNS): `EGO_RESEND_FROM=Ego-IA <onboarding@resend.dev>`  
(só envia para o e-mail da conta Resend)

---

## Testar

```powershell
$headers = @{ "X-Admin-Key" = "SUA_CHAVE"; "Content-Type" = "application/json" }
$body = '{"email":"seu@gmail.com","full_name":"Iury"}'
Invoke-RestMethod -Method POST `
  -Uri "https://ego-ai-production-a2c2.up.railway.app/api/v1/admin/test-signup-email" `
  -Headers $headers -Body $body
```

Esperado: `{ "ok": true, "provider": "smtp" }` ou `"resend"`
