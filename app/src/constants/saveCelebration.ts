import type { SendChatResult } from "@/api/types";

export function chatResultHasScheduleSave(result: SendChatResult): boolean {
  return Boolean(
    (result.reminders_saved?.length ?? 0) > 0 ||
      (result.shared_events_saved?.length ?? 0) > 0 ||
      (result.agenda_saved?.length ?? 0) > 0
  );
}

export function buildSaveCelebrationLine(
  assistantName: string,
  result: SendChatResult
): string | null {
  const rem = result.reminders_saved?.[0];
  if (rem) {
    const title = (rem.title || "Lembrete").trim();
    let when = "";
    try {
      when = new Date(String(rem.scheduled_at)).toLocaleString("pt-BR", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      /* keep */
    }
    return when
      ? `${assistantName}: fechado! Te aviso em ${when} — «${title}».`
      : `${assistantName}: fechado! «${title}» está na sua agenda.`;
  }
  const ev = result.shared_events_saved?.[0];
  if (ev) {
    const title = (ev.title || "Compromisso").trim();
    return `${assistantName}: marcado! «${title}» está na agenda.`;
  }
  const habit = result.agenda_saved?.[0];
  if (habit) {
    const title = (habit.titulo || "Hábito").trim();
    return `${assistantName}: hábito «${title}» registrado. Conte comigo!`;
  }
  return null;
}

export function buildSaveCelebrationSpeech(assistantName: string, result: SendChatResult): string | null {
  const line = buildSaveCelebrationLine(assistantName, result);
  if (!line) return null;
  return line.replace(`${assistantName}: `, "");
}
