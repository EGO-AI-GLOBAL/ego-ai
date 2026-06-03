# Setup monitoramento — passo a passo (Sentry + Railway + Discord)

Siga na ordem. Tempo total: ~30–40 min (uma vez só).

---

## Parte A — Sentry (conta e 2 projetos)

### A1. Criar conta

1. No **PC**, abra: https://sentry.io/signup/
2. Cadastre com e-mail ou Google.
3. Plano **Developer** (grátis) — suficiente para começar.

### A2. Projeto da API (Flask / Railway)

1. **Create project**
2. Plataforma: **Python**
3. Nome sugerido: `ego-ai-api`
4. **Create project**
5. Copie o **DSN** (parece com):
   ```text
   https://xxxxxxxx@o000000.ingest.us.sentry.io/0000000
   ```
6. Guarde num bloco de notas como `SENTRY_DSN_API`.

### A3. Projeto do app (React Native / Expo)

1. Menu **Projects** → **Create project**
2. Plataforma: **React Native**
3. Nome sugerido: `ego-ai-mobile`
4. **Create project**
5. Copie o **DSN** → guarde como `SENTRY_DSN_APP`.

### A4. Alertas por e-mail (Sentry)

**Em cada projeto** (`ego-ai-api` e `ego-ai-mobile`):

1. **Settings** (engrenagem do projeto) → **Alerts**
2. **Create Alert** → template **Issues**
3. Condição: “A new issue is created” (ou similar)
4. Ação: **Send a notification to** → seu e-mail
5. Salvar.

Opcional: instale o app **Sentry** no celular (iOS/Android) e faça login — vê crashes no telefone.

---

## Parte B — Railway (variáveis da API)

### B1. Abrir o serviço certo

1. https://railway.app → login
2. Projeto **EGO-AI** (ou o nome que você usa)
3. Clique no serviço da **API** (não o Streamlit), o que usa `Dockerfile` e `flask_api`.

### B2. Colar variáveis

1. Aba **Variables**
2. **Add variable** (ou Raw Editor) e cole:

```env
SENTRY_DSN=COLE_AQUI_O_DSN_DO_PROJETO_ego-ai-api
SENTRY_ENVIRONMENT=production
```

3. Confirme que já existem (não apague):
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (anon)
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `GOOGLE_API_KEY`
   - `STRIPE_WEBHOOK_SECRET` (se usar Stripe)

4. Railway faz **redeploy** sozinho — espere ficar **Active** (verde).

### B3. Testar API

No navegador do PC ou celular:

```text
https://ego-ai-production-a2c2.up.railway.app/api/v1/health
```

Procure no JSON:

```json
"monitoring": {
  "sentry": true,
  "sentry_dsn_set": true,
  ...
}
```

Se `sentry: false`, o DSN não entrou ou o deploy ainda não terminou.

---

## Parte C — Discord no celular (alertas instantâneos)

### C1. Criar canal e webhook (no celular ou PC)

1. Abra o **Discord** → seu servidor (ou crie um servidor só “EGO-AI”).
2. Crie canal `#ego-alertas` (ou use um existente).
3. Toque no nome do canal → **Editar canal** → **Integrações** → **Webhooks**
4. **Novo webhook** → nome: `EGO-AI Erros`
5. **Copiar URL do webhook** (começa com `https://discord.com/api/webhooks/...`)

### C2. Colar no Railway

No mesmo serviço API → **Variables**:

```env
ERROR_ALERT_WEBHOOK_URL=https://discord.com/api/webhooks/SEU_ID/SEU_TOKEN
```

Salve → aguarde redeploy.

### C3. Testar webhook (PC)

No PowerShell (troque a URL):

```powershell
$body = @{ content = "Teste EGO-AI — se apareceu aqui, alertas OK." } | ConvertTo-Json
Invoke-RestMethod -Uri "SUA_URL_DO_WEBHOOK" -Method Post -Body $body -ContentType "application/json"
```

Deve aparecer a mensagem no canal `#ego-alertas` no celular.

---

## Parte D — Supabase (guardar erros)

1. https://supabase.com → seu projeto EGO-AI
2. **SQL Editor** → **New query**
3. Abra no PC o arquivo:
   `supabase/migrations/20260604120000_error_reports.sql`
4. Copie **todo** o conteúdo → cole no SQL Editor → **Run**
5. **Table Editor** → deve existir tabela `error_reports`

(Rode também as migrations antigas se ainda não rodou: `stripe_revenue_ledger`, `referral_partners`.)

---

## Parte E — App mobile (Sentry no build)

### E1. Instalar dependência

No PC, pasta do app:

```powershell
cd "C:\Users\Iury\OneDrive\Área de Trabalho\EGO-AI-APP - Copia\app"
npm install
```

### E2. Variável no EAS (produção / testadores)

Com EAS CLI logado:

```powershell
eas secret:create --name EXPO_PUBLIC_SENTRY_DSN --value "COLE_DSN_DO_ego-ai-mobile" --scope project
```

Ou no site: https://expo.dev → seu projeto **ego-ai** → **Secrets**.

### E3. Novo build para testadores

```powershell
eas build --platform android --profile production
```

(ou o perfil que você usa na Play teste interno)

Sem novo build, o app antigo **não** envia erros ao Sentry.

---

## Parte F — UptimeRobot (API caiu)

1. https://uptimerobot.com → conta grátis
2. **Add monitor**
   - Tipo: **HTTP(s)**
   - URL: `https://ego-ai-production-a2c2.up.railway.app/api/v1/health`
   - Nome: `EGO-AI API`
   - Intervalo: **5 minutes**
3. **Alert contacts** → seu e-mail (e app UptimeRobot no celular se quiser)

---

## Parte G — Fluxo do dia a dia

```text
[Testador usa app] 
    → erro? 
        → Discord avisa no celular
        → Sentry guarda detalhes
        → Supabase error_reports (cópia)

[Quando for corrigir]
    → Abra Cursor no PC
    → "Corrigir: [cole mensagem Discord ou link Sentry]"
    → Deploy Railway (API) e/ou novo .aab (app)
```

### No celular você vê

- Discord: mensagem curta
- Sentry app: stack trace
- Play Console: crashes Android (depois do build na Play)

### No PC você corrige

- Cursor + este repositório
- Railway redeploy (automático ao push, se conectado ao GitHub)

---

## Parte H — Testar tudo (checklist)

| # | Teste | OK? |
|---|--------|-----|
| 1 | `/api/v1/health` → `monitoring.sentry: true` | ☐ |
| 2 | Mensagem teste no Discord (webhook) | ☐ |
| 3 | SQL `error_reports` existe no Supabase | ☐ |
| 4 | UptimeRobot monitor criado | ☐ |
| 5 | `EXPO_PUBLIC_SENTRY_DSN` no EAS | ☐ |
| 6 | Novo `.aab` enviado à Play (teste interno) | ☐ |

### Teste de erro na API (opcional)

Depois do Sentry da API ativo, force um erro só em ambiente de teste — ou espere o primeiro erro real. O Sentry deve mostrar o issue em **ego-ai-api**.

### Ver últimos erros no PC

```powershell
cd "C:\Users\Iury\OneDrive\Área de Trabalho\EGO-AI-APP - Copia"
# .env com SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY
python scripts/list_recent_errors.py
```

---

## Variáveis — cola rápida (Railway API)

Modelo: `railway-monitoring.env.example` na raiz do projeto.

```env
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
ERROR_ALERT_WEBHOOK_URL=
```

## Variáveis — cola rápida (EAS / app)

```env
EXPO_PUBLIC_SENTRY_DSN=
```

---

## Problemas comuns

| Problema | Solução |
|----------|---------|
| `sentry: false` no health | DSN errado ou deploy não terminou |
| Discord não recebe | URL webhook incompleta; teste com Invoke-RestMethod |
| App não aparece no Sentry | Falta novo build com `EXPO_PUBLIC_SENTRY_DSN` |
| `error_reports` vazio | Migration SQL não rodou ou falta `SUPABASE_SERVICE_ROLE_KEY` |

---

## Quando precisar de mim (Cursor)

Mande neste chat:

1. Print ou texto do Discord, **ou**
2. Link do issue no Sentry, **ou**
3. Saída de `python scripts/list_recent_errors.py`

Exemplo: *“Corrigir erro do testador: [colar mensagem]”*
