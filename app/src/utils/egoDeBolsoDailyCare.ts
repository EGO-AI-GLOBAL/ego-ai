import type { WellnessJourney } from "@/api/types";

/** Barra «Cuidado»: 1/5 = 20%, 2/5 = 40% … 5/5 = 100%. */
export function egoDeBolsoDailyCarePercent(journey: WellnessJourney): number {
  if (journey.mission_done_today || journey.journey_finished) return 100;
  const perDay = journey.missions_per_day ?? 5;
  if (perDay <= 0) return 0;
  const done = Math.max(0, journey.missions_today ?? 0);
  return Math.min(100, Math.round((done / perDay) * 100));
}

export function egoDeBolsoDailyCareFraction(journey: WellnessJourney): number {
  return egoDeBolsoDailyCarePercent(journey) / 100;
}
