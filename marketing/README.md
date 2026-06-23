# Marketing EGO-AI — pacote de divulgação

Material alinhado à estratégia de **conexão, alívio e produtividade** (não vender “tokens” nem jargão técnico).

## O que está aqui

| Pasta / arquivo | Uso |
|----------------|-----|
| [`landing/index.html`](./landing/index.html) | Landing (logo, cores e Stripe via `brand/config.json`) |
| [`brand/config.json`](./brand/config.json) | Domínio, cores, links Stripe, redes, UTM |
| [`anuncios/SCRIPTS_15S_FALAS.md`](./anuncios/SCRIPTS_15S_FALAS.md) | Falas Luna/Leo para gravar áudio dos anúncios |
| [`videos/`](./videos/) | **8 vídeos prontos** (avatar + voz do app) — ver `videos/README.md` |
| [`influencers/BRIEF_CREATORS_EGO-AI.pdf`](./influencers/BRIEF_CREATORS_EGO-AI.pdf) | Brief PDF para creators (gerar abaixo) |
| [`anuncios/ROTEIROS_CRIATIVOS.md`](./anuncios/ROTEIROS_CRIATIVOS.md) | Ganchos 1 e 2 + variações para Meta/TikTok |
| [`influencers/CAMPANHA_MEU_NOVO_AMIGO.md`](./influencers/CAMPANHA_MEU_NOVO_AMIGO.md) | Brief para creators lifestyle |
| [`loja/PLAY_STORE_COPY.md`](./loja/PLAY_STORE_COPY.md) | Título, descrições e keywords Play Store |
| [`loja/APP_STORE_COPY.md`](./loja/APP_STORE_COPY.md) | Mesmo para App Store (EN + PT) |
| [`ESTRATEGIA_DIVULGACAO.md`](./ESTRATEGIA_DIVULGACAO.md) | Plano completo em um documento |

## Configurar marca e links

Edite **`marketing/brand/config.json`**:

- `siteUrl`, `domain`, `privacyUrl`
- `playStoreUrl` / `appStoreUrl` quando publicar
- `stripe.connection`, `stripe.premium`, `stripe.total`
- `instagram`, `supportEmail`, `colors`

A landing carrega isso via `landing/brand.js`. Imagens já estão em `landing/img/` (ícone + avatares).

## Publicar a landing

1. Hospede a pasta **`marketing/`** inteira (ou `landing` + `brand` no mesmo host) em HTTPS.
2. Teste: abra `landing/index.html` via servidor local (`npx serve marketing`) para o `config.json` carregar.
3. Use a URL na Play Console e nas bios dos influencers.

## Gerar PDF do brief

```powershell
pip install fpdf2
python scripts/generate_influencer_brief_pdf.py
```

Saída: `marketing/influencers/BRIEF_CREATORS_EGO-AI.pdf`

## Próximos passos (você ou agência)

- [ ] Gravar os 2 vídeos dos roteiros (15–30 s)
- [ ] Contratar 3–5 micro-influencers lifestyle (brief em `influencers/`)
- [ ] Substituir placeholders de loja pelos links reais
- [ ] Screenshots reais do app em `app/store-assets/`
- [ ] Pixel Meta + UTM nas CTAs da landing (`?utm_source=meta&utm_campaign=lancamento`)
