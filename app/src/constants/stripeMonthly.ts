import type { PlanCatalogItem, PlanTier } from "@/api/types";

/** Oferta única: EGO Premium R$ 49,90/mês (BR) + equivalente INT. */

export type MonthlyMarket = "br" | "int";

export type MonthlyPlanOffer = {
  market: MonthlyMarket;
  tier: PlanTier;
  label: string;
  tagline: string;
  /** Preço só para exibição no card */
  displayPrice: string;
  highlighted?: boolean;
};

/** Meses com preço promocional (legado IAP / API; UI Stripe já não vende lançamento). */
export const LAUNCH_OFFER_INTRO_MONTHS = 6;

/** Início da campanha na Play (espelha EGO_LAUNCH_OFFER_START_DATE). */
export const LAUNCH_OFFER_CAMPAIGN_START = "2026-06-01";

/** Oferta de lançamento BR (fallback se a API não enviar launch_offer). */
export const LAUNCH_PLAN_OFFER_BR = {
  tier: "connection" as const,
  label: "EGO Lançamento",
  tagline: `Oferta de lançamento por ${LAUNCH_OFFER_INTRO_MONTHS} meses. Depois EGO Premium.`,
  displayPrice: "R$ 10,94/mês",
  priceNum: 10.94,
  introMonths: LAUNCH_OFFER_INTRO_MONTHS,
  priceAfterBrl: 49.9,
};

function addMonthsIso(startIso: string, months: number): Date {
  const [y, m, d] = startIso.slice(0, 10).split("-").map(Number);
  const start = new Date(y, m - 1, d);
  const end = new Date(start.getFullYear(), start.getMonth() + months, start.getDate());
  return end;
}

/** Campanha global ainda ativa (some do app após 6 meses). */
export function isLaunchCampaignActive(
  startIso: string = LAUNCH_OFFER_CAMPAIGN_START,
  months: number = LAUNCH_OFFER_INTRO_MONTHS
): boolean {
  const end = addMonthsIso(startIso, months);
  return Date.now() < end.getTime();
}

export const MONTHLY_PLAN_OFFERS: MonthlyPlanOffer[] = [
  {
    market: "br",
    tier: "premium",
    label: "EGO Premium",
    tagline: "3 dias grátis · depois R$ 49,90/mês",
    displayPrice: "R$ 49,90/mês",
    highlighted: true,
  },
  {
    market: "int",
    tier: "premium",
    label: "EGO Premium",
    tagline: "3-day trial · then US$ 14,99/month",
    displayPrice: "US$ 14,99/month",
    highlighted: true,
  },
];

export const DISPLAY_PRICE_BRL: Record<Exclude<PlanTier, "essential">, number> = {
  connection: 49.9,
  premium: 49.9,
  total: 49.9,
  enterprise: 49.9,
};

export const DISPLAY_PRICE_USD: Record<Exclude<PlanTier, "essential">, number> = {
  connection: 14.99,
  premium: 14.99,
  total: 14.99,
  enterprise: 14.99,
};

export function fallbackLimitsForTier(tier: PlanTier): PlanCatalogItem["limits"] {
  if (tier === "essential") {
    return {
      monthly_tokens: 200_000,
      daily_text_messages: 5,
      daily_voice_messages: 3,
      daily_tts_replies: 5,
      max_agenda_items: 0,
      max_reminders: 0,
      audio_speed_multipliers: [1],
    };
  }
  // Catálogo público = Premium; outros tiers legados mapeiam para os mesmos limites generosos.
  void tier;
  return {
    monthly_tokens: 2_500_000,
    daily_text_messages: 0,
    daily_voice_messages: 0,
    daily_tts_replies: 0,
    max_agenda_items: 0,
    max_reminders: 0,
    audio_speed_multipliers: [1, 1.5, 2],
  };
}
