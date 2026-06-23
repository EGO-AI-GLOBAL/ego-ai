import type { AgendaItem, DashboardData, Reminder, SharedCalendar } from "@/api/types";

export type UpcomingItem = {
  id: string;
  kind: "shared" | "reminder" | "agenda";
  title: string;
  whenLabel: string;
  calendarName?: string;
  scheduledAtMs: number;
};

function formatWhen(isoOrTime: string, dias?: string): string {
  if (/^\d{1,2}:\d{2}/.test(isoOrTime) && dias) {
    return `${dias} · ${isoOrTime.slice(0, 5)}`;
  }
  try {
    const d = new Date(isoOrTime);
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleString("pt-BR", {
        weekday: "short",
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    }
  } catch {
    /* ignore */
  }
  return isoOrTime || "";
}

export function collectUpcomingItems(
  data: DashboardData,
  limit = 5,
  horizonDays = 14
): UpcomingItem[] {
  const now = Date.now();
  const horizon = now + horizonDays * 24 * 60 * 60 * 1000;
  const items: UpcomingItem[] = [];

  for (const cal of data.shared_calendars ?? []) {
    const calName = (cal.name || "Agenda").trim();
    for (const ev of cal.events ?? []) {
      if (ev.dismissed) continue;
      const ms = new Date(String(ev.scheduled_at || "")).getTime();
      if (!ms || Number.isNaN(ms) || ms < now - 60_000 || ms > horizon) continue;
      items.push({
        id: `sc-${ev.id}`,
        kind: "shared",
        title: (ev.title || "Compromisso").trim(),
        whenLabel: formatWhen(String(ev.scheduled_at || "")),
        calendarName: calName,
        scheduledAtMs: ms,
      });
    }
  }

  for (const r of data.reminders ?? []) {
    if (r.dismissed) continue;
    const ms = new Date(String(r.scheduled_at || "")).getTime();
    if (!ms || Number.isNaN(ms) || ms < now - 60_000 || ms > horizon) continue;
    items.push({
      id: `rem-${r.id}`,
      kind: "reminder",
      title: (r.title || "Lembrete").trim(),
      whenLabel: formatWhen(String(r.scheduled_at || "")),
      scheduledAtMs: ms,
    });
  }

  for (const a of data.agenda ?? []) {
    items.push({
      id: `ag-${a.id}`,
      kind: "agenda",
      title: (a.titulo || "Hábito").trim(),
      whenLabel: formatWhen(String(a.horario || ""), a.dias_da_semana),
      scheduledAtMs: now + 86_400_000,
    });
  }

  items.sort((a, b) => a.scheduledAtMs - b.scheduledAtMs);
  return items.slice(0, limit);
}

export function defaultCalendarName(calendars: SharedCalendar[]): string {
  const first = calendars[0]?.name?.trim();
  return first || "Entre Nós";
}
