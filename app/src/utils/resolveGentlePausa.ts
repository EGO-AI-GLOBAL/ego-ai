import type { DailyCareCrisisBridge, PausaDailyExercise } from "@/api/types";

/** PAUSA inline no jardim — técnica curta para Nublina/Agita. */
export function resolveGentlePausaExercise(bridge?: DailyCareCrisisBridge | null): PausaDailyExercise {
  const seconds = bridge?.duration_seconds ?? 60;
  return {
    key: bridge?.exercise_key ?? "breath44",
    emoji: "🌬️",
    title: bridge?.title ?? "PAUSA 60s",
    subtitle: bridge?.subtitle ?? "Respiração lenta — acalma o corpo agora",
    duration_seconds: seconds,
    mode: "breath",
    breath_inhale: 4,
    breath_exhale: 6,
  };
}
