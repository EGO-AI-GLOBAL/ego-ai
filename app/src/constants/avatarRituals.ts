/**
 * Rituais por avatar — mesmo horário, convite diferente por persona.
 */

const MORNING: Record<string, string> = {
  f1: "Como você acordou por dentro hoje? Quer desabafar um pouco?",
  m1: "Checkpoint directo: como está a energia agora?",
  m2: "Bom dia — o que você quer celebrar ou aliviar hoje?",
  m3: "60 segundos de presença: o que sente no corpo ao acordar?",
  f4: "Bom dia acolhedor — uma gratidão pequena ou um peso, o que vier.",
  m4: "Vamos por partes: o que mais ocupa a mente neste início de dia?",
  g1: "E aí — como tá por dentro hoje?",
  f5: "Início de dia: o que você precisa ser ouvido(a) agora?",
  m5: "Levantou — o que te dá força ou te pesa nesta manhã?",
  g2: "Ancoragem suave: três coisas que você nota agora (som, ar, corpo).",
};

const AFTERNOON: Record<string, string> = {
  f1: "Checkpoint da tarde — como está o coração neste meio do dia?",
  m1: "Meio do dia: o que drenou ou sustentou você?",
  m2: "Metade do dia — onde você merece um respiro?",
  m3: "Pausa calma: o que a tarde trouxe para dentro?",
  f4: "Tarde acolhedora — valido o cansaço se vier.",
  m4: "Checkpoint: uma coisa que foi bem e uma que pesa.",
  g1: "Como tá a tarde por dentro?",
  f5: "Tarde: o que precisa de escuta agora?",
  m5: "Você aguentou até aqui — o que soltar um pouco?",
  g2: "Respire comigo: o que mudou desde a manhã?",
};

const EVENING: Record<string, string> = {
  f1: "Desabafo da noite — solte o que pesou; estou aqui.",
  m1: "Fim do dia: o que ficou guardado que quer soltar?",
  m2: "Noite — celebre um momento pequeno ou desabafe o que sobrou.",
  m3: "Ancoragem noturna: o que você solta antes de dormir?",
  f4: "Noite gentil — gratidão ou cansaço, os dois cabem.",
  m4: "Fecho do dia: uma frase sobre como foi por dentro.",
  g1: "Noite — desabafa no seu tempo.",
  f5: "Antes de dormir: o que ainda ecoa?",
  m5: "Você chegou ao fim do dia — o que quer deixar ir?",
  g2: "Desabafo calmo — amanhã você confirma na Agenda, hoje só escuta.",
};

function pick(map: Record<string, string>, avatarId: string, fallback: string): string {
  return map[avatarId] ?? fallback;
}

export function avatarRitualHook(
  ritual: "morning" | "afternoon" | "evening",
  avatarId: string | undefined,
  assistantName: string
): string {
  const id = (avatarId || "f1").trim().toLowerCase();
  switch (ritual) {
    case "morning":
      return pick(MORNING, id, `${assistantName}: como você está nesta manhã?`);
    case "afternoon":
      return pick(AFTERNOON, id, `${assistantName}: checkpoint emocional da tarde.`);
    case "evening":
      return pick(EVENING, id, `${assistantName}: desabafo da noite — estou aqui.`);
  }
}

export function avatarOfDaySuggestion(
  avatarId: string,
  shortName: string,
  ritual: "morning" | "afternoon" | "evening" = "morning"
): { title: string; body: string } {
  const hook = avatarRitualHook(ritual, avatarId, shortName);
  return {
    title: `Hoje: ${shortName} sugere`,
    body: hook,
  };
}
