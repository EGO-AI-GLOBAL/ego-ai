/** Rituais diários — 7h amanhã revelado, 8h briefing, 14h checkpoint, 21h descarrego. */

export type DailyRitualId = "reveal" | "morning" | "afternoon" | "evening";

export const DAILY_RITUAL_HOURS: Record<DailyRitualId, number> = {
  reveal: 7,
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
    case "reveal":
      return (
        `[Ritual 7h — amanhã revelado] Sou ${assistantName}. ` +
        `Diga que itens do desabafo da noite estão na Agenda para confirmar (Agendar / Excluir). ` +
        `Peça para ABRIR a Agenda AGORA e revisar cada item — leva menos de 1 minuto. ` +
        `Tom acolhedor: «Bom dia! Vamos confirmar juntos o que você desabafou ontem?»`
      );
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
        `Peça para eu SEGURAR o microfone e desabafar tudo que está na cabeça (compromissos de amanhã, mercado, remédios). ` +
        `Explique que amanhã de manhã abro a Agenda e confirmo cada item — nada entra sozinho. ` +
        `Tom calmo e acolhedor: «Solte agora, durma leve. Amanhã organizamos juntos na Agenda.» ` +
        `Não peça para marcar manualmente hoje — o fluxo é gravar agora e confirmar de manhã.`
      );
  }
}

/** Texto da notificação push — tem que puxar para abrir o app e fazer algo. */
export function ritualNotificationCopy(
  ritual: DailyRitualId,
  assistantName: string,
  userName?: string,
  streakCurrent?: number,
  nightDumpStreak?: number
): { title: string; body: string } {
  const name = userName?.trim() || "você";
  switch (ritual) {
    case "reveal": {
      const nights = nightDumpStreak ?? 0;
      if (nights >= 3) {
        return {
          title: "🌙 Amanhã revelado",
          body: `🔥 ${nights} noites de desabafo! Toque — confirme na Agenda o que guardou ontem.`,
        };
      }
      return {
        title: "🌙 Amanhã revelado",
        body: `${assistantName}: bom dia! Abra a Agenda e confirme o desabafo de ontem.`,
      };
    }
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
    case "evening": {
      const nights = nightDumpStreak ?? 0;
      const streak = streakCurrent ?? 0;
      if (nights >= 3) {
        return {
          title: `🌙 ${nights} noites de desabafo`,
          body: `${assistantName}: grave agora — amanhã você confirma na Agenda. Não quebre a sequência!`,
        };
      }
      if (streak >= 3) {
        return {
          title: `🔥 ${streak} dias seguidos!`,
          body: `Ei, você já está com ${streak} dias de organização! Não vai deixar a peteca cair hoje, né? ${assistantName}: grave um áudio rápido.`,
        };
      }
      return {
        title: "Desabafo da noite",
        body: `${assistantName}: toque, grave o que está na cabeça. Amanhã confirma na Agenda.`,
      };
    }
  }
}
