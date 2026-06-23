# EGO-AI — Estratégia de divulgação (agência)

## Posicionamento

**Não vendemos:** tecnologia, tokens, “LLM”.  
**Vendemos:** conexão, alívio, produtividade.

| ChatGPT (categoria fria) | EGO-AI |
|--------------------------|--------|
| Ferramenta de trabalho | Companheiro de bolso |
| Sem rosto fixo | Luna ou Leo com voz |
| Web / genérico | App mobile, rotina integrada |
| Preço em dólar, tom neutro | Preço local (R$ / USD), tom acolhedor |

**Frase-mãe:** *Chega de telas frias. Conheça quem te ouve, te organiza e te acompanha de verdade.*

---

## Três pilares de conversão

### 1. Tráfego pago (Meta, TikTok, YouTube Shorts)

Dois criativos principais + retargeting:

| Criativo | Dor | Gancho | CTA |
|--------|-----|--------|-----|
| **A — Solidão / noite** | Feed infinito, solidão, insônia | Luna/Leo “acordou com você” | Baixe grátis AGORA |
| **B — Produtividade** | Correria, esquecer hábitos | Áudio → lembrete + hábitos | Comece grátis |

Roteiros detalhados: [`anuncios/ROTEIROS_CRIATIVOS.md`](./anuncios/ROTEIROS_CRIATIVOS.md).

**Métricas alvo (fase teste 14 dias):** CPI < R$ 8 (BR), instalação → cadastro > 40%, cadastro → 1ª mensagem > 60%.

---

### 2. Influência e viral (TikTok, Reels, Shorts)

**Perfil de creator:** lifestyle, rotina, saúde mental leve, produtividade — **não** tech reviewer.

**Campanhas:**

1. **#MeuNovoAmigo** — vlog: conversa no viva-voz com Luna/Leo no carro/cozinha.  
2. **Corte “Desabafo”** — pergunta relatable (ansiedade de domingo) + resposta humana da IA na tela.

Brief: [`influencers/CAMPANHA_MEU_NOVO_AMIGO.md`](./influencers/CAMPANHA_MEU_NOVO_AMIGO.md).

**Entregáveis por creator:** 1 Reels + 1 Story com link na bio (landing ou loja).

---

### 3. Landing + loja (vitrine)

- Landing: [`landing/index.html`](./landing/index.html)  
- Play Store: [`loja/PLAY_STORE_COPY.md`](./loja/PLAY_STORE_COPY.md)  
- App Store: [`loja/APP_STORE_COPY.md`](./loja/APP_STORE_COPY.md)

**Elementos obrigatórios na vitrine:**

- Hero emocional (Luna/Leo)  
- Comparativo destruidor (EGO vs “robô genérico”)  
- Preços com **Premium = Escolha do Editor** (ancoragem: “menos que uma pizza/mês”)  
- Painel de uso em **%** — “como a bateria do celular, sem surpresa”

---

## Funil sugerido

```
Anúncio / Influencer → Landing ou loja direta → Instala grátis (Essencial)
        → 3–7 dias de uso → Push/in-app: Premium em destaque
        → Checkout Stripe (Conexão / Premium / Total)
```

---

## Calendário de lançamento (4 semanas)

| Semana | Ação |
|--------|------|
| 1 | Landing no ar + 2 vídeos gravados + copy loja |
| 2 | Teste A/B criativo A vs B (R$ 500–1.500/dia BR) |
| 3 | 5 micro-influencers (10k–100k) + cortes desabafo orgânicos |
| 4 | Retargeting quem visitou landing + escala do criativo vencedor |

---

## O que ainda depende do produto

- API em **HTTPS** e app publicado (ver `app/PLAYSTORE.md`)  
- Links reais Play/App Store na landing  
- Política de privacidade pública (`docs/privacidade.html`)  
- Opcional: página `/termos` espelhando `legal_copy.py`
