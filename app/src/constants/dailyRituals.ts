/** Rituais diários — 7h amanhã revelado, 8h briefing, 14h checkpoint, 21h descarrego. */

import { avatarRitualHook, avatarOfDaySuggestion } from "@/constants/avatarRituals";

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
export function ritualChatPrompt(
  ritual: DailyRitualId,
  assistantName: string,
  avatarId?: string
): string {
  const hookFor = (slot: "morning" | "afternoon" | "evening") =>
    avatarRitualHook(slot, avatarId, assistantName);

  switch (ritual) {
    case "reveal":
      return (
        `[Ritual 7h — amanhã revelado] Sou ${assistantName}. ` +
        `Bom dia acolhedor. Se houve desabafo ontem, lembre em UMA frase que os itens ficam na Agenda ` +
        `para o utilizador confirmar manualmente — você NÃO marca nada. ` +
        `${hookFor("morning")}`
      );
    case "morning":
      return (
        `[Ritual 8h — briefing] Sou ${assistantName}. ` +
        `${hookFor("morning")} ` +
        `Se mencionarem compromissos, escute — NÃO ofereça agendar. ` +
        `Foco: presença e escuta clínica, 3–5 frases.`
      );
    case "afternoon":
      return (
        `[Ritual 14h — checkpoint] Sou ${assistantName}. ` +
        `${hookFor("afternoon")} ` +
        `Valide cansaço ou ansiedade. NÃO empurre agenda. Tom parceiro, frases curtas.`
      );
    case "evening":
      return (
        `[Ritual 21h — descarrego] Sou ${assistantName}. ` +
        `${hookFor("evening")} ` +
        `NÃO peça para marcar nada hoje. Tom calmo: «Solte agora, estou aqui.»`
      );
  }
}

/** Texto da notificação push — tem que puxar para abrir o app e fazer algo. */
export function ritualNotificationCopy(
  ritual: DailyRitualId,
  assistantName: string,
  userName?: string,
  streakCurrent?: number,
  nightDumpStreak?: number,
  avatarOfDay?: { avatar_id: string; shortName: string }
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
    case "morning": {
      if (avatarOfDay) {
        const day = avatarOfDaySuggestion(avatarOfDay.avatar_id, avatarOfDay.shortName, "morning");
        return {
          title: day.title,
          body: `${day.body} Quer falar com ${avatarOfDay.shortName}?`,
        };
      }
      return {
        title: `${name}, como você está? ☀️`,
        body: `${assistantName}: toque — um momento de escuta para começar o dia.`,
      };
    }
    case "afternoon":
      return {
        title: "Como está a tarde por dentro?",
        body: `${assistantName}: toque — checkpoint emocional, estou aqui.`,
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
          body: `Ei, você já está com ${streak} dias! ${assistantName}: desabafe um pouco agora.`,
        };
      }
      return {
        title: "Desabafo da noite",
        body: `${assistantName}: toque e desabafe — estou aqui para ouvir.`,
      };
    }
  }
}
