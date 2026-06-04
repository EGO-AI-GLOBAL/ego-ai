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

/** Oferta de lançamento BR (fallback se a API não enviar launch_offer). */
export const LAUNCH_PLAN_OFFER_BR = {
  tier: "connection" as const,
  label: "EGO Conexão — Oferta de lançamento",
  tagline: "Mesmos benefícios da Conexão · depois R$ 29,90/mês",
  displayPrice: "R$ 9,90/mês",
  priceNum: 9.9,
};

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
