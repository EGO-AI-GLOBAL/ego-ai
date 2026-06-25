# Relatório diário de cadastros (e-mail)

Todo dia você recebe um e-mail com:

- **Cadastros totais** até aquele momento
- **Novos hoje** e **últimos 7 dias**
- **Logins** e quem **usou chat**
- **Tabela dos últimos 14 dias** (histórico no inbox)

---

## Passo 1 — E-mail de destino (Railway)

1. Abra [railway.app](https://railway.app) → projeto **EGO-AI**
2. Clique no serviço da **API** (Flask / `ego-ai-production`)
3. Aba **Variables**
4. **+ New Variable** e adicione:

| Nome | Valor |
|------|--------|
| `EGO_DAILY_STATS_EMAIL` | Seu e-mail (ex.: `seu@gmail.com`) |
| `EGO_DAILY_STATS_ENABLED` | `1` |

5. Salve (Railway redeploy sozinho)

---

## Passo 2 — Deploy do código (se ainda não fez push)

O endpoint `/api/v1/admin/cron/daily-stats` precisa estar no ar.  
Push para `main` ou **Redeploy** manual da API.

---

## Passo 3 — Cron no Railway (clique a clique)

O cron é um **serviço novo e pequeno** que só roda `curl` todo dia às 8h (Brasília) e desliga.

### 3.1 Criar o serviço

1. No projeto Railway, botão **+ Create** (ou **New**)
2. Escolha **Empty Service** (serviço vazio)
3. Nome sugerido: `cron-relatorio-cadastros`

### 3.2 Imagem Docker (só curl)

1. Entre no serviço `cron-relatorio-cadastros`
2. Aba **Settings**
3. Procure **Source** / **Deploy** → **Deploy from Docker Image**
4. Imagem: `curlimages/curl`
5. Salve

### 3.3 Comando que roda todo dia

Ainda em **Settings**, campo **Custom Start Command** (ou **Start Command**), cole **uma linha**:

```sh
sh -c 'curl -sS -X POST "https://ego-ai-production-a2c2.up.railway.app/api/v1/admin/cron/daily-stats" -H "X-Admin-Key: $REFERRAL_ADMIN_SECRET" -H "Content-Type: application/json" -d "{}" --fail'
```

> Usa a variável `REFERRAL_ADMIN_SECRET` que já existe no projeto — **não precisa colar a chave no texto**.

Se a variável só existir na API, copie para este serviço também:
- **Variables** do `cron-relatorio-cadastros` → **+ New Variable**
- Nome: `REFERRAL_ADMIN_SECRET`
- Valor: **o mesmo** da API (Railway → API → Variables → copiar valor)

### 3.4 Horário (todo dia 8h Brasília)

1. **Settings** do mesmo serviço
2. Campo **Cron Schedule**
3. Cole: `0 11 * * *`
4. Salve

| O que significa | Valor |
|-----------------|--------|
| Railway usa **UTC** | 11:00 UTC |
| No Brasil (UTC−3) | **8:00 da manhã** |

Outros horários (Brasília → UTC, some 3h):

| Quer receber às | Cron Schedule |
|-----------------|---------------|
| 7h | `0 10 * * *` |
| 8h | `0 11 * * *` |
| 9h | `0 12 * * *` |
| 20h | `0 23 * * *` |

### 3.5 Deploy

1. Botão **Deploy** (ou aguarde deploy automático)
2. Serviço fica parado até o horário — **isso é normal**

---

## Passo 4 — Testar manualmente (sem esperar 8h)

**Opção A — no PC:** duplo clique em `TESTAR-RELATORIO-CADASTROS.bat`

**Opção B — no Railway:**

1. Serviço `cron-relatorio-cadastros`
2. **Deployments** → **Deploy** / **Run now** (dispara o start command agora)
3. **Logs** — deve aparecer resposta JSON com `"sent": true`
4. Confira sua caixa de entrada (e spam)

---

## Resumo visual

```
[Railway projeto EGO-AI]
    │
    ├── API (Flask)          ← EGO_DAILY_STATS_EMAIL aqui
    │       └── envia o e-mail quando chamada
    │
    └── cron-relatorio-cadastros   ← NOVO
            imagem: curlimages/curl
            cron: 0 11 * * *
            comando: curl → POST /admin/cron/daily-stats
```

---

## Problemas comuns

| Sintoma | Solução |
|---------|---------|
| 401 Chave inválida | `REFERRAL_ADMIN_SECRET` no serviço cron = igual à API |
| 503 E-mail não configurado | Brevo/SMTP na API + `EGO_DAILY_STATS_EMAIL` |
| 404 Not found | API ainda sem deploy do código novo — redeploy API |
| Não chegou e-mail | Spam; ou rode `TESTAR-RELATORIO-CADASTROS.bat` e veja erro |

---

## Desligar

- Apagar **Cron Schedule** do serviço cron, ou
- `EGO_DAILY_STATS_ENABLED=0` na API
