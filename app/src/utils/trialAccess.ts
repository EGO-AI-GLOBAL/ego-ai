import type { AccessInfo } from "@/api/types";
import type { DailyCareInfo } from "@/api/types";
import type { StreakInfo } from "@/api/types";
import type { WellnessJourney } from "@/api/types";

/** Dias restantes do trial (null = não é trial ou já é plano pago). */
export function parseTrialDaysRemaining(access: AccessInfo | null | undefined): number | null {
  if (!access?.access_status) return null;
  if (access.is_pro || access.plan_tier !== "essential") return null;
  const m = /(\d+)\s+dias?\s+restantes/i.exec(access.access_status);
  if (!m) return null;
  const n = parseInt(m[1], 10);
  return Number.isFinite(n) ? n : null;
}

export function isTrialExpired(access: AccessInfo | null | undefined): boolean {
  if (!access) return false;
  if (access.access_allowed === false) return true;
  return /expirado/i.test(access.access_status || "");
}

export function isTrialUrgent(days: number | null): boolean {
  return days !== null && days >= 0 && days <= 5;
}

export function buildTrialExpiredMessage(
  streak?: StreakInfo | null,
  journey?: WellnessJourney | null,
  care?: DailyCareInfo | null
): string {
  const parts: string[] = ["Seu teste grátis de 20 dias terminou."];
  const streakDays = streak?.current ?? 0;
  const journeyLevel = journey?.level ?? 0;
  const careDays = care?.current ?? 0;
  if (streakDays > 0) {
    parts.push(`Você construiu ${streakDays} ${streakDays === 1 ? "dia" : "dias"} de cuidado seguidos.`);
  }
  if (careDays > 0) {
    parts.push(`Monstrinhos do Humor: ${careDays} ${careDays === 1 ? "dia" : "dias"}.`);
  }
  if (journeyLevel > 1) {
    parts.push(`Companheiro de Bolso: nível ${journeyLevel}/${journey?.max_level ?? 20}.`);
  }
  parts.push("Assine para continuar — não perca seu progresso.");
  return parts.join(" ");
}
