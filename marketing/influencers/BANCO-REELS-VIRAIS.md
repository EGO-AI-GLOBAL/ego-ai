# Banco de Reels — EGO-AI

Registo de **TODOS** os vídeos feitos, **ordenados por resultado** (score).  
TOP 10 = os melhores para enviar a influencers.

**Regra:** cada vídeo novo → adicionar em `TODOS-REELS-POR-RESULTADO.csv` → reordenar → atualizar `TOP-10-REELS.csv`.

| Arquivo | Conteúdo |
|---------|----------|
| **`TODOS-REELS-POR-RESULTADO.csv`** | **12 vídeos** já feitos · score · métricas ads |
| **`TOP-10-REELS.csv`** | 10 melhores para pacote influencer (10 dias) |
| `ABRIR-REELS-POR-RESULTADO.bat` | Abre planilha no Excel |

**Modelo oficial (propostas DM):**

| Quem | O quê |
|------|--------|
| **Influencer** | Story — rosto dela, 2 frases, link + cupom |
| **EGO-AI** | Reels prontos — MP4 + legenda, ela só publica #publi |

Propostas: `PROPOSTA-DM-PADRAO.txt` · TOP 10: `TOP-10-REELS.csv`

Atualizado: 2026-06-26

---

## Todos os vídeos feitos (por resultado)

Ver planilha completa: **`TODOS-REELS-POR-RESULTADO.csv`**

| Rank | Score | Arquivo | Ads? | Veredicto |
|------|-------|---------|------|-----------|
| 1 | 100 | `ego-ai-agenda-reel3-reels.mp4` | Reel 3 | ✅ **#1 enviar** |
| 2 | 98 | `ego-ai-agenda-retencao-reels.mp4` | Reel 2 ads | ✅ **#2 enviar** |
| 3 | 85 | `ego-ai-1.0.39-retencao-reels.mp4` | orgânico | ✅ Enviar |
| 4 | 75 | `ego-ai-1.0.39-viral-reels.mp4` | orgânico | Testar |
| 5 | 70 | `ego-ai-1.0.39-reels.mp4` | orgânico | Testar |
| 6 | 65 | `ego-ai-1.0.39-claro-reels.mp4` | orgânico | Testar |
| 7 | 35 | `ego-ai-1.0.42-retencao-reels.mp4` | Reel 1 ads | ❌ Monstrinhos CTR 0,5% |
| 8 | 30 | `ego-ai-hoje-reels.mp4` | orgânico | Reserva |
| 9 | 25 | `ego-ai-1.0.35-reels.mp4` | orgânico | Reserva |
| 10 | 22 | `ego-ai-1.0.34-reels.mp4` | orgânico | ❌ 70s longo |
| 11 | 20 | `ego-ai-app-real-reels.mp4` | orgânico | ❌ 50s demo |
| 12 | 15 | `luna/05-descarrego-completo.mp4` | antigo | ❌ legado |

---

## TOP 10 — enviar para influencers

| # | Reel | Hook | Duração | CTR | Visitas perfil | Custo/visita | Veredicto |
|---|------|------|---------|-----|----------------|--------------|-----------|
| 1 | **Agenda** — "Se você lembra de tudo da..." | Organização | **11s** | **2,3%** | **27** | **R$ 0,96** | ✅ **USAR** |
| 2 | Monstrinhos — "Baixei um app só pro meu..." | Companheiro | 19s | 0,5% | 13 | R$ 1,85 | ❌ Não renovar |

**Regra:** ângulo **agenda / rotina / lembra de tudo** · vídeo **~10s** · CTA site ou link parceiro.

---

## Arquivos de vídeo no projeto

| Arquivo | Ângulo | Usar para influencer? |
|---------|--------|------------------------|
| `marketing/videos/app-real/ego-ai-agenda-reel3-reels.mp4` | Agenda Reel 3 | ✅ **Prioridade 1** |
| `marketing/videos/app-real/ego-ai-agenda-retencao-reels.mp4` | Agenda retenção | ✅ Prioridade 2 |
| `marketing/videos/app-real/ego-ai-1.0.42-retencao-reels.mp4` | Retenção geral | ✅ Backup |
| `marketing/videos/app-real/ego-ai-1.0.39-viral-reels.mp4` | Viral genérico | ⚠️ Testar |
| `marketing/videos/app-real/ego-ai-1.0.39-claro-reels.mp4` | Versão clara | ⚠️ Testar |
| `marketing/videos/app-real/ego-ai-hoje-reels.mp4` | Descarrego | ⚠️ Secundário |

Legendas prontas: `marketing/POST-REEL-3.txt`, `marketing/POST-REEL-AGENDA.txt`, `marketing/INSIGHTS-REELS-1-2.txt`

---

## Novos Reels — ficha para preencher quando viralizar

Copie e cole uma linha por vídeo:

```
DATA: __/__/2026
ARQUIVO: marketing/videos/app-real/__________.mp4
HOOK (1ª frase): 
DURAÇÃO: __s
ORGÂNICO / ADS: 
VISUALIZAÇÕES: 
CTR / CLIQUES: 
COMENTÁRIO FIXADO: 
APTO INFLUENCER (S/N): 
NOTAS: 
```

---

## Reels virais de OUTRAS contas (referência)

Use só como **inspiração de hook** — não repostar sem direitos.

| Conta | Views (ref.) | O que copiar |
|-------|--------------|--------------|
| @ericalacerdafit | 2M–15M (fixados) | Transformação + texto na tela |
| @rebeccafbarros | 4k–13k/reel recente | Lifestyle + produto natural |
| @fabricia_vianaaa | 6k–112k | Rotina local, autenticidade |

---

## Pacote influencer — Story only + Reels prontos

### O que a influencer faz (menos trabalho = preço menor)

| Ela faz | EGO fornece |
|---------|-------------|
| **1 Story/dia** (10 dias) — rosto dela, 2–3 frases, link sticker | Roteiro do Story (copiar/colar) |
| Opcional: **publicar Reel pronto** (1/dia) — só legenda + #publi | MP4 + legenda + link `/go?ref=CODIGO` |
| Cupom dela no link | SQL parceiro + link pronto |

### O que NÃO funciona bem

- Repostar **o mesmo Reel idêntico** em 3 perfis — Instagram penaliza
- Só Reel pronto **sem** Story dela — converte menos que rosto + link
- Reel 19s monstrinhos — CTR baixo nos nossos dados

### O que funciona

- Story dela (confiança) + Reel nosso **com intro dela 3s** (“gente, testei isso…”)
- Ou: Story todo dia + **1 Reel/semana** dela gravando tela do app
- Variantes: 3–5 MP4s diferentes, rotacionar entre influencers

---

## Roteiro Story (modelo — influencer só lê)

```
Slide 1 (falando):
"Gente, tô usando um app que organiza agenda e lembrete 
com uma IA que parece conversa — EGO-AI."

Slide 2:
"Tem Luna e Leo, voz, chat… link aqui 👆"

Sticker: link /go?ref=CODIGO&next=signup

Slide 3 (opcional):
"Cupom CODIGO = 10% na 1ª assinatura. Testa grátis."
```

---

## Preço revisado (Story only vs pacote completo)

| Pacote | Fabrícia | Rebecca | Érica |
|--------|----------|---------|-------|
| 10d Story + 10 Reel **dela grava** | R$ 2–3,5k | R$ 8–15k | R$ 25k+ |
| **10d Story dela + Reels prontos EGO** | **R$ 800–1.500** | **R$ 3–6k** | **R$ 8–15k** |
| 10d Story only (sem Reel) | R$ 400–800 | R$ 2–4k | R$ 5–10k |

*Negociar sempre: menos trabalho dela = menos fixo.*

---

## Pasta entrega influencer (montar ao fechar)

```
marketing/influencers/entrega/FABRICIA10/
  01-reel-agenda-reel3.mp4
  02-reel-agenda-retencao.mp4
  ROTEIRO-STORY.txt
  LEGENDA-REEL.txt
  LINK.txt          → /go?ref=FABRICIA10&next=signup
  CUPOM.txt         → FABRICIA10
```

---

## Checklist antes de mandar material

- [ ] Link `/go?ref=` testado no celular
- [ ] Cupom cadastrado no Supabase
- [ ] Legenda com **#publi** ou “parceria paga”
- [ ] MP4 vertical 9:16, ≤30s (ideal ~10s)
- [ ] Não mandar o mesmo MP4 para 2 influencers no mesmo dia

---

## Próximos passos

1. Guardar métricas do **Reel 3** ads → atualizar `TOP-10-REELS.csv`
2. Gerar **2–3 variantes** agenda ~10s (subir no ranking)
3. Nova influencer interessada → `PROPOSTA-DM-PADRAO.txt` + pasta `entrega/[CODIGO]/`

Ver também: `marketing/PREVISAO-INFLUENCERS-10-DIAS.csv`
