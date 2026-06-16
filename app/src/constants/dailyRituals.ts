/** Rituais diários — 8h briefing, 14h checkpoint, 21h descarrego. */

export type DailyRitualId = "morning" | "afternoon" | "evening";

export const DAILY_RITUAL_HOURS: Record<DailyRitualId, number> = {
  morning: 8,
  afternoon: 14,
  evening: 21,
};

export const LEGACY_WELLNESS_HOURS = [8, 12, 16, 20] as const;

export function ritualNotificationId(ritual: DailyRitualId): string {
  return `ego-daily-ritual-${ritual}`;
}

export function ritualChatPrompt(ritual: DailyRitualId, assistantName: string): string {
  switch (ritual) {
    case "morning":
      return (
        `Briefing de café: resumo da minha agenda de hoje em tópicos curtos e tom acolhedor, ` +
        `como ${assistantName} numa conversa de manhã. No fim, pergunte se quero marcar ou lembrar algo.`
      );
    case "afternoon":
      return (
        `Ponto de controle da tarde: liste o que ainda tenho hoje e pergunte se já fiz os compromissos ` +
        `da tarde. Se eu confirmar que fiz, ajude a marcar como concluído ou atualizar a agenda.`
      );
    case "evening":
      return (
        `Descarrego da noite: ajude-me a tirar os planos da cabeça antes de dormir. ` +
        `Pergunte o que tenho para amanhã e ofereça criar lembretes. Tom calmo e breve.`
      );
  }
}

export function ritualNotificationCopy(
  ritual: DailyRitualId,
  assistantName: string,
  userName?: string
): { title: string; body: string } {
  const name = userName?.trim() || "você";
  switch (ritual) {
    case "morning":
      return {
        title: `Bom dia, ${name}!`,
        body: `${assistantName} preparou o resumo do seu dia. Toque para ouvir.`,
      };
    case "afternoon":
      return {
        title: "Metade do dia!",
        body: `${assistantName}: como foi sua tarde? Atualize a agenda em um toque.`,
      };
    case "evening":
      return {
        title: "Hora de descansar a mente",
        body: `${assistantName}: conte o que tem para amanhã e durma mais leve.`,
      };
  }
}
