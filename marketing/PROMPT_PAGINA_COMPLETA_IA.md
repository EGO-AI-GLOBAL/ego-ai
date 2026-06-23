# Prompt — página completa EGO-AI (colar na outra IA)

Copie **tudo** entre as linhas `--- INÍCIO ---` e `--- FIM ---`.

A IA deve devolver **um único arquivo `index.html`** (CSS dentro de `<style>`, JS mínimo no final). Você sobe esse arquivo na pasta `public_html` da UOL (+ pasta `img/` se ela gerar imagens separadas).

---

## --- INÍCIO ---

Você é um desenvolvedor front-end sênior. Crie **uma landing page completa em um único arquivo HTML** (`index.html`), em **português do Brasil**, pronta para hospedagem estática (UOL Host / Apache). **Sem React, sem build, sem npm** — só HTML + CSS + JavaScript vanilla.

### Marca e posicionamento

- **Nome:** EGO-AI  
- **Conceito central (marketing):** *"O amigo que não te abandona"* — companheiro digital com voz e rosto, acolhedor, **não** corporativo, **não** robô de fábrica.  
- **Tagline secundária:** *Chega de telas frias.*  
- **Personas:** **Luna** (mulher, voz acolhedora) e **Leo** (homem, voz calma) — dois assistentes fixos com avatar; o usuário escolhe um.  
- **Aviso visível (rodapé e seção legal):** *Não substitui acompanhamento médico, psicológico ou de emergência.*

### Identidade visual

- Fundo: `#09090B`  
- Cards: `#141416`  
- Bordas: `#27272A`  
- Primária: `#A78BFA` / gradiente com `#7C3AED`  
- Texto: `#FAFAFA` · Muted: `#A1A1AA` · Sucesso: `#22C55E`  
- Fonte: **DM Sans** (Google Fonts)  
- Estilo: dark mode premium, mobile-first, cantos arredondados, sombra roxa suave nos CTAs  
- **Hero:** área para banner 16:9 com `<img src="img/hero-banner.png" alt="...">` (se a imagem não existir, mostrar placeholder elegante com gradiente roxo, sem quebrar o layout)

### Estrutura da página (uma página só, menu com âncoras)

Header fixo com logo texto **EGO-AI** (EGO em branco, -AI em roxo) e links: Início · Por quê · Planos · Baixar · Regras · Contato

1. **#inicio — Hero**  
   - Badge: `Conexão · Alívio · Produtividade`  
   - H1: **O amigo que não te abandona.**  
   - Subtítulo: Luna e Leo — assistente com voz, rosto e rotina no bolso. Comece grátis.  
   - CTAs: `Baixar grátis` (#baixar) e `Ver planos` (#planos)  
   - Dois cards lado a lado: Luna e Leo (use placeholders circulares com iniciais ou URLs `img/avatar-luna.png` e `img/avatar-leo.png`)

2. **#porque — Por que o EGO-AI**  
   Três pilares com ícone:  
   - Te escuta de verdade (texto + voz)  
   - Organiza sua rotina (hábitos e lembretes)  
   - Uso transparente (percentagem tipo bateria, sem jargão de tokens)

3. **#comparativo — Tabela**  
   EGO-AI vs “outros apps de IA”: personalidade fixa, voz PT, agenda integrada, preço em R$, plano grátis, uso em %

4. **#planos — Preços (BRL/mês)**  
   | Plano | Preço | Resumo |  
   | EGO Essencial | Grátis | Conhecer Luna/Leo |  
   | EGO Conexão | R$ 29,90 | Dia a dia |  
   | EGO Premium | R$ 49,90 | Destaque “mais popular” |  
   | EGO Total | R$ 99,90 | Uso intenso |  
   Botões assinar (abrir nova aba):  
   - Conexão: `https://buy.stripe.com/5kQ6oJfeC3mWeq4cJA4ow00`  
   - Premium: `https://buy.stripe.com/14A7sNgiG6z8chWgZQ4ow02`  
   - Total: `https://buy.stripe.com/5kQeVf6I60aK95K6lc4ow03`  
   Nota: impostos podem aparecer como +5% no checkout Stripe.

5. **#baixar**  
   - Botão Google Play: `href="#"` com id `btn-play-store` (comentário HTML: substituir pelo link real)  
   - App Store: “Em breve” (desabilitado visualmente)

6. **#legal — Bloco “Informações legais”** (texto legível, não só link externo)  
   Subseções com ids para Play Store:  
   - **#contato** — suporte: **contato@egoai.com.br**  
   - **#termos** — Termos de Uso completos: aceitação; serviço com IA (Google Gemini); não é conselho médico/jurídico; idade mínima 16 anos; uso proibido; conteúdo do usuário; planos Stripe; limitação de responsabilidade; alterações; LGPD/RGPD mencionados  
   - **#privacidade** — Política de Privacidade completa: dados tratados (conta, conversas, logs, Stripe); finalidades; subencarregados/IA na nuvem; conservação; direitos do titular; segurança; menores; contacto  
   - **#reembolso** — Reembolso plano pago: 7 dias corridos na primeira cobrança; pedido por e-mail contato@egoai.com.br; exclusões (fraude, após 7 dias)

7. **Rodapé**  
   © 2026 EGO-AI · egoai.com.br · Instagram @egoai.br · links âncora Privacidade · Termos · Reembolso · Contato

### Requisitos técnicos obrigatórios

- **NÃO use Tailwind CDN** (`cdn.tailwindcss.com`) — se falhar, a página fica branca.
- **NÃO use** `https://googleapis.com` — use `https://fonts.googleapis.com`
- Um arquivo só: `index.html`  
- CSS em `<style>` no `<head>` (cores de fundo `#09090B` no `body` com `!important`)  
- Imagens reais: `img/avatar-f1.png` (Luna) e `img/avatar-m1.png` (Leo) — **não use só emoji**
- `scroll-behavior: smooth` e menu que destaca seção ativa (opcional)  
- 100% responsivo (mobile primeiro; tabela comparativa com scroll horizontal no celular)  
- Meta description e title SEO  
- `lang="pt-BR"`  
- Links de privacidade para loja: âncora `#privacidade` (URL final será `https://egoai.com.br/#privacidade`)  
- Sem dependências além de Google Fonts  
- Sem texto “Lorem ipsum”  
- Código limpo e comentado onde trocar link da Play Store  

### Tom de voz do copy

Humano, brasileiro, caloroso, direto. Vender **conexão e presença**, não “tokens” nem “LLM”. Frases curtas. Evitar tom B2B frio.

### Entrega

Responda **apenas** com o código HTML completo do `index.html`, pronto para eu salvar e enviar por FTP. Não explique — só o arquivo.

## --- FIM ---

---

## Depois que a outra IA gerar

1. Salve como `index.html`  
2. Se vier imagens, crie pasta `img/` no mesmo nível  
3. Na UOL: envie para `public_html`  
4. Teste: `https://egoai.com.br/` e `https://egoai.com.br/#privacidade`  
5. Me envie o HTML ou print — eu ajusto o que faltar  

**Alternativa:** o projeto já tem `site-publico/` gerado com a mesma estrutura; este prompt serve se quiser redesign total na outra ferramenta.
