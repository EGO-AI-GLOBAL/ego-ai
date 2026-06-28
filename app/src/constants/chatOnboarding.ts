/** Guia inicial no chat — curto e direto. */

import { avatarWelcomeLine, avatarWelcomeSpeech } from "@/constants/avatarWelcome";

function greeting(userName: string | undefined, assistantName: string): string {
  const who = (userName || "").trim();
  if (!who) return `Oi! Sou ${assistantName}, seu assistente.`;
  return `Oi, ${who}! Sou ${assistantName}.`;
}

export function buildChatOnboardingMessage(
  assistantName: string,
  userName?: string,
  _isMale?: boolean,
  avatarId?: string
): string {
  const welcome = avatarWelcomeLine(avatarId, assistantName);
  return `${greeting(userName, assistantName)}

${welcome}

Escreva ou toque no microfone. Estou aqui para ouvir e acolher — como o melhor apoio emocional no bolso. Ex.: «Estou ansioso hoje» ou «Preciso desabafar».`;
}

export function buildChatOnboardingSpeech(
  assistantName: string,
  userName?: string,
  _isMale?: boolean,
  avatarId?: string
): string {
  const welcome = avatarWelcomeSpeech(avatarId, assistantName);
  return `${greeting(userName, assistantName)} ${welcome} Escreva ou fale quando quiser.`;
}
