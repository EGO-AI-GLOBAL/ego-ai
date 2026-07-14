EGO-AI — PLANO VISUAL "NOSSA QUE MASSA" (mockup / direção)
=============================================================
Feedback testador: app funciona, mas parece simples e feio.
Regra: NÃO complicar funções — só elevar acabamento (premium + futurista suave).

═══════════════════════════════════════════════════════════════════
HOJE (por que parece "simples demais")
═══════════════════════════════════════════════════════════════════

Login:     fundo cinza + card branco + logo estático
Chat:      bolhas planas, header básico, menu hamburger comum
Cores:     roxo + cinza (correto, mas sem profundidade)
Monstrinhos: MELHOR parte visual (jardim animado) — usar como referência
Bolso:     estilo retrô (proposital) — não misturar com "futurista"

O testador provavelmente viu: Login + Chat + Agenda "planas"
e não chegou ao jardim dos Monstrinhos.

═══════════════════════════════════════════════════════════════════
DIREÇÃO: "COMPANHEIRO IA PREMIUM" (não sci-fi agressivo)
═══════════════════════════════════════════════════════════════════

Referência de sensação (não copiar layout):
  • Abertura tipo app de IA premium (escuro, luz suave)
  • Luna/Leo em destaque — vídeo/avatar já é o "wow"
  • Cards com vidro + borda luminosa leve
  • Roxo EGO + ciano (#22D3EE) como "energia" — já no ícone

Evitar:
  • Neon exagerado, matrix, fonte futurista ilegível
  • Muitos gradientes rainbow
  • Parecer jogo arcade ou app bancário

═══════════════════════════════════════════════════════════════════
ANTES × DEPOIS (wireframe)
═══════════════════════════════════════════════════════════════════

── LOGIN HOJE ──
┌────────────────────────┐
│   [logo png]           │
│ ┌────────────────────┐ │
│ │ email              │ │
│ │ senha              │ │
│ │ [ Entrar ]         │ │
│ └────────────────────┘ │
└────────────────────────┘

── LOGIN "WOW" (fase 1) ──
┌────────────────────────┐
│ ░░ gradiente escuro ░░ │  ← mesh roxo→azul noite
│                        │
│    (Luna vídeo loop    │  ← 3s ao abrir, já existe asset
│     ou avatar glow)    │
│                        │
│  EGO-AI                │  ← tipografia mais forte
│  Seu companheiro com   │
│  voz e rosto           │
│                        │
│ ╭─ vidro ─────────────╮│
│ │ email               ││  ← blur + borda 1px luminosa
│ │ senha               ││
│ │ ═══ Entrar ═══      ││  ← botão com glow suave
│ ╰─────────────────────╯│
└────────────────────────┘

── CHAT HOJE ──
[≡]  Chat
─────────────────
 bolha cinza
 bolha branca
 [composer]

── CHAT "WOW" (fase 2) ──
┌────────────────────────┐
│ ░ fundo gradiente ░    │  ← sutil, não compete com texto
│                        │
│     ┌─────────┐        │
│     │ Luna    │        │  ← avatar maior no topo vazio
│     │ (fala)  │        │     anel pulsante quando TTS
│     └─────────┘        │
│                        │
│  ╭─ Luna ─────────────╮│
│  │ Oi! Como posso...  ││  ← bolha assistente: vidro + borda
│  ╰────────────────────╯│
│        ╭─ você ────────╮│
│        │ oi            ││  ← bolha user: roxo suave
│        ╰───────────────╯│
│ [cartão Monstrinhos]   │  ← já existe, só polish
│ ═══════════════════════│
│ 🌙  [━━━━ mensagem ━━━]│  ← composer flutuante, sombra
└────────────────────────┘

═══════════════════════════════════════════════════════════════════
5 MELHORIAS DE MAIOR IMPACTO (ordem)
═══════════════════════════════════════════════════════════════════

| # | O quê | Efeito "massa" | Esforço |
|---|--------|----------------|---------|
| 1 | Fundo gradiente + glow no login e chat | Primeira impressão | Médio |
| 2 | Avatar Luna/Leo maior ao abrir chat + anel ao falar | Já tens vídeo — só layout | Baixo |
| 3 | Cards vidro (blur) em formulários e bolhas | Premium 2025 | Médio |
| 4 | Splash 1.5s: logo + fade no avatar | "Abri o app uau" | Baixo |
| 5 | Botões e FAB mic com gradiente + haptic | Tacto moderno | Baixo |

NÃO mexer agora: Monstrinhos jardim (já bom), Bolso retrô, API, auth.

═══════════════════════════════════════════════════════════════════
FASES DE LANÇAMENTO
═══════════════════════════════════════════════════════════════════

1.0.49 — "Polish visual" (só UI, sem feature nova)
  • Splash animado
  • Login com fundo gradiente + botão premium
  • Chat: fundo + bolhas + composer flutuante
  • Default dark (ou respeitar sistema) — dark impressiona mais

1.0.50 — "Hero moment"
  • Primeira abertura pós-login: Luna fala 1 frase (onboarding já existe — só visual)
  • Cartão "3 toques" com ícones melhores

Depois da Play pública — se testadores validarem:
  • Micro-animações Monstrinhos ao escolher humor
  • Tema claro refinado (hoje light é muito "planilha")

═══════════════════════════════════════════════════════════════════
FRASE PARA O TESTADOR
═══════════════════════════════════════════════════════════════════

"Você tem razão no visual — estamos mantendo simples de usar,
mas a próxima versão traz cara de app premium: mais Luna na
abertura, cores com profundidade e menos tela 'crua'."

═══════════════════════════════════════════════════════════════════
ARQUIVOS QUE MUDARIAM (quando for codar)
═══════════════════════════════════════════════════════════════════

app/src/theme/colors.ts          — gradientes, glow tokens
app/app/login.tsx                — hero + fundo
app/app/signup.tsx               — igual login
app/src/components/ScreenShell.tsx — header mais limpo
app/src/components/ChatPreview.tsx — bolhas
app/src/components/ChatComposer.tsx — barra flutuante
app/src/components/SpeakingAvatar.tsx — anel glow ao falar
app/app/_layout.tsx ou splash    — animação entrada

Não tocar: ego_api, auth, voz upload, Stripe, agenda lógica.
