import type { StreakInfo } from "@/api/types";

/** Frase da Luna/Leo no avatar conforme a sequência de desabafo (sem partilha no chat). */
export function streakAvatarSubtitle(
  streak: StreakInfo | undefined,
  assistantName: string
): string | null {
  const current = streak?.current ?? 0;
  if (current < 1) return null;
  const atRisk = streak?.at_risk && !streak?.active_today;
  if (atRisk) {
    return `${assistantName}: sequência em risco — 1 áudio salva o dia`;
  }
  if (current >= 14) {
    return `${assistantName}: ${current} dias juntos — não para agora!`;
  }
  if (current >= 7) {
    return `${assistantName}: ${current} dias seguidos — orgulho de você`;
  }
  if (current >= 3) {
    return `${assistantName}: ${current} dias seguidos — vamos manter?`;
  }
  return `${assistantName}: dia ${current} da sequência`;
}

export function streakShareHeadline(current: number, atRisk: boolean): string {
  if (atRisk) return "Sequência em risco hoje";
  if (current === 1) return "1 dia organizado";
  return `${current} dias organizados`;
}

export function streakShareTagline(atRisk: boolean): string {
  if (atRisk) return "Grave 1 desabafo e salve a sequência";
  return "Desabafo → Agenda · EGO-AI";
}
