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



Escreva ou toque no microfone. Estou aqui para ouvir, acolher e conversar — como o melhor apoio emocional no bolso. Ex.: «Estou ansioso hoje» ou «Preciso desabafar».`;

}



export function buildChatOnboardingSpeech(

  assistantName: string,

  userName?: string,

  _isMale?: boolean

): string {

  return `${greeting(userName, assistantName)} Escreva ou fale quando quiser — estou aqui para ouvir e acolher.`;

}


