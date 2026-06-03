import type { SendChatResult } from "@/api/types";

export function chatSavedNotice(result: SendChatResult): string | null {
  const parts: string[] = [];
  for (const a of result.agenda_saved || []) {
    const hor = String(a.horario || "").slice(0, 5);
    parts.push(`Agenda: ${a.titulo || "Compromisso"} ${hor} (${a.dias_da_semana})`);
  }
  for (const r of result.reminders_saved || []) {
    parts.push(`Lembrete: ${r.title || "Lembrete"}`);
  }
  for (const c of result.shared_calendars_saved || []) {
    parts.push(`Agenda compartilhada: ${c.name || "Nova agenda"}`);
  }
  for (const ev of result.shared_events_saved || []) {
    parts.push(`Compartilhada: ${ev.title || "Compromisso"}`);
  }
  return parts.length ? parts.join(" · ") : null;
}

export function chatWarnings(result: SendChatResult): string | null {
  const w = result.warnings?.filter(Boolean) || [];
  return w.length ? w.join(" ") : null;
}
