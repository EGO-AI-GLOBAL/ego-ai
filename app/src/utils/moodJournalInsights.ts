import type { DailyCareMoodJournalEntry } from "@/api/types";

const WEEKDAY_PT = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const MONTH_PT = [
  "jan",
  "fev",
  "mar",
  "abr",
  "mai",
  "jun",
  "jul",
  "ago",
  "set",
  "out",
  "nov",
  "dez",
];

export function formatJournalDatePt(dateIso: string): string {
  const parts = dateIso.split("-").map((x) => parseInt(x, 10));
  if (parts.length < 3 || parts.some((n) => Number.isNaN(n))) {
    return dateIso;
  }
  const dt = new Date(parts[0], parts[1] - 1, parts[2]);
  const wd = WEEKDAY_PT[dt.getDay()] ?? "";
  const day = parts[2];
  const mon = MONTH_PT[parts[1] - 1] ?? "";
  return `${wd}, ${day} ${mon}`;
}

export function moodJournalTopLabel(entries: DailyCareMoodJournalEntry[], maxDays: number): string {
  const slice = entries.slice(0, maxDays);
  if (!slice.length) return "";
  const counts: Record<string, number> = {};
  for (const e of slice) {
    const k = (e.label || e.mood || "").trim();
    if (!k) continue;
    counts[k] = (counts[k] ?? 0) + 1;
  }
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
  return top ? `${top[1]}× ${top[0]}` : "";
}

export function buildMoodJournalChatDraft(entries: DailyCareMoodJournalEntry[]): string {
  const week = entries.slice(0, 7);
  if (!week.length) {
    return "Quero falar sobre como tenho me sentido ultimamente.";
  }
  const lines = week
    .map((e) => `${formatJournalDatePt(e.date)}: ${e.emoji} ${e.label || e.mood}`)
    .join("\n");
  return `Quero desabafar sobre meu humor esta semana:\n${lines}`;
}
