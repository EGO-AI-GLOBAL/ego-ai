EGO-AI — MOCKUP VISUAL (só para ver — não é código)
====================================================
Objetivo: mostrar como seria um "Hub Apoio" vs melhorar o que já existe.
Nada disto está implementado — é wireframe + textos.

═══════════════════════════════════════════════════════════════════
OPÇÃO A — HUB APOIO (1 tela nova que SÓ LIGA o que já existe)
═══════════════════════════════════════════════════════════════════

Onde entraria no menu (exemplo):

  Menu lateral (hoje)              Menu lateral (com Hub)
  ───────────────────              ──────────────────────
  Chat                             Chat
  Monstrinhos do Humor             ★ Apoio no dia a dia  ← NOVO (só atalhos)
  EGO de Bolso                     Monstrinhos do Humor
  Agenda                           EGO de Bolso
  ...                              Agenda
                                   ...

───────────────────────────────────────────────────────────────────
TELA: APOIO NO DIA A DIA
───────────────────────────────────────────────────────────────────

┌─────────────────────────────────────────┐
│  ←  Apoio no dia a dia                  │
│                                         │
│  Oi, Maria. Como você está agora?       │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐│
│  │ 😔  │ │ 😐  │ │ 🙂  │ │ 😊  │ │ 🤩  ││
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘│
│  (toque → abre Monstrinhos, já existe)  │
│                                         │
│  ─── Preciso de ajuda agora ───         │
│                                         │
│  ┌───────────────────────────────────┐│
│  │ 💬  Conversar com Luna              ││ → Chat (já existe)
│  │     Texto ou voz                    ││
│  └───────────────────────────────────┘│
│  ┌───────────────────────────────────┐│
│  │ 🌙  Desabafar (noite)               ││ → Chat modo desabafo (já existe)
│  │     Grava ou escreve; amanhã agenda ││
│  └───────────────────────────────────┘│
│  ┌───────────────────────────────────┐│
│  │ 🫁  Respirar 1 minuto               ││ → Missão Monstrinhos / ritual (já existe)
│  │     Sem pressa                      ││
│  └───────────────────────────────────┘│
│                                         │
│  ─── Minha rotina hoje ───              │
│                                         │
│  ┌───────────────────────────────────┐│
│  │ 💜  Monstrinhos — 2/5 missões       ││ → daily-care (já existe)
│  └───────────────────────────────────┘│
│  ┌───────────────────────────────────┐│
│  │ 🥚  EGO de Bolso — lembrete 18h     ││ → wellness-journey (já existe)
│  └───────────────────────────────────┘│
│  ┌───────────────────────────────────┐│
│  │ 📅  Agenda — 1 compromisso hoje   ││ → agenda (já existe)
│  └───────────────────────────────────┘│
│                                         │
│  ─── Importante ───                     │
│  O EGO apoia no dia a dia. Não         │
│  substitui psicólogo ou médico.         │
│  Crise? Ligue CVV 188 (24h).           │
│                                         │
└─────────────────────────────────────────┘

Custo: ~1 ecrã React Native + links (router.push).
Não cria match-3, não cria IA nova.

═══════════════════════════════════════════════════════════════════
OPÇÃO B — SEM HUB (melhorar o que já tem — RECOMENDADO)
═══════════════════════════════════════════════════════════════════

Em vez de menu novo, o utilizador vê isto no CHAT (primeira abertura):

┌─────────────────────────────────────────┐
│  Luna · Chat                            │
├─────────────────────────────────────────┤
│  ┌─ Seu dia em 3 toques ─────────────┐ │
│  │ 1️⃣ Humor    2️⃣ Dizer oi    3️⃣ Agenda │ │
│  │ [Monstrinhos] [já está aqui] [abrir] │ │
│  └─────────────────────────────────────┘ │
│                                         │
│  ┌─ Jardim dos Monstrinhos ────────────┐ │  ← cartão que JÁ EXISTE no 1.0.48
│  │  Pet + 2/5 missões · [Abrir jardim] │ │
│  └─────────────────────────────────────┘ │
│                                         │
│  ... mensagens ...                      │
│                                         │
│  [🌙 Desabafo]  [mic]  [escrever...]    │  ← botão desabafo JÁ EXISTE
└─────────────────────────────────────────┘

Monstrinhos (ecrã que JÁ EXISTE — só textos melhores):

┌─────────────────────────────────────────┐
│  Monstrinhos do Humor 💜                │
├─────────────────────────────────────────┤
│  [Jardim animado + pet]                 │
│                                         │
│  Como você está?  😔 😐 🙂 😊 🤩         │
│                                         │
│  Missões de hoje (2/5)                  │
│  ☑ Humor   ☑ Respirar   ☐ Regar ...     │
│                                         │
│  💡 Respirar 1 min ajuda na ansiedade.  │  ← NOVO: só 1 linha de copy
│     Não substitui terapia.              │
└─────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
COMPARAR AS DUAS OPÇÕES
═══════════════════════════════════════════════════════════════════

| | Hub Apoio (A) | Melhorar existente (B) |
|---|---------------|------------------------|
| Ecrãs novos | 1 | 0 (só cards/textos) |
| Tempo dev | ~3–5 dias | ~1–2 dias |
| Utilizador percebe? | Sim, se abrir o menu | Sim, se abrir Chat |
| Risco menu cheio | +1 item no drawer | Nenhum |
| Para teste 1.0.48 | Distrai | Encaixa |

═══════════════════════════════════════════════════════════════════
PRIMEIROS 3 DIAS (fluxo — Opção B, sem função nova)
═══════════════════════════════════════════════════════════════════

DIA 1 — Instalou
  Abre app → Chat
  Banner: "Toque no humor · escreva oi · marque 1 compromisso"
  Luna responde ao "oi"
  Push opcional no fim do dia: "Como foi o humor hoje?"

DIA 2 — Voltou
  Cartão Monstrinhos no chat: "2 missões novas"
  Sugestão: "Experimente voz — segure o microfone"
  Bolso: "1 missão no EGO de Bolso"

DIA 3 — Hábito
  Streak Monstrinhos visível
  Se noite: botão Desabafo destacado
  "Amanhã veja a agenda"

═══════════════════════════════════════════════════════════════════
REELS / MARKETING (mesma mensagem, sem Hub)
═══════════════════════════════════════════════════════════════════

Hook 1:
  "Não é Candy. É quem pergunta como você está."
  [tela humor Monstrinhos → chat oi]

Hook 2:
  "Ansiedade à noite? Desabafo. De manhã a Luna organiza."
  [botão desabafo → agenda manhã]

Hook 3:
  "Finch em inglês. EGO em português, com voz."
  [Luna falando + jardim]

═══════════════════════════════════════════════════════════════════
VEREDITO PARA DECISÃO
═══════════════════════════════════════════════════════════════════

Hub Apoio = bonito no papel, mas é REORGANIZAÇÃO.

Para "só ver como seria": imagina o mockup da Opção A acima.

Para lançar agora (1.0.49): Opção B — cartão no chat + 3 linhas
de copy + fluxo 3 dias. Sem aba nova.

Se depois dos testadores 80% disserem "não achei o desabafo",
aí sim vale o Hub (Opção A).
