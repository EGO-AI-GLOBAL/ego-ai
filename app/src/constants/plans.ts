import type { PlanCatalogItem, PlanTier } from "@/api/types";

const TIER_RANK: Record<PlanTier, number> = {
  essential: 0,
  connection: 1,
  premium: 2,
  total: 3,
  enterprise: 4,
};

/** Botão de checkout conforme plano atual (mensal: pode subir ou descer). */
export function subscribeLabelForTier(
  target: PlanTier,
  current: PlanTier,
  opts?: { isLaunch?: boolean }
): string {
  if (target === current && !opts?.isLaunch) return "Plano atual";
  if (opts?.isLaunch) return "Assinar oferta";
  const t = TIER_RANK[target] ?? 0;
  const c = TIER_RANK[current] ?? 0;
  if (t < c) return "Mudar para este plano";
  if (t > c) return "Melhorar plano";
  return "Assinar";
}

/** Único plano à venda. Outros tiers existem só por legado / webhook / IAP antiga. */
export const PAID_PLAN_TIERS: PlanTier[] = ["premium"];

export const PLAN_TAGLINES: Record<PlanTier, string> = {
  essential: "3 dias para conhecer o EGO-AI",
  connection: "EGO Premium",
  premium: "Tudo no bolso · voz, agenda e assistentes",
  total: "EGO Premium",
  enterprise: "EGO Premium",
};

export function formatBrl(price: number): string {
  if (price <= 0) return "Grátis";
  return price.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export function formatMonthlyPrice(price: number): string {
  if (price <= 0) return "Grátis";
  return `${formatBrl(price)}/mês`;
}

export function formatTokenLimit(n: number): string {
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    const label = Number.isInteger(m) ? `${m}` : m.toFixed(1);
    return `${label}M tokens/mês`;
  }
  if (n >= 1_000) {
    return `${Math.round(n / 1_000)}k tokens/mês`;
  }
  return `${n} tokens/mês`;
}

export function formatDailyLimit(n: number, unit: string): string {
  if (n <= 0) return `${unit} ilimitado`;
  return `${n} ${unit}/dia`;
}

export function formatCap(n: number, unit: string): string {
  if (n <= 0) return `${unit} ilimitados`;
  return `Até ${n} ${unit}`;
}

export function planFeatureLines(plan: PlanCatalogItem): string[] {
  const lim = plan.limits;
  const speeds =
    lim.audio_speed_multipliers.length <= 1
      ? "Velocidade de áudio 1x"
      : `Velocidade ${lim.audio_speed_multipliers.map((s) => (s === 1 ? "1x" : `${s}x`)).join(", ")}`;

  return [
    formatTokenLimit(lim.monthly_tokens),
    formatDailyLimit(lim.daily_text_messages, "mensagens de texto"),
    formatDailyLimit(lim.daily_voice_messages, "mensagens de voz"),
    lim.daily_tts_replies <= 0
      ? "Respostas em áudio ilimitadas"
      : `${lim.daily_tts_replies} respostas em áudio/dia`,
    formatCap(lim.max_agenda_items, "hábitos na agenda"),
    formatCap(lim.max_reminders, "lembretes"),
    "Agenda compartilhada e Entre Nós",
    speeds,
    "Todos os assistentes desbloqueados",
  ];
}
