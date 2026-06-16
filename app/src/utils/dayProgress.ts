import type { DashboardData } from "@/api/types";
import type { UpcomingItem } from "@/utils/upcomingEvents";
import { collectUpcomingItems } from "@/utils/upcomingEvents";

export type DayPeriod = "morning" | "afternoon" | "evening" | "night";

export function dayPeriodFromHour(hour = new Date().getHours()): DayPeriod {
  if (hour >= 5 && hour < 12) return "morning";
  if (hour >= 12 && hour < 18) return "afternoon";
  if (hour >= 18 && hour < 23) return "evening";
  return "night";
}

function isSameLocalDay(iso: string, ref: Date): boolean {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return false;
  return (
    d.getFullYear() === ref.getFullYear() &&
    d.getMonth() === ref.getMonth() &&
    d.getDate() === ref.getDate()
  );
}

const WEEKDAY_KEYS = ["dom", "seg", "ter", "qua", "qui", "sex", "sab"] as const;

function habitMatchesToday(dias: string | undefined, ref: Date): boolean {
  const raw = (dias || "").toLowerCase();
  if (!raw.trim()) return true;
  const key = WEEKDAY_KEYS[ref.getDay()];
  return raw.split(/[,\s]+/).some((p) => p.startsWith(key));
}

export type DayProgress = {
  period: DayPeriod;
  total: number;
  done: number;
  nextItem: UpcomingItem | null;
  emptyHint: string;
};

export function computeDayProgress(data: DashboardData, now = new Date()): DayProgress {
  const period = dayPeriodFromHour(now.getHours());
  let total = 0;
  let done = 0;

  for (const r of data.reminders ?? []) {
    const at = String(r.scheduled_at || "");
    if (!at || !isSameLocalDay(at, now)) continue;
    total += 1;
    if (r.dismissed) done += 1;
  }

  for (const cal of data.shared_calendars ?? []) {
    for (const ev of cal.events ?? []) {
      const at = String(ev.scheduled_at || "");
      if (!at || !isSameLocalDay(at, now)) continue;
      total += 1;
      if (ev.dismissed) done += 1;
    }
  }

  for (const h of data.agenda ?? []) {
    if (!habitMatchesToday(h.dias_da_semana, now)) continue;
    total += 1;
    /* hábitos não têm dismissed — contam como pendentes */
  }

  const upcoming = collectUpcomingItems(data, 8, 2);
  const nextItem =
    upcoming.find((it) => {
      if (it.kind === "agenda") return true;
      return it.scheduledAtMs >= now.getTime() - 60_000;
    }) ?? null;

  const emptyHint =
    period === "morning"
      ? "Nada marcado hoje — fale ou toque num atalho abaixo."
      : period === "afternoon"
        ? "Tarde livre por agora. Quer marcar algo?"
        : "Noite tranquila. Quer anotar algo para amanhã?";

  return { period, total, done, nextItem, emptyHint };
}

export function periodGreeting(period: DayPeriod, name?: string): string {
  const who = name?.trim() || "você";
  switch (period) {
    case "morning":
      return `Bom dia, ${who}`;
    case "afternoon":
      return `Boa tarde, ${who}`;
    case "evening":
      return `Boa noite, ${who}`;
    default:
      return `Olá, ${who}`;
  }
}
