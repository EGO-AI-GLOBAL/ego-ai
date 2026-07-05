import type { PausaDailyExercise } from "@/api/types";

export const DEFAULT_DAILY_EXERCISE: PausaDailyExercise = {
  key: "breath44",
  emoji: "🌬️",
  title: "Respiração 4–4",
  subtitle: "Acalma o corpo em 1 minuto",
  duration_seconds: 60,
  mode: "breath",
  breath_inhale: 4,
  breath_exhale: 4,
};

export function resolveDailyExercise(pausa?: { daily_exercise?: PausaDailyExercise | null } | null): PausaDailyExercise {
  return pausa?.daily_exercise ?? DEFAULT_DAILY_EXERCISE;
}

export function formatPausaDuration(seconds: number): string {
  if (seconds >= 120) return "2 min";
  if (seconds >= 90) return "90s";
  if (seconds >= 60) return "1 min";
  return `${Math.max(30, seconds)}s`;
}
