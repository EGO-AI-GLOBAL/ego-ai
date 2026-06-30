import type { WellnessJourney } from "@/api/types";
import { resolveCompanionDisplayName } from "@/utils/egoDeBolsoCompanionName";
import { formatWellnessPendingLine } from "@/utils/egoDeBolsoStepHints";

/** Texto pré-preenchido no chat ao tocar «Falar disso». */
export function buildBolsoTalkDraft(journey: WellnessJourney): string {
  const petName = resolveCompanionDisplayName(journey);
  const missionsToday = journey.missions_today ?? 0;
  const missionsPerDay = journey.missions_per_day ?? 5;
  const pending = journey.steps?.filter((s) => !s.done) ?? [];
  const pendingLine = formatWellnessPendingLine(pending);
  const task = (journey.today_task || "missão de hoje").trim();
  const tail = pendingLine ? ` Falta: ${pendingLine}.` : "";
  return `Quero ajuda com a missão do ${petName} (${missionsToday}/${missionsPerDay} hoje): ${task}.${tail}`;
}
