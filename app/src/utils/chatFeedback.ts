import type { SendChatResult } from "@/api/types";

export function chatShouldSkipNotificationRefresh(result: SendChatResult): boolean {
  if (
    result.shared_events_saved?.length ||
    result.shared_calendars_saved?.length ||
    result.shared_members_saved?.length ||
    result.reminders_saved?.length ||
    result.agenda_saved?.length
  ) {
    return true;
  }
  const notice = chatSavedNotice(result);
  return Boolean(notice && /lembrete|agenda/i.test(notice));
}

/** @deprecated use chatShouldSkipNotificationRefresh */
export function chatChangedSharedCalendar(result: SendChatResult): boolean {
  return chatShouldSkipNotificationRefresh(result);
}

export function chatSavedNotice(result: SendChatResult): string | null {
  const parts: string[] = [];
  for (const ev of result.shared_events_saved || []) {
    const title = ev.title || "Compromisso";
    parts.push(`Agenda: ${title}`);
  }
  for (const cal of result.shared_calendars_saved || []) {
    const name = cal.name || "Agenda";
    parts.push(`Agenda criada: ${name}`);
  }
  for (const a of result.agenda_saved || []) {
    const hor = String(a.horario || "").slice(0, 5);
    parts.push(`Agenda: ${a.titulo || "Compromisso"} ${hor} (${a.dias_da_semana})`);
  }
  for (const r of result.reminders_saved || []) {
    parts.push(`Lembrete: ${r.title || "Lembrete"}`);
  }
  return parts.length ? parts.join(" · ") : null;
}

export function chatWarnings(result: SendChatResult): string | null {
  const w = result.warnings?.filter(Boolean) || [];
  if (w.length) return w.join(" ");
  const reply = (result.reply || "").trim();
  if (/não consegui|não foi possível|não confirm/i.test(reply)) {
    return reply;
  }
  return null;
}
