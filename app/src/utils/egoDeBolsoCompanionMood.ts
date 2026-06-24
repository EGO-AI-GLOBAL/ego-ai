import type { WellnessJourney } from "@/api/types";
import { resolveEgoDeBolsoCareRoute } from "./egoDeBolsoCareRoute";

export type CompanionMood = "happy" | "waiting" | "lonely";

/** Todas as missões do nível actual estão feitas. */
export function egoDeBolsoMissionsComplete(journey: WellnessJourney): boolean {
  if (journey.level_complete) return true;
  const steps = journey.steps ?? [];
  if (steps.length === 0) return false;
  return steps.every((s) => s.done);
}

export const EGO_BOLSO_DAY_COMPLETE_MSG =
  "Todas as missões de hoje concluídas! Volte amanhã 💜";

export function companionNeedsCare(journey: WellnessJourney): boolean {
  if (egoDeBolsoMissionsComplete(journey)) return false;
  const pending = journey.steps?.filter((s) => !s.done) ?? [];
  return pending.length > 0 || !journey.level_complete;
}

export function companionMood(journey: WellnessJourney): CompanionMood {
  if (journey.level_complete) return "happy";
  const care = journey.care_percent ?? Math.round((journey.progress ?? 0) * 100);
  if (care >= 50) return "waiting";
  return "lonely";
}

/** Frase emocional do bichinho (Fase 2 — vínculo). */
export function companionMoodLine(journey: WellnessJourney): string | null {
  if (egoDeBolsoMissionsComplete(journey)) {
    return EGO_BOLSO_DAY_COMPLETE_MSG;
  }
  const mood = companionMood(journey);
  const task = (journey.today_task || "").trim();
  if (mood === "lonely") {
    if (task) return `Estou com saudade… ${task}`;
    return "Estou com saudade — falta a missão de hoje 🥚";
  }
  if (task) return `Quase lá! ${task}`;
  return "Falta pouco para completar o nível de hoje ✨";
}

export function egoDeBolsoNotificationCopy(journey: WellnessJourney): {
  title: string;
  body: string;
  screen: "wellness-journey" | "agenda" | "daily-care" | "chat";
} {
  const stage = journey.companion_stage_label ?? "EGO de Bolso";
  const task = (journey.today_task || "Complete a missão de hoje").trim();
  const route = resolveEgoDeBolsoCareRoute(journey);
  const screen =
    route === "/(main)/agenda"
      ? "agenda"
      : route === "/(main)/daily-care"
        ? "daily-care"
        : route === "/(main)/chat"
          ? "chat"
          : "wellness-journey";

  return {
    title: `${stage} precisa de você 🥚`,
    body: task.length > 90 ? `${task.slice(0, 87)}…` : task,
    screen,
  };
}
