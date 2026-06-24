# Execução Simples de Blindagem (Antes do Lançamento)

Sequência recomendada para subir em produção com baixo custo e menor risco.

## Passo 1 — Preparar segredos

1. Rotacione no provedor correspondente:
   - `GOOGLE_API_KEY`
   - `SUPABASE_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
2. Atualize as variáveis apenas no ambiente do servidor (não no app).

## Passo 2 — Configurar API de produção

Defina estas variáveis no backend:

```env
EGO_API_ENV=production
EGO_API_DEBUG=0
EGO_ENFORCE_HTTPS=1
EGO_HEALTH_DETAILS=0
EGO_CORS_ORIGINS=https://app.seudominio.com
```

Opcional (mais de um front):

```env
EGO_CORS_ORIGINS=https://app.seudominio.com,https://www.seudominio.com
```

## Passo 3 — Configurar app mobile para produção

No build de release:

```env
EXPO_PUBLIC_API_URL=https://api.seudominio.com
EXPO_PUBLIC_ALLOW_HTTP=0
```

## Passo 4 — Validar webhook Stripe

No serviço do webhook:

```env
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
```

Teste:

```bash
stripe trigger checkout.session.completed
```

## Passo 5 — Auditar segurança mínima

1. Executar:

```bash
python scripts/security_prelaunch_audit.py
```

2. Executar no Supabase SQL Editor:
   - `supabase/security_rls_audit.sql`

3. Validar fluxo real:
   - Login
   - Chat texto
   - Chat voz
   - TTS
   - Troca de avatar
   - Checkout/webhook

## Passo 6 — Go/No-Go

Lançar somente se:
- auditoria local OK;
- RLS/policies OK;
- API e app em HTTPS;
- segredos rotacionados.

## Passo 7 — Segurança mobile (antes do público geral)

Seguir secção **8** de [SECURITY_PRELAUNCH_CHECKLIST.md](./SECURITY_PRELAUNCH_CHECKLIST.md):

1. Play Integrity API no Android (validar no backend).
2. Formulário Segurança de dados na Play Console.
3. Remover `EGO_TEST_TOTAL_EMAILS` em produção.
4. Cloudflare + alertas de custo OpenAI/Gemini.

