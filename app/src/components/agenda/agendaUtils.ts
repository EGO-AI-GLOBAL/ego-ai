import type { SharedCalendarEvent } from "@/api/types";

export const AGENDA_TIME_MINUTE_INTERVAL = 30;

export function defaultDateBr(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return formatDateBr(d);
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

export function sortSharedEvents(events: SharedCalendarEvent[]) {
  return [...events].sort((a, b) => {
    const ta = a.scheduled_at ? new Date(a.scheduled_at).getTime() : 0;
    const tb = b.scheduled_at ? new Date(b.scheduled_at).getTime() : 0;
    return ta - tb;
  });
}
