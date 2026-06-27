import type { WellnessJourney } from "@/api/types";
import { egoDeBolsoDailyCarePercent } from "./egoDeBolsoDailyCare";
import { resolveEgoDeBolsoCareRoute } from "./egoDeBolsoCareRoute";
import { resolveCompanionDisplayName } from "./egoDeBolsoCompanionName";

export type CompanionMood = "happy" | "waiting" | "lonely";

/** Fechou o dia (X/X missões) ou terminou a jornada. */
export function egoDeBolsoMissionsComplete(journey: WellnessJourney): boolean {
  if (journey.mission_done_today) return true;
  if (journey.journey_finished) return true;
  return false;
}

export function egoDeBolsoDayCompleteMessage(journey: WellnessJourney): string {
  const task = (journey.today_task || "").trim();
  if (journey.mission_done_today && task) return task;
  const n = journey.missions_per_day ?? 5;
  return `${n} missões de hoje concluídas! Volte amanhã 💜`;
}

/** @deprecated use egoDeBolsoDayCompleteMessage(journey) */
export const EGO_BOLSO_DAY_COMPLETE_MSG =
  "Missões de hoje concluídas! Volte amanhã 💜";

export function companionNeedsCare(journey: WellnessJourney): boolean {
  if (egoDeBolsoMissionsComplete(journey)) return false;
  const pending = journey.steps?.filter((s) => !s.done) ?? [];
  return pending.length > 0 || !journey.level_complete;
}

export function companionMood(journey: WellnessJourney): CompanionMood {
  if (journey.level_complete) return "happy";
  const care = egoDeBolsoDailyCarePercent(journey);
  if (care >= 50) return "waiting";
  return "lonely";
}

/** Frase emocional do bichinho (Fase 2 — vínculo). */
export function companionMoodLine(journey: WellnessJourney): string | null {
  if (egoDeBolsoMissionsComplete(journey)) {
    return egoDeBolsoDayCompleteMessage(journey);
  }
  const name = resolveCompanionDisplayName(journey);
  const mood = companionMood(journey);
  const task = (journey.today_task || "").trim();
  if (mood === "lonely") {
    if (task) return `${name} sente saudade… ${task}`;
    return `${name} sente saudade — falta a missão de hoje 🥚`;
  }
  if (task) return `Quase lá, ${name}! ${task}`;
  return `${name} está quase no nível de hoje ✨`;
}

export function egoDeBolsoNotificationCopy(journey: WellnessJourney): {
  title: string;
  body: string;
  screen: "wellness-journey" | "agenda" | "daily-care" | "chat";
} {
  const name = resolveCompanionDisplayName(journey);
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
    title: `${name} precisa de você 🥚`,
    body: task.length > 90 ? `${task.slice(0, 87)}…` : task,
    screen,
  };
}
