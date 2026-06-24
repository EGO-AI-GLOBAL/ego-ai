import type { WellnessJourney } from "@/api/types";

/** Atualiza EGO de Bolso no dashboard após ação manual na agenda. */
export function applyAgendaWellnessUpdate(
  journey: WellnessJourney | null | undefined,
  onUpdate?: (j: WellnessJourney) => void
): void {
  if (journey && onUpdate) onUpdate(journey);
}
