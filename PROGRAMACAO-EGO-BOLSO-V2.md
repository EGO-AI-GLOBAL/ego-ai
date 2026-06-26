# Programação EGO de Bolso v2 — 1 fase por dia + build

Ritmo acordado: **de manhã** build/submit da fase anterior · **à tarde** código da fase nova · **no fim do dia** enfileirar próxima versão.

Pasta: `EGO-AI-APP - Copia` · Branch: `main` · Sempre Android + iOS juntos.

---

## Dia 0 — Quarta (build 1.0.47 já preparada)

| Quando | Quem | O quê |
|--------|------|--------|
| **Manhã** | Outro agente / tu | `SUBIR-BUILD-1.0.47.bat` → `AGUARDAR-E-SUBMETER-1.0.47.bat` |
| Tarde | — | Testar no telemóvel: 5 missões/dia, Entre Nós, Monstrinhos F5 |
| Railway | **Só depois** da loja publicar | `EGO_LATEST_APP_VERSION=1.0.47` · `versionCode=85` |

**Não começar Dia 1** antes da 1.0.47 estar submetida (ou pelo menos na fila EAS).

---

## Calendário v2 (Dia 1 → Dia 10)

| Dia | Data* | Manhã | Tarde (código) | Build no fim do dia | Versão |
|-----|-------|--------|----------------|---------------------|--------|
| **1** | Qui | Aguardar/submit **1.0.47** se ainda pendente | ~~Habitat animado~~ **incluído na 1.0.47** | `SUBIR-BUILD-1.0.47.bat` | 1.0.47 · iOS 34 · Android 85 |
| **2** | Sex | Submit **1.0.47** quando EAS terminar | **Pet com vida** — piscar, flutuar, feliz ao completar missão | 1.0.48 · iOS 35 · Android 86 |
| **3** | Sáb | Submit **1.0.49** | **Nome do bolso** — campo, `ui_state`, push e frases com nome | 1.0.50 · iOS 37 · Android 88 |
| **4** | Dom | Submit **1.0.50** | **Push 10h** — «Faltam X/5 missões» (máx. 2/dia com 18h) | 1.0.51 · iOS 38 · Android 89 |
| **5** | Seg | Submit **1.0.51** | **Estrelas + loja** — 3–5 cores de ovo | 1.0.52 · iOS 39 · Android 90 |
| **6** | Ter | Submit **1.0.52** | **Partilha viral** — card e textos WA/IG melhorados | 1.0.53 · iOS 40 · Android 91 |
| **7** | Qua | Submit **1.0.53** | **Simulador viral** — script Python + doc cenários | 1.0.54 · iOS 41 · Android 92 |
| **8** | Qui | Submit **1.0.54** | **Missão da semana** — desafio 7 dias na API | 1.0.55 · iOS 42 · Android 93 |
| **9** | Sex | Submit **1.0.55** | **Chat + bolso** — avatar menciona missão pendente | 1.0.56 · iOS 43 · Android 94 |
| **10** | Sáb | Submit **1.0.56** | **Polimento** — regression, checklist, widget Android se der | 1.0.57 · iOS 44 · Android 95 |

\*Datas assumem **amanhã = 1.º dia da tabela (Quinta)**. Ajusta se a 1.0.47 sair noutro dia.

---

## Rotina de cada dia (tu + agente)

### Manhã (~30 min)
1. `AGUARDAR-E-SUBMETER` da versão de ontem (se build já terminou)
2. Smoke rápido no telemóvel (1 fluxo bolso)
3. Dizer ao agente: **«Dia N do bolso»** (este chat)

### Tarde (agente implementa)
- Só a fase do dia — **sem** refatorar auth/voz/Stripe
- `python scripts\regression_guard.py`
- `python scripts\smoke_test_api.py`
- Commit + push `main`

### Fim do dia (~15 min)
1. Bump `app.config.ts` (versão do dia)
2. Criar/copiar `SUBIR-BUILD-1.0.XX.bat` se ainda não existir
3. `SUBIR-BUILD-1.0.XX.bat` (ou pedir ao outro agente)

### Depois de publicar cada versão na loja
- Railway: `EGO_LATEST_APP_VERSION` + `EGO_LATEST_ANDROID_VERSION_CODE` **só quando a loja tiver a build**

---

## O que pedir ao agente (copy-paste)

| Dia | Mensagem |
|-----|----------|
| 1 | `Dia 1 do bolso — habitat animado no CompanionPocketScene` |
| 2 | `Dia 2 do bolso — animações do pet (piscar, flutuar)` |
| 3 | `Dia 3 do bolso — nome do companheiro` |
| 4 | `Dia 4 do bolso — push das 10h` |
| 5 | `Dia 5 do bolso — estrelas e loja de cores` |
| 6 | `Dia 6 do bolso — partilha social` |
| 7 | `Dia 7 do bolso — simulador viral` |
| 8 | `Dia 8 do bolso — missão da semana` |
| 9 | `Dia 9 do bolso — chat ligado ao bolso` |
| 10 | `Dia 10 do bolso — polimento e release` |

---

## Builds — outro agente

Handoff fixo para quem só sobe build:

```
cd "C:\Users\Iury\OneDrive\Área de Trabalho\EGO-AI-APP - Copia"
SUBIR-BUILD-1.0.XX.bat
AGUARDAR-E-SUBMETER-1.0.XX.bat
```

Checklist por versão: `marketing/VALIDAR-1.0.XX.txt` (criar a partir do Dia 1).

---

## Regras (não quebrar)

- Uma fase por dia — não acumular 3 fases numa build
- API deploy automático no push — testar smoke antes
- Paridade **Android + iOS** sempre
- Banner Railway **atrás** da loja, nunca antes

---

## Resumo

| Hoje / amanhã | Outro agente → **1.0.47** |
| Amanhã tarde | Este chat → **Dia 1** → build **1.0.48** |
| Dias seguintes | **Dia N** à tarde → **1.0.47+N** à noite |

Quando fores começar: **«Dia 1 do bolso»**.
