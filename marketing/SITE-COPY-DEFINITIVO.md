# Site EGO-AI — copy definitivo (verdade + LGPD)

**Uso:** `marketing/landing/index.html` · gerar com `build_site_publico.py --modo completo`

## Regras

- **Sem** “20 dias grátis” até existir trial configurado no Stripe e no app.
- **Plano grátis:** EGO Essencial — Luna e Leo, limites diários, sem cartão.
- **12 avatares:** todos no catálogo; **2 grátis**; restantes por plano (Conexão / Premium / Total).
- **Agenda compartilhada:** validada; convite só para quem já tem conta.
- **IA:** não substitui médico, psicólogo, advogado ou emergência.
- **Lojas:** secção Android + iPhone **sem link** até `playStoreUrl` / `appStoreUrl` no `config.json`.

## Hero

- Título: **EGO-AI: O seu amigo no bolso.**
- Sub: **Sua vida em ordem. Você vive o dia; ele organiza a sua agenda.**
- CTA: **Começar grátis** → `#planos`
- Nota: Plano Essencial · sem cartão de crédito

## Pilares (3)

1. **Chat e voz** — Luna ou Leo; texto e áudio em português.
2. **PDF e fotos** — Anexe e pergunte; resumos na conversa (limites do plano).
3. **Agenda** — Lembretes pessoais e agendas compartilhadas com convite por e-mail.

## Avatares (12)

Ver `marketing/landing/avatars-site.json` — nomes e frases alinhados a `avatarCatalog.ts`.

## Planos (site)

Textos curtos de `marketing/PLANOS-SITE-DESCRICOES.md`. Essencial = “No aplicativo” (sem Stripe).

## Rodapé CTA

- **Pronto para organizar a rotina?**
- **Ver planos** → `#planos`
- Aviso legal + links `/privacidade/` `/termos/` `/exclusao-conta/`

## Cores (`brand/config.json`)

- Fundo: `#121C2C`
- Destaque: `#4D96FF`
- CTA: `#FF6F59`
- Texto: `#FFFFFF` / muted `#E2E8F0`

## Deploy

```powershell
.\.venv\Scripts\python.exe scripts\build_site_publico.py --modo completo
```

Enviar `site-publico/` para `public_html` na UOL.
