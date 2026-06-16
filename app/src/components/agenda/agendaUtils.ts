import type { Reminder, SharedCalendarEvent } from "@/api/types";

export const AGENDA_TIME_MINUTE_INTERVAL = 30;

export const WEEKDAY_KEYS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"] as const;
export const WEEKDAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

export function todayDateBr(): string {
  return formatDateBr(new Date());
}

export function tomorrowDateBr(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return formatDateBr(d);
}

/** @deprecated Prefer defaultScheduleSlot() — mantido para compatibilidade. */
export function defaultDateBr(): string {
  return tomorrowDateBr();
}

/** Próximo slot de 30 min — padrão de apps de calendário modernos. */
export function defaultScheduleSlot(): { date: string; time: string } {
  const now = new Date();
  const slot = new Date(now);
  const remainder = slot.getMinutes() % AGENDA_TIME_MINUTE_INTERVAL;
  const addMin =
    remainder === 0 ? AGENDA_TIME_MINUTE_INTERVAL : AGENDA_TIME_MINUTE_INTERVAL - remainder;
  slot.setMinutes(slot.getMinutes() + addMin, 0, 0);
  return { date: formatDateBr(slot), time: formatTimeHm(slot) };
}

export function formatDateFriendly(dateBr: string): string {
  const parsed = parseDateBr(dateBr);
  if (!parsed) return dateBr || "Data";
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  const target = new Date(parsed);
  target.setHours(12, 0, 0, 0);
  const diffDays = Math.round((target.getTime() - today.getTime()) / 86_400_000);
  if (diffDays === 0) return `Hoje · ${dateBr}`;
  if (diffDays === 1) return `Amanhã · ${dateBr}`;
  const weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
  return `${weekdays[target.getDay()]} · ${dateBr}`;
}

export function toggleWeekdayCsv(current: string, key: string): string {
  const set = new Set(
    current
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean)
  );
  const k = key.toLowerCase();
  if (set.has(k)) set.delete(k);
  else set.add(k);
  return WEEKDAY_KEYS.filter((d) => set.has(d)).join(",");
}

export function defaultTimeHm(hour = 10, minute = 0): string {
  const d = new Date();
  d.setHours(hour, snapMinute(minute, AGENDA_TIME_MINUTE_INTERVAL), 0, 0);
  return formatTimeHm(d);
}

export function parseDateBr(value: string): Date | null {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value.trim());
  if (!m) return null;
  const day = Number(m[1]);
  const month = Number(m[2]);
  const year = Number(m[3]);
  const d = new Date(year, month - 1, day, 12, 0, 0, 0);
  if (d.getFullYear() !== year || d.getMonth() !== month - 1 || d.getDate() !== day) {
    return null;
  }
  return d;
}

export function parseTimeHm(value: string): { hour: number; minute: number } | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(value.trim());
  if (!m) return null;
  const hour = Number(m[1]);
  const minute = Number(m[2]);
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null;
  return { hour, minute };
}

export function formatDateBr(date: Date): string {
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${day}/${month}/${date.getFullYear()}`;
}

export function formatTimeHm(date: Date): string {
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  return `${hour}:${minute}`;
}

export function snapMinute(minute: number, interval: number): number {
  const step = Math.max(1, interval);
  const snapped = Math.round(minute / step) * step;
  return snapped === 60 ? 0 : snapped;
}

export function combineDateAndTime(dateBr: string, timeHm: string): Date {
  const base = parseDateBr(dateBr) ?? new Date();
  const t = parseTimeHm(timeHm);
  const hour = t?.hour ?? 10;
  const minute = snapMinute(t?.minute ?? 0, AGENDA_TIME_MINUTE_INTERVAL);
  const d = new Date(base);
  d.setHours(hour, minute, 0, 0);
  return d;
}

/** Alinhado à agenda pessoal: compromissos passados deixam de aparecer na lista. */
export const AGENDA_PAST_GRACE_MS = 60_000;

export function isScheduledStillVisible(
  scheduledAt?: string | null,
  nowMs = Date.now()
): boolean {
  if (!scheduledAt) return false;
  const ms = new Date(scheduledAt).getTime();
  return !Number.isNaN(ms) && ms >= nowMs - AGENDA_PAST_GRACE_MS;
}

export function filterVisibleReminders(reminders: Reminder[]) {
  return reminders.filter((r) => !r.dismissed && isScheduledStillVisible(r.scheduled_at));
}

export function filterVisibleSharedEvents(events: SharedCalendarEvent[]) {
  return events.filter((ev) => !ev.dismissed && isScheduledStillVisible(ev.scheduled_at));
}

export function sortSharedEvents(events: SharedCalendarEvent[]) {
  return [...events].sort((a, b) => {
    const ta = a.scheduled_at ? new Date(a.scheduled_at).getTime() : 0;
    const tb = b.scheduled_at ? new Date(b.scheduled_at).getTime() : 0;
    return ta - tb;
  });
}
