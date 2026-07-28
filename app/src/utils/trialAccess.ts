import type { AccessInfo } from "@/api/types";
import type { DailyCareInfo } from "@/api/types";
import type { StreakInfo } from "@/api/types";
import type { WellnessJourney } from "@/api/types";
import { allowsInAppPlanPurchase } from "@/utils/iosAppStoreBilling";

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
  // Freemium pós-trial: servidor libera texto (access_allowed true) — não tratar como bloqueio total.
  if (access.essential_post_trial || access.show_ads) {
    if (access.access_allowed !== false) return false;
  }
  if (access.access_allowed === false) return true;
  return /expirado/i.test(access.access_status || "");
}

/** Voz/TTS bloqueados no freemium pós-trial (texto continua com limite diário). */
export function isVoiceBlockedForPlan(access: AccessInfo | null | undefined): boolean {
  if (!access) return false;
  if (access.essential_post_trial) return true;
  if (access.daily_voice_messages_ok === false && access.plan_tier === "essential") {
    return true;
  }
  return false;
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
    const stage = journey?.companion_stage_label ?? "EGO de Bolso";
    const emoji = journey?.companion_sprite_emoji ?? journey?.emoji ?? "🥚";
    parts.push(
      `${emoji} Seu ${stage} chegou ao nível ${journeyLevel}/${journey?.max_level ?? 500} — não deixe ele parar no ovo.`
    );
  }
  parts.push(
    allowsInAppPlanPurchase()
      ? "Assine o EGO Premium e continue cuidando do seu progresso."
      : "Entre com o mesmo e-mail se já tiver plano ativo na sua conta."
  );
  return parts.join(" ");
}
