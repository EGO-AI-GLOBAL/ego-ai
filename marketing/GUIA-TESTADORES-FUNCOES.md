# EGO-AI — O que o app faz (guia para testadores)

Versão **1.0.2** (build 19) · Teste interno Google Play  
Site: https://egoai.com.br · Suporte: contato@egoai.com.br

---

## O que é o EGO-AI

Assistente com **rosto e voz** (Luna, Leo e outros). Conversa por **texto e áudio**, ajuda na **organização** (agenda e lembretes), lê **PDFs e documentos** que você anexa, e pode **resumir** ou responder perguntas sobre o conteúdo.

Plano inicial gratuito: **EGO Essencial** (com limites diários — ver secção Planos).

---

## 1. Conta e acesso

| Função | O que testar |
|--------|----------------|
| **Cadastro** | Nome, e-mail, senha, confirmar senha, aceitar termos |
| **Login** | E-mail + senha |
| **Esqueci a senha** | Link na tela de login → e-mail de recuperação |
| **Código de indicação** (opcional) | «Tem código de indicação?» no cadastro — 10% na 1ª compra se tiver código válido |
| **Sair** | Menu lateral (☰) → **Sair** |

---

## 2. Assistentes (personas)

| Função | O que testar |
|--------|----------------|
| **Luna e Leo** | Disponíveis no plano gratuito |
| **Trocar assistente** | No **Chat**, toque no nome/avatar → escolha outro (feminino, masculino, neutro) |
| **Conta** | Menu → **Conta** → também dá para trocar assistente |
| **Outros avatares** | Alguns só desbloqueiam em planos pagos (aparece cadeado) |

---

## 3. Chat — conversa principal

Abra o menu **☰** → **Chat** (ou é a tela inicial após login).

| Função | Como usar | O que testar |
|--------|-----------|----------------|
| **Mensagem de texto** | Digite e envie | Perguntas, desabafar, pedir ideias |
| **Histórico** | Role para cima | Mensagens anteriores da sessão |
| **Microfone (voz)** | Toque e segure (ou toque para gravar/enviar conforme o app indicar) | Fale 3–10 s, veja se transcreve e responde |
| **Ouvir ao responder** | Interruptor «Ouvir ao responder» | Resposta falada automaticamente |
| **Ouvir resposta** | Botão após uma resposta | Repete o último áudio |
| **Velocidade do áudio** | 1x / 1,5x / 2x (se seu plano permitir) | Só com «Ouvir ao responder» ligado |
| **Avatar animado** | Topo da tela | Move quando fala / ouve |

**Dicas de teste no chat:**
- «Como te chamas?»
- «Ajuda-me a organizar a semana»
- «Cria um lembrete amanhã às 9h para tomar água» (pode criar item na agenda)

---

## 4. Documentos e PDF (importante)

| Função | Como usar | O que testar |
|--------|-----------|----------------|
| **Anexar ficheiro** | Ícone **Doc** (clipe/documento) ao lado da caixa de mensagem | Escolher **PDF** ou Word |
| **Resumo automático** | Após anexar, aparece faixa com tamanho do doc → **Enviar resumo** | Ou escreva: «Resume em 5 tópicos» |
| **Vários anexos** | Anexar outro PDF (acumula partes) | Contador de partes na faixa |
| **Limpar documento** | **Limpar** na faixa do PDF | Remove anexo da sessão |
| **Foto / câmera** | Doc → **Tirar foto** ou **Galeria** | Foto com texto (ex.: página, recibo) — pergunte sobre o texto |

**Teste sugerido (5 min):** PDF curto (1–3 páginas) → «Faz um resumo em 5 tópicos» → pergunta específica sobre uma parte do texto.

---

## 5. Agenda pessoal

Menu **☰** → **Agenda**

| Função | O que testar |
|--------|----------------|
| **Ver lembretes / hábitos** | Lista do que já existe |
| **Marcar compromisso** | Botão **Marcar compromisso** → **Agenda pessoal** → título, data, hora |
| **Concluir lembrete** | Marcar como feito |
| **Apagar item** | Remover da lista |
| **Pelo chat** | Pedir no chat para criar lembrete ou hábito |

Limites no plano **Essencial:** até **3 hábitos** e **3 lembretes** (se chegar ao limite, o app avisa).

---

## 6. Agendas compartilhadas (família / equipe)

**Nesta fase de teste:** a equipe EGO-AI testa primeiro **internamente**. Testadores focam em chat, voz, PDF e agenda **pessoal**.

Se quiser experimentar (opcional, com outra pessoa que **já tenha conta**):

| Função | Onde |
|--------|------|
| Criar agenda compartilhada | **Agenda** → secção compartilhadas → **Gerir agendas** |
| Convidar membro | E-mail de quem **já usa o EGO-AI** (mesma conta cadastrada) |
| Marcar evento | Dentro da agenda → título, data, hora |
| Notificações | Membros recebem aviso de novos eventos |

---

## 7. Planos e pagamento (opcional no teste)

Menu **☰** → **Planos**

| Plano | Preço (BR) | Resumo |
|-------|------------|--------|
| **Essencial** | Grátis | 10 msg texto/dia, 3 voz/dia, 3 hábitos + 3 lembretes |
| **Conexão** | R$ 29,90/mês | Mais mensagens, voz, agenda, 4 assistentes extra |
| **Premium** | R$ 49,90/mês | Texto/voz ilimitados no dia, agenda ilimitada |
| **Total** | R$ 99,90/mês | Uso intenso, todos os assistentes |
| **Equipes** | Variável | Planos para várias pessoas (Stripe) |

**Teste opcional:** abrir tela de planos e ver se abre checkout Stripe (não é obrigatório pagar para testar).

---

## 8. Uso do plano

Menu **☰** → **Uso**

- Mostra **percentagem** do consumo (mensagens, tokens, etc.) conforme seu plano.

---

## 9. Conta e perfil

Menu **☰** → **Conta**

| Função | O que testar |
|--------|----------------|
| Nome / e-mail | Dados do perfil |
| Plano atual | Essencial ou pago |
| Trocar assistente | PersonaPicker |
| Resumo de uso | Gráficos / limites |

---

## 10. Legal

No menu **☰**, secção **Legal**:

- **Privacidade**
- **Termos de uso**
- **Política de reembolso**

---

## 11. Navegação

- **Menu lateral:** toque **☰** (canto superior) em qualquer tela principal.
- **Tema:** claro/escuro conforme sistema do telemóvel.

---

## Checklist rápido (15–20 min)

Marque o que testou:

- [ ] Instalar/atualizar **1.0.2** pela Play (teste interno)
- [ ] Criar conta + login
- [ ] Escolher **Luna** ou **Leo**
- [ ] Enviar **3 mensagens de texto**
- [ ] Usar **microfone** (1 mensagem de voz)
- [ ] Ligar **Ouvir ao responder** e ouvir uma resposta
- [ ] Anexar **PDF** → **Enviar resumo** ou pedir resumo no chat
- [ ] **Agenda** → **Marcar compromisso** pessoal
- [ ] Abrir **Uso** e **Planos**
- [ ] (Opcional) Foto com texto via **Doc**

---

## Como reportar bug

Envie para quem convidou ou **contato@egoai.com.br**:

1. O que fez (passo a passo)
2. O que esperava
3. O que aconteceu
4. **Print ou vídeo curto**
5. Modelo do telemóneo + versão do app (**1.0.2**)

Obrigado por testar o EGO-AI.
