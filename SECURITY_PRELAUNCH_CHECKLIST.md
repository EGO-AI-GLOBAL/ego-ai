# EGO-AI Security Pre-Launch Checklist

Guia prático para lançar com segurança no menor custo possível.

## 1) Hardening de código (obrigatório)

- [ ] Backend com CORS restrito por ambiente (`EGO_CORS_ORIGINS`).
- [ ] Rate limit ativo nas rotas críticas de auth/chat/tts.
- [ ] Sem detalhes sensíveis em erros de autenticação/webhook.
- [ ] App de produção bloqueando `EXPO_PUBLIC_API_URL` sem `https://`.

Arquivos:
- `flask_api.py`
- `ego_api/config.py`
- `app/src/api/client.ts`
- `app/app.config.ts`
- `stripe_webhook.py`

## 2) Segredos e rotação (obrigatório)

Rotacionar antes de produção:
- [ ] `GOOGLE_API_KEY`
- [ ] `SUPABASE_KEY` (publishable)
- [ ] `SUPABASE_SERVICE_ROLE_KEY`
- [ ] `STRIPE_SECRET_KEY`
- [ ] `STRIPE_WEBHOOK_SECRET`

Regras:
- [ ] Nunca commitar `.env`, `.streamlit/secrets.toml`, credenciais.
- [ ] Só usar placeholders em `.env.example`.
- [ ] Segredos apenas em variáveis de ambiente do servidor.
- [ ] App mobile só com variáveis públicas `EXPO_PUBLIC_*`.

## 3) Infra mínima segura (baixo custo)

- [ ] API em domínio HTTPS (ex.: `api.seudominio.com`).
- [ ] Proxy/CDN (Cloudflare) com TLS Full/Strict.
- [ ] Redirecionar HTTP -> HTTPS.
- [ ] `EGO_API_ENV=production`
- [ ] `EGO_ENFORCE_HTTPS=1`
- [ ] `EGO_API_DEBUG=0`
- [ ] `EGO_HEALTH_DETAILS=0`

## 4) Stripe webhook seguro

- [ ] Webhook usa assinatura Stripe (`STRIPE_WEBHOOK_SECRET`).
- [ ] Webhook usa **apenas** `SUPABASE_SERVICE_ROLE_KEY`.
- [ ] Endpoint só retorna erros genéricos.
- [ ] Teste com `stripe trigger checkout.session.completed`.

## 5) Banco e RLS (Supabase)

- [ ] RLS habilitado em `profiles`, `chat_history`, `user_personas`, `agenda`, `reminders`, `message_feedback`.
- [ ] Policies de `select/insert/update/delete` por `auth.uid()`.
- [ ] Toda rota autenticada filtra por `g.user_id`.

Consulta rápida:
- `supabase/security_rls_audit.sql`

## 6) Checklist final de release

- [ ] Build mobile aponta para API HTTPS (sem IP LAN/ngrok).
- [ ] Login, chat texto, chat voz, tts, troca de avatar funcionando.
- [ ] Limites de plano e 402 validados.
- [ ] Logs sem tokens/chaves.
- [ ] Alertas de custo Gemini configurados.
- [ ] Backup básico do banco habilitado.

## 7) Resposta a incidente (playbook curto)

1. Pausar tráfego (Cloudflare / scale to zero) se necessário.
2. Rotacionar chave comprometida.
3. Revogar sessões ativas (logout global/Supabase).
4. Reativar serviço com chave nova.
5. Registrar incidente e ação corretiva.

---

## 8) App mobile e anti-abuso (Play Store / hackers)

Protege contra APK clonado, bots a gastar a sua API OpenAI/Gemini e contas falsas.

### Obrigatório antes de produção pública

- [ ] **Play Integrity API** (Android): app envia token → backend valida com Google antes de chat/voz/realtime.  
  Guia: [PLAY_INTEGRITY_SETUP.md](./PLAY_INTEGRITY_SETUP.md) — código já no repo; falta configurar Google Cloud + `EGO_PLAY_INTEGRITY=1`.
- [ ] **Formulário Segurança de dados** (Play Console): microfone, e-mail, histórico de chat, pagamentos.
- [ ] Remover **`EGO_TEST_TOTAL_EMAILS`** e qualquer bypass de plano em produção.
- [ ] Build release com **`EXPO_PUBLIC_ALLOW_HTTP=0`** e API só **HTTPS**.
- [ ] Tokens no celular: confirmar **SecureStore** (já usado no nativo; web usa storage mais fraco).

### Recomendado (camada extra)

- [ ] **App Attest / DeviceCheck** (iOS) — equivalente Apple ao Play Integrity.
- [ ] **Cloudflare** (ou similar) na API: rate limit global, bloqueio de IPs, WAF básico.
- [ ] **Restrição de chaves** no Google Cloud / OpenAI: limite de custo + referrer/IP se possível.
- [ ] **Certificate pinning** no app (opcional v1; mais complexo de manter).
- [ ] Deteção de **root/jailbreak** só se quiser bloquear (pode afastar utilizadores legítimos).
- [ ] Alertas de **custo OpenAI/Gemini** (e-mail quando passar X €/dia).

### Play Integrity — o que implementar (resumo técnico)

1. Play Console → **Integridade do app** → ativar API.
2. No app (dev build / produção): pedir token com `react-native-google-play-integrity` ou `@google-cloud/play-integrity` no cliente nativo.
3. No Flask: novo middleware `POST /api/v1/auth/integrity` ou header `X-Play-Integrity` validado no servidor.
4. Rotas caras (`/chat/*`, `/voice/realtime/*`) recusam pedido se o token falhar ou for de app reempacotado.

Documentação Google: [Play Integrity API](https://developer.android.com/google/play/integrity)

### iOS (quando publicar na App Store)

- [ ] **App Store Connect** → privacidade + microfone.
- [ ] **App Attest** para validar app legítimo (paridade com Play Integrity).

---

## 9) Avaliação rápida — “está seguro hoje?”

| Área | Estado hoje | Notas |
|------|-------------|--------|
| Chaves OpenAI/Gemini/Stripe | **Bom** | Ficam no servidor; o app não leva `sk-`. |
| Login / sessão | **Bom** | JWT Supabase; rotas protegidas com `@require_auth`. |
| Rate limit | **Razoável** | Existe no Flask; em memória (ok no início; escalar depois). |
| HTTPS / CORS | **Dev ≠ Prod** | Em dev: HTTP + IP local é normal. **Em produção** ative `EGO_ENFORCE_HTTPS=1` e CORS fechado. |
| Banco (RLS) | **Verificar** | Script existe; tem de correr `security_rls_audit.sql` no Supabase. |
| App clonado / hacker na API | **Fraco** | Sem Play Integrity ainda — quem extrair o APK pode chamar a API com token roubado. |
| Chamada ao vivo (custo) | **Risco médio** | Autenticado + limite de plano; abuso ainda possível dentro das quotas. |
| Expo Go / dev | **Não é produção** | Expo Go e IP LAN não são alvo de lançamento. |

**Resposta curta:** para **testes e primeiros utilizadores fechados**, a base está **aceitável** (auth, chaves no servidor, rate limit). Para **Play Store aberta** e medo de hacker a esvaziar OpenAI/Stripe, falta fechar **HTTPS + RLS confirmado + Play Integrity + remover bypasses de teste**. Não é “inseguro de dia zero”, mas **não está blindado contra app clonado** até a secção 8 estar feita.

