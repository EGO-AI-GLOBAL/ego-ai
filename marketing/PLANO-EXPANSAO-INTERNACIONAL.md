# Plano de expansão internacional — Ego-IA

Ordem após **Brasil estável**: Play pública + App Store + sem bugs graves por ~2 semanas.  
**Pagamento internacional:** manter **USD** (links Stripe INT já prontos ou a completar).  
**Cupom / influenciadores:** só depois das 2 lojas BR públicas e estáveis (ver `PROGRAMA-INDICACAO.md`).

---

## Pré-requisitos globais (antes de qualquer país novo)

- [ ] Brasil: teste interno → **loja pública** Android
- [ ] iPhone: **App Store** aprovada e pública
- [ ] Agenda, chat, voz, pagamento validados (webhook Stripe **200**)
- [ ] Links Stripe INT completos (ver secção Stripe abaixo)
- [ ] Site `egoai.com.br` com privacidade/termos ok
- [ ] Suporte: `contato@egoai.com.br` respondendo em 24–48h

---

## Fases (ordem recomendada)

| Fase | Mercado | Idioma | Moeda checkout | Esforço |
|------|---------|--------|----------------|---------|
| **0** | Brasil | PT-BR | BRL (R$) | Em curso |
| **1** | Portugal | PT-PT | **USD** (INT) | Baixo |
| **2** | México | ES | **USD** (INT) | Médio |
| **3** | Colômbia, Chile, Argentina | ES | **USD** (INT) | Médio (reuso ES) |
| **4** | Espanha | ES (EU) | USD → EUR opcional | Médio-alto |
| **5** | EUA | EN | **USD** (INT) | Alto (concorrência + ads) |
| **6** | Filipinas / Indonésia | EN / local | USD | Alto (volume, ticket baixo) |

---

## Stripe INT (USD) — completar uma vez para todos

Já confirmado:

```env
STRIPE_CHECKOUT_INT_CONNECTION_URL=https://buy.stripe.com/00w3cx9UibTs0ze24W4ow04
```

**Criar no Stripe** (Payment Link mensal, moeda **USD**, metadata `plan_tier`):

| Plano | Preço | Variável `.env` |
|-------|-------|-----------------|
| EGO AI Premium | US$ 14,99/mês | `STRIPE_CHECKOUT_INT_PREMIUM_URL` |
| EGO AI Complete | US$ 29,99/mês | `STRIPE_CHECKOUT_INT_TOTAL_URL` |
| EGO AI Business | US$ 49,99/mês | `STRIPE_CHECKOUT_INT_ENTERPRISE_URL` |

Em **cada** link INT: **Allow promotion codes** (para cupom `EGOINDICA10` no futuro).

Colocar URLs no Railway (ego-ai) → Redeploy.

**Portugal e LATAM:** usam estes mesmos links — **não** criar EUR/MXN no início.

---

## Fase 1 — Portugal (piloto internacional)

**Porquê primeiro:** mesmo idioma, cultura próxima, mercado menor = teste barato.

### Produto / app

- [ ] Secção **Internacional (USD)** visível no ecrã Planos (já existe)
- [ ] Revisão **PT-PT** (não obrigatório código novo — textos loja + site primeiro):
  - telemóvel, aplicação, correio eletrónico, agendar
- [ ] Luna/Leo: prompts podem ficar PT-BR no início; PT-PT fino na fase 2

### Lojas

**Google Play**

- [ ] País: adicionar **Portugal** na distribuição
- [ ] Listing PT-PT: título, descrição curta/longa
- [ ] Screenshots (reutilizar BR ou legendas PT-PT)
- [ ] Preço: app grátis; assinatura via Stripe **US$** (mencionar na descrição)

**App Store** (quando iOS público)

- [ ] Disponibilidade: Portugal
- [ ] Metadados PT-PT
- [ ] Nota: *“Assinatura cobrada em dólares (USD) via Stripe”*

### Marketing

- [ ] Instagram / site: post “Disponível em Portugal”
- [ ] Hashtags PT: `#egoai #ia #produtividade #bemestar`
- [ ] Ads: orçamento baixo (€5–10/dia) só PT, 7 dias teste
- [ ] **Sem** cupom influenciador nesta fase

### Suporte

- [ ] FAQ: “Porque é que o preço aparece em dólares?”  
  → *O cartão converte para euros; cobrança internacional em USD.*

### Métricas de sucesso (30 dias)

| Métrica | Meta piloto |
|---------|-------------|
| Instalações PT | 50–200 |
| Cadastros | >40% instalações |
| 1ª mensagem no chat | >50% cadastros |
| Assinantes pagos | ≥3–5 |
| Bugs críticos | 0 repetidos |

### Quando passar EUR (opcional, fase 1b)

Só se ≥20 pagantes PT ou muitas dúvidas sobre USD → duplicar links Stripe em EUR (~€7,49 / €13,99 / €27,99).

---

## Fase 2 — México

**Idioma:** espanhol (MX). **Moeda:** USD (links INT).

### Antes de abrir

- [ ] Tradução **ES** mínima: onboarding, planos, erros comuns, site landing
- [ ] Criativos Reels/TikTok em espanhol (reaproveitar estrutura vídeo 1 e 2)
- [ ] Play + App Store listing **es-MX**

### Lojas

- [ ] Distribuição: México
- [ ] Descrição: companheiro IA, voz, agenda; preço desde US$ 7,99/mês

### Marketing

- [ ] Meta Ads: México, 25–54, Instagram, orçamento teste
- [ ] Influenciador micro (opcional) — **sem** cupom até política global de indicação

### Métricas (60 dias)

- Instalações: 500+
- CPI alvo: < US$ 2–4 (teste)
- Assinantes: validar conversão vs Portugal

---

## Fase 3 — LATAM (Colômbia, Chile, Argentina)

**Reuso:** mesmo app ES + mesmos links USD.

| País | Prioridade | Nota |
|------|------------|------|
| Colômbia | Alta | Android forte, custo ads menor |
| Chile | Média | Melhor ticket médio |
| Argentina | Média | Cuidado inflação; USD ajuda |

### Checklist (bloco único)

- [ ] Play/App Store: adicionar os 3 países
- [ ] Listing ES (variante neutra LATAM)
- [ ] Ads: 1 país de cada vez (não os 3 juntos no dia 1)
- [ ] Suporte: horário América (UTC−3/−5)

---

## Fase 4 — Espanha

- [ ] ES europeu (vos/tu vs ustedes — revisão leve)
- [ ] GDPR: confirmar política privacidade + exclusão conta (`egoai.com.br/exclusao-conta/`)
- [ ] USD no início; EUR se volume justificar
- [ ] Concorrência maior — criativo e ASO mais cuidadosos

---

## Fase 5 — Estados Unidos

**Só entrar com:** receita BR+PT+LATAM, app polido, budget ads, listing **100% inglês**.

- [ ] App: taglines EN (já parcial em `stripeMonthly.ts`)
- [ ] Chat/persona: inglês nativo nos prompts
- [ ] Play + App Store US
- [ ] Ads: custo alto — testar US$ 20–30/dia mínimo 14 dias
- [ ] Diferencial: rosto + voz + agenda (não “mais um ChatGPT”)

---

## Fase 6 — Filipinas / Indonésia (opcional, volume)

- [ ] Inglês (PH) ou inglês + UI parcial local (ID)
- [ ] Ticket baixo — plano Pro US$ 7,99 como âncora
- [ ] TikTok / Reels pesado
- [ ] Suporte async (WhatsApp/ email)

---

## O que NÃO muda entre países (fase 1–3)

| Item | Mantém |
|------|--------|
| Preços INT | US$ 7,99 / 14,99 / 29,99 / 49,99 |
| Payment Links | Mesmos 4 links INT |
| API Railway | `ego-ai-production` |
| Webhook | `/stripe/webhook` |
| Cupom futuro | `EGOINDICA10` (quando ligar indicação) |

---

## O que muda por país

| Item | BR | PT | MX/LATAM | EUA |
|------|----|----|----------|-----|
| Língua app/loja | PT-BR | PT-PT | ES | EN |
| Moeda checkout | BRL | USD | USD | USD |
| Oferta lançamento R$ 9,99 | Sim | Não | Não | Não |
| Teste interno Play | Sim | Não (público) | Não | Não |

---

## Calendário sugerido (exemplo)

| Quando | Ação |
|--------|------|
| Agora | BR teste + ads + bugs |
| BR público + iOS OK | Estabilizar 2 semanas |
| Mês +1 | **Portugal** piloto (USD, PT-PT loja) |
| Mês +2 | Completar 3 links Stripe INT em falta |
| Mês +3 | **México** + ES no app |
| Mês +4–5 | Colômbia / Chile |
| Mês +6+ | Espanha ou EUA (conforme dados) |
| Lojas estáveis + sem bugs | **Cupom + influenciadores** |

---

## Checklist rápida — Portugal (copiar e ir marcando)

```
PRÉ
[ ] BR loja pública Android
[ ] iOS App Store pública
[ ] Webhook 200 em pagamento real
[ ] INT_PREMIUM + INT_TOTAL + INT_ENTERPRISE no Stripe + Railway

LOJA
[ ] Play: país Portugal ativo
[ ] Play: texto PT-PT (título + descrição)
[ ] App Store: Portugal + PT-PT (quando iOS live)

COMUNICAÇÃO
[ ] Site: linha “Disponível em Portugal”
[ ] Post Instagram / Kwai PT
[ ] FAQ USD → EUR no cartão

MÉTRICAS (30 dias)
[ ] Instalações ___
[ ] Pagantes ___
[ ] Bugs críticos: nenhum repetido → OK para Fase 2 (México)
```

---

## Referências no projeto

- Preços: `PLANS_MONTHLY.md`
- Indicação (futuro): `marketing/PROGRAMA-INDICACAO.md`
- Copy loja BR: `marketing/loja/PLAY_STORE_COPY.md`
- Copy App Store: `marketing/loja/APP_STORE_COPY.md`
- Estratégia geral: `marketing/ESTRATEGIA_DIVULGACAO.md`

---

*Última atualização: junho 2026 — expansão em USD; EUR/MXN só com volume.*
