import type { PlanCatalogItem, PlanTier } from "@/api/types";

/** Lançamento: assinaturas mensais (4 BR + 4 USD). Anuais INT ficam para fase 2. */

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

/** Meses com preço promocional (espelha EGO_LAUNCH_OFFER_MONTHS no Railway). */
export const LAUNCH_OFFER_INTRO_MONTHS = 6;

/** Início da campanha na Play (espelha EGO_LAUNCH_OFFER_START_DATE). */
export const LAUNCH_OFFER_CAMPAIGN_START = "2026-06-01";

/** Oferta de lançamento BR (fallback se a API não enviar launch_offer). */
export const LAUNCH_PLAN_OFFER_BR = {
  tier: "connection" as const,
  label: "EGO Conexão — Oferta de lançamento",
  tagline: `Oferta de lançamento: R$ 9,99/mês por ${LAUNCH_OFFER_INTRO_MONTHS} meses. Depois R$ 19,90/mês por ${LAUNCH_OFFER_INTRO_MONTHS} meses. Depois R$ 29,90/mês (EGO Conexão). Cancele quando quiser. Sem cupons adicionais.`,
  displayPrice: "R$ 9,99/mês",
  priceNum: 9.99,
  introMonths: LAUNCH_OFFER_INTRO_MONTHS,
  priceAfterBrl: 29.9,
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

const TIER_PRICE_ORDER_BR: Record<PlanTier, number> = {
  essential: 0,
  connection: 29.9,
  premium: 49.9,
  total: 99.9,
  enterprise: 199.9,
};

/** Individual BR: do mais barato ao mais caro (sem essencial). */
export function sortIndividualOffersByPrice(
  offers: MonthlyPlanOffer[]
): MonthlyPlanOffer[] {
  return [...offers].sort(
    (a, b) => TIER_PRICE_ORDER_BR[a.tier] - TIER_PRICE_ORDER_BR[b.tier]
  );
}

export const MONTHLY_PLAN_OFFERS: MonthlyPlanOffer[] = [
  {
    market: "br",
    tier: "connection",
    label: "EGO Conexão",
    tagline: "Seu assistente no dia a dia",
    displayPrice: "R$ 29,90/mês",
  },
  {
    market: "br",
    tier: "premium",
    label: "EGO Premium",
    tagline: "Mais conversa, voz e agenda",
    displayPrice: "R$ 49,90/mês",
    highlighted: true,
  },
  {
    market: "br",
    tier: "total",
    label: "EGO Total",
    tagline: "Uso intenso, quase sem limites",
    displayPrice: "R$ 99,90/mês",
  },
  {
    market: "br",
    tier: "enterprise",
    label: "EGO Empresa",
    tagline: "Equipes e agenda compartilhada",
    displayPrice: "R$ 199,90/mês",
    highlighted: true,
  },
  {
    market: "int",
    tier: "connection",
    label: "EGO AI Pro",
    tagline: "Your daily AI companion",
    displayPrice: "US$ 7,99/month",
  },
  {
    market: "int",
    tier: "premium",
    label: "EGO AI Premium",
    tagline: "More chat, voice & agenda",
    displayPrice: "US$ 14,99/month",
    highlighted: true,
  },
  {
    market: "int",
    tier: "total",
    label: "EGO AI Complete",
    tagline: "Generous limits for power users",
    displayPrice: "US$ 29,99/month",
  },
  {
    market: "int",
    tier: "enterprise",
    label: "EGO AI Business",
    tagline: "Teams & shared calendars",
    displayPrice: "US$ 49,99/month",
    highlighted: true,
  },
];

export const DISPLAY_PRICE_BRL: Record<Exclude<PlanTier, "essential">, number> = {
  connection: 29.9,
  premium: 49.9,
  total: 99.9,
  enterprise: 199.9,
};

export const DISPLAY_PRICE_USD: Record<Exclude<PlanTier, "essential">, number> = {
  connection: 7.99,
  premium: 14.99,
  total: 29.99,
  enterprise: 49.99,
};

export function fallbackLimitsForTier(tier: PlanTier): PlanCatalogItem["limits"] {
  if (tier === "essential") {
    return {
      monthly_tokens: 200_000,
      daily_text_messages: 10,
      daily_voice_messages: 3,
      daily_tts_replies: 5,
      max_agenda_items: 3,
      max_reminders: 3,
      audio_speed_multipliers: [1],
    };
  }
  if (tier === "connection") {
    return {
      monthly_tokens: 800_000,
      daily_text_messages: 50,
      daily_voice_messages: 15,
      daily_tts_replies: 0,
      max_agenda_items: 20,
      max_reminders: 20,
      audio_speed_multipliers: [1, 1.5, 2],
    };
  }
  if (tier === "premium") {
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
  if (tier === "enterprise") {
    return {
      monthly_tokens: 10_000_000,
      daily_text_messages: 0,
      daily_voice_messages: 0,
      daily_tts_replies: 0,
      max_agenda_items: 0,
      max_reminders: 0,
      audio_speed_multipliers: [1, 1.5, 2, 2.5],
    };
  }
  return {
    monthly_tokens: 5_000_000,
    daily_text_messages: 0,
    daily_voice_messages: 0,
    daily_tts_replies: 0,
    max_agenda_items: 0,
    max_reminders: 0,
    audio_speed_multipliers: [1, 1.5, 2],
  };
}
