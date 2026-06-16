/** Guia inicial no chat — curto e direto. */



function greeting(userName: string | undefined, assistantName: string): string {

  const who = (userName || "").trim();

  if (!who) return `Oi! Sou ${assistantName}, seu assistente.`;

  return `Oi, ${who}! Sou ${assistantName}.`;

}



export function buildChatOnboardingMessage(

  assistantName: string,

  userName?: string,

  _isMale?: boolean

): string {

  return `${greeting(userName, assistantName)}



Escreva ou toque no microfone. Posso ouvir, acolher e te ensinar o app — agenda, convites, avatares e mais. Ex.: «Como marco um compromisso?» ou «Como convido alguém?»`;

}



export function buildChatOnboardingSpeech(

  assistantName: string,

  userName?: string,

  _isMale?: boolean

): string {

  return `${greeting(userName, assistantName)} Escreva ou fale quando quiser — estou aqui para conversar e te mostrar como usar o EGO-AI.`;

}


