/** Guia inicial no chat — escrito + versão curta para voz (TTS). */

function greeting(userName: string | undefined, assistantName: string): string {
  const who = (userName || "").trim();
  if (!who) return `Olá! Sou ${assistantName}, seu assistente no EGO-AI.`;
  return `Olá, ${who}! Sou ${assistantName}, seu assistente no EGO-AI.`;
}

/** Texto completo no chat (a pessoa lê no ecrã). */
export function buildChatOnboardingMessage(
  assistantName: string,
  userName?: string
): string {
  const head = greeting(userName, assistantName);

  return `${head}

(A apresentação em voz começa em instantes — pode ler abaixo enquanto ouve.)

O que posso fazer por você:

• Marcar — compromissos na agenda partilhada (diga agenda, dia e hora)
• Lembrar — lembretes no telefone
• Convidar — pessoa por telefone ou e-mail na agenda
• Resumo — ver compromissos da semana

Como usar (é simples):

1. Toque nos botões Marcar, Lembrar… acima da mensagem (envio na hora)
2. Ou escreva o que precisa na caixa de texto
3. Microfone — fale e toque na seta para enviar
4. Doc — anexar PDF ou foto

Menu ☰ (lateral): Agendas partilhadas, Planos, Conta.

Exemplos:
«Marcar reunião amanhã 15h na agenda Família»
«Lembrar pagar luz dia 10 às 9h»

Pergunte o que quiser — estou aqui para ajudar.`;
}

/** Versão falada (mais curta — apresentação por voz). */
export function buildChatOnboardingSpeech(
  assistantName: string,
  userName?: string
): string {
  const head = greeting(userName, assistantName);

  return (
    `${head} ` +
    "Posso marcar compromissos na agenda partilhada, criar lembretes, " +
    "convidar pessoas por telefone ou e-mail, e resumir a sua semana. " +
    "Use os botões Marcar e Lembrar em baixo, escreva na caixa de mensagem, " +
    "ou fale pelo microfone. No menu lateral estão as agendas e os planos. " +
    "Por exemplo, diga: marcar reunião amanhã às três da tarde. " +
    "Estou aqui para ajudar!"
  );
}
