# EGO-AI — Roteiro: API vs APK (testes e correções)

Use este guia quando um testador reportar bug ou quando for corrigir algo.

---

## Regra de ouro

| Onde corrigir | Quando | Testador precisa atualizar app? |
|---------------|--------|----------------------------------|
| **API (Railway)** | Lógica no servidor, limites, Stripe, agenda, avatar via API | **Não** — fecha e abre o app |
| **Supabase (SQL)** | Tabelas, plano manual, convites | **Não** |
| **APK (Play)** | Botões, telas, scroll, layout, aviso de atualização | **Sim** — Play Store → Atualizar |

**Versão velha continua funcionando** até a pessoa atualizar na Play.

---

## Fluxo quando aparece um bug

### 1) Classificar

| Sintoma | Provável camada |
|---------|-----------------|
| "Erro interno" no chat/agenda | API |
| Botão some / não rola a tela | APK |
| Plano não ativa após pagar | API + Stripe webhook |
| Crash ao abrir | APK |
| Só uma conta (teste Total) | Supabase / Railway env |

### 2) Corrigir

**Só API:**
1. Alterar `ego_api/` ou `flask_api.py`
2. `git push` → Railway redeploy (2–5 min)
3. Pedir ao testador: fechar e abrir o app

**APK necessário:**
1. Corrigir `app/`
2. Subir `EGO_LATEST_APP_VERSION` na Railway (ver abaixo)
3. Build EAS → Play teste interno
4. Testadores com versão antiga veem faixa **"Ir para a Play"**

### 3) Validar (checklist rápido)

- [ ] Login
- [ ] Chat "Oi"
- [ ] Trocar avatar
- [ ] Convidar na agenda
- [ ] Cadastro (novo testador)
- [ ] Planos / checkout (opcional)

---

## Aviso de atualização no app (1.0.11+)

Quando publicar versão nova na Play:

### Railway — variáveis

```env
EGO_LATEST_APP_VERSION=1.0.11
EGO_PLAY_STORE_URL=https://play.google.com/apps/internaltest/4700773173398888106
EGO_APP_UPDATE_MESSAGE=Nova versão com correções. Toque em Ir para a Play.
```

| Variável | Função |
|----------|--------|
| `EGO_LATEST_APP_VERSION` | Versão **na Play** (igual ao `app.config.ts`) |
| `EGO_PLAY_STORE_URL` | Link teste interno ou loja pública |
| `EGO_APP_UPDATE_MESSAGE` | Texto opcional no banner |

**Ordem:**
1. Publicar APK na Play
2. Atualizar `EGO_LATEST_APP_VERSION` na Railway
3. Redeploy Railway
4. Quem estiver na versão anterior vê o banner ao abrir o app

### Manutenção servidor (opcional)

```env
EGO_MAINTENANCE=1
EGO_MAINTENANCE_MESSAGE=Atualizando o servidor. Volte em 2 minutos.
```

Remove `EGO_MAINTENANCE` quando terminar.

---

## Gravidade — quando subir APK urgente

| Grave (APK rápido) | Pode esperar (só API) |
|--------------------|------------------------|
| Cadastro impossível | Voz falha às vezes |
| App fecha sozinho | Lentidão pontual |
| Login quebrado | Texto de plano |
| Chat texto não responde para todos | Sentry raro |

---

## Mensagem WhatsApp — nova versão na Play

```
Nova versão do EGO-AI na Play.

Opção A: abra o app — deve aparecer faixa "Ir para a Play" no topo.
Opção B: Play Store → Ego-IA → Atualizar.

Depois teste de novo e me diga ✅ ou ❌.
```

---

## Resumo diário (Supabase)

Arquivo: `supabase/RESUMO-DIARIO-USUARIOS.sql` — rode 1x por dia.

---

## Não apagar na Railway (produção)

- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `GOOGLE_API_KEY`, `STRIPE_*`
- `EGO_LATEST_APP_VERSION` (após 1.0.11)

## Remover antes da loja aberta

- `EGO_TEST_TOTAL_EMAILS`
- `EGO_BETA_SEM_LIMITE`
