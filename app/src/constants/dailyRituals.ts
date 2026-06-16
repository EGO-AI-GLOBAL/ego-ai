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

/** Prompt enviado ao chat quando o utilizador toca na notificação. */
export function ritualChatPrompt(ritual: DailyRitualId, assistantName: string): string {
  switch (ritual) {
    case "morning":
      return (
        `[Ritual 8h — briefing] Sou ${assistantName}. ` +
        `Resuma em tópicos curtos o que tenho HOJE na agenda. ` +
        `Depois pergunte o que falta marcar e peça para eu ABRIR a aba Agenda AGORA, ` +
        `tocar «+ Novo compromisso» e marcar cada coisa que ainda não está lá. ` +
        `Seja direto e acolhedor — quero sair deste chat e ir marcar. ` +
        `Termine com: «Vai na Agenda agora — leva 10 segundos. Volta aqui quando terminar.»`
      );
    case "afternoon":
      return (
        `[Ritual 14h — checkpoint] Sou ${assistantName}. ` +
        `Liste o que ainda tenho HOJE e pergunte o que já fiz. ` +
        `Se faltar algo na agenda ou no dia, peça para eu ABRIR a Agenda AGORA e marcar ou apagar o que mudou. ` +
        `Não deixe passar em branco — empurre para a ação: «Abre a Agenda e ajusta agora, antes que a tarde acabe.» ` +
        `Tom parceiro, frases curtas.`
      );
    case "evening":
      return (
        `[Ritual 21h — descarrego] Sou ${assistantName}. ` +
        `Pergunte o que tenho AMANHÃ e o que ainda está na cabeça sem estar marcado. ` +
        `Depois peça para eu ABRIR a Agenda, tocar «Amanhã» e marcar cada compromisso antes de dormir. ` +
        `Tom calmo mas firme: «Não durma com isso solto — vai na Agenda agora e marca. Depois me conta como ficou.» ` +
        `Breve e humano.`
      );
  }
}

/** Texto da notificação push — tem que puxar para abrir o app e fazer algo. */
export function ritualNotificationCopy(
  ritual: DailyRitualId,
  assistantName: string,
  userName?: string
): { title: string; body: string } {
  const name = userName?.trim() || "você";
  switch (ritual) {
    case "morning":
      return {
        title: `${name}, seu dia começa agora ☀️`,
        body: `${assistantName}: toque — veja a agenda de hoje e marque o que falta.`,
      };
    case "afternoon":
      return {
        title: "Metade do dia — não deixe escapar",
        body: `${assistantName}: abra agora, confira a tarde e atualize sua agenda.`,
      };
    case "evening":
      return {
        title: "Antes de dormir: marque amanhã",
        body: `${assistantName}: toque, descarregue a cabeça e marque na Agenda agora.`,
      };
  }
}
