import type { AccessInfo } from "@/api/types";

/**
 * Essential / FREE com anúncios → rodapé (AdMob ou cross-promo).
 * Premium / pago / show_ads=false → nada.
 */
export function shouldShowChatAds(access: AccessInfo | null | undefined): boolean {
  if (!access) return false;
  if (access.show_ads === false) return false;
  if (access.is_pro === true) return false;
  if (access.show_ads === true) return true;
  const tier = (access.plan_tier || "essential").toString().trim().toLowerCase();
  return tier === "essential";
}
