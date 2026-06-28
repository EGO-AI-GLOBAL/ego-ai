/** Boas-vindas únicas por avatar (texto + voz curta). */

const WELCOME_BY_AVATAR: Record<string, { line: string; speech: string }> = {
  f1: {
    line: "Sou a Luna — fico aqui contigo, no seu ritmo.",
    speech: "Sou a Luna. Fico aqui contigo, no seu ritmo.",
  },
  m1: {
    line: "Sou o Leo — pode falar quando quiser, estou presente.",
    speech: "Sou o Leo. Pode falar quando quiser — estou presente.",
  },
  f2: {
    line: "Sou a Aisha — vamos por partes, com calma.",
    speech: "Sou a Aisha. Vamos por partes, com calma.",
  },
  f3: {
    line: "Sou a Hana — pode desabafar, sem filtro.",
    speech: "Sou a Hana. Pode desabafar quando quiser.",
  },
  m2: {
    line: "Sou o Kai — um passo de cada vez, eu acredito em você.",
    speech: "Sou o Kai. Um passo de cada vez — estou aqui.",
  },
  m3: {
    line: "Sou o Omar — respire comigo; não precisa ter pressa.",
    speech: "Sou o Omar. Respire comigo — sem pressa.",
  },
  f4: {
    line: "Sou a Amara — estou aqui para ouvir de coração.",
    speech: "Sou a Amara. Estou aqui para ouvir de coração.",
  },
  m4: {
    line: "Sou o Ravi — o que pesa mais agora?",
    speech: "Sou o Ravi. O que pesa mais agora?",
  },
  g1: {
    line: "Sou o Alex — conversa leve, escuta de verdade.",
    speech: "Sou o Alex. Conversa leve, escuta de verdade.",
  },
  f5: {
    line: "Sou a Sara — acolho o que você trouxer hoje.",
    speech: "Sou a Sara. Acolho o que você trouxer hoje.",
  },
  m5: {
    line: "Sou o Malik — você não está só nisto.",
    speech: "Sou o Malik. Você não está só nisto.",
  },
  g2: {
    line: "Sou o Jordan — presença calma, sem julgamento.",
    speech: "Sou o Jordan. Presença calma, sem julgamento.",
  },
};

export function avatarWelcomeLine(avatarId: string | undefined, assistantName: string): string {
  const id = (avatarId || "").trim().toLowerCase();
  return WELCOME_BY_AVATAR[id]?.line ?? `Sou ${assistantName} — estou aqui para ouvir.`;
}

export function avatarWelcomeSpeech(avatarId: string | undefined, assistantName: string): string {
  const id = (avatarId || "").trim().toLowerCase();
  return WELCOME_BY_AVATAR[id]?.speech ?? `Sou ${assistantName}. Estou aqui para ouvir.`;
}
