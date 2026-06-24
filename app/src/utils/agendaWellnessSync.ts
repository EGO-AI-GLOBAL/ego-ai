import type { WellnessJourney } from "@/api/types";
import { completeWellnessJourneyStep } from "@/api/client";

/** Atualiza EGO de Bolso no dashboard após ação manual na agenda. */
export function applyAgendaWellnessUpdate(
  journey: WellnessJourney | null | undefined,
  onUpdate?: (j: WellnessJourney) => void
): void {
  if (journey && onUpdate) onUpdate(journey);
}

/** Se a API não devolveu jornada, tenta registar o passo (fallback). */
export async function ensureAgendaWellnessStep(
  journey: WellnessJourney | null | undefined,
  step: "habit" | "reminder"
): Promise<WellnessJourney | null> {
  if (journey) return journey;
  return completeWellnessJourneyStep(step);
}
