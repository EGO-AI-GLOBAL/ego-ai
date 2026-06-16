/** Guia inicial no chat — curto, humano, com gancho para o primeiro lembrete. */

function greeting(userName: string | undefined, assistantName: string): string {
  const who = (userName || "").trim();
  if (!who) return `Oi! Sou ${assistantName}.`;
  return `Oi, ${who}! Sou ${assistantName}.`;
}

export function buildChatOnboardingMessage(
  assistantName: string,
  userName?: string,
  isMale?: boolean
): string {
  const head = greeting(userName, assistantName);
  const hook = isMale
    ? "Me diz uma coisa: o que você não pode esquecer amanhã? Eu marco e te aviso."
    : "Me conta: tem algo importante amanhã que eu possa lembrar você?";

  return `${head}

${hook}

Pode escrever, usar os atalhos em baixo ou tocar no microfone e falar.

Exemplo: «Lembrar pagar luz dia 10 às 9h» ou «Marcar reunião amanhã 15h».`;
}

export function buildChatOnboardingSpeech(
  assistantName: string,
  userName?: string,
  isMale?: boolean
): string {
  const head = greeting(userName, assistantName);
  const hook = isMale
    ? "O que você não pode esquecer amanhã? Eu organizo e te aviso."
    : "Tem algo importante amanhã? Me conta que eu lembro você.";

  return `${head} ${hook} Pode falar ou escrever quando quiser.`;
}
