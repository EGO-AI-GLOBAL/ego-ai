import { Linking } from "react-native";

function toGoogleDates(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  const y = d.getUTCFullYear();
  const m = pad(d.getUTCMonth() + 1);
  const day = pad(d.getUTCDate());
  const h = pad(d.getUTCHours());
  const min = pad(d.getUTCMinutes());
  const start = `${y}${m}${day}T${h}${min}00Z`;
  const endMs = d.getTime() + 60 * 60 * 1000;
  const e = new Date(endMs);
  const end = `${e.getUTCFullYear()}${pad(e.getUTCMonth() + 1)}${pad(e.getUTCDate())}T${pad(e.getUTCHours())}${pad(e.getUTCMinutes())}00Z`;
  return `${start}/${end}`;
}

export function googleCalendarUrl(title: string, scheduledAt: string, details?: string): string {
  const dates = toGoogleDates(scheduledAt);
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: title || "Compromisso",
  });
  if (dates) params.set("dates", dates);
  if (details) params.set("details", details);
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

export async function openGoogleCalendar(opts: {
  title: string;
  scheduledAt: string;
  calendarName?: string;
}): Promise<void> {
  const details = opts.calendarName
    ? `Agenda compartilhada: ${opts.calendarName}`
    : undefined;
  const url = googleCalendarUrl(opts.title, opts.scheduledAt, details);
  await Linking.openURL(url);
}
