import type { AccessInfo } from "@/api/types";

export type UsageLevel = "ok" | "warn" | "critical";

export function usageLevel(percent: number): UsageLevel {
  if (percent >= 96) return "critical";
  if (percent >= 71) return "warn";
  return "ok";
}

export function usagePercent(used: number, limit: number): number {
  if (limit <= 0) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

export function formatCount(n: number): string {
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return Number.isInteger(m) ? `${m}M` : `${m.toFixed(1)}M`;
  }
  if (n >= 1_000) {
    return `${Math.round(n / 1_000)}k`;
  }
  return String(n);
}

export type UsageMetric = {
  id: string;
  label: string;
  used: number;
  limit: number;
  unlimited: boolean;
  percent: number;
  level: UsageLevel;
  detail: string;
};

export function buildUsageMetrics(access: AccessInfo | null): UsageMetric[] {
  if (!access) return [];

  const items: UsageMetric[] = [];

  const tokLimit = access.monthly_tokens_limit ?? 0;
  const tokUsed = access.monthly_tokens_used ?? 0;
  if (tokLimit > 0) {
    const pct = usagePercent(tokUsed, tokLimit);
    items.push({
      id: "tokens",
      label: "Tokens este mês",
      used: tokUsed,
      limit: tokLimit,
      unlimited: false,
      percent: pct,
      level: usageLevel(pct),
      detail: `${formatCount(tokUsed)} / ${formatCount(tokLimit)}`,
    });
  }

  const textLimit = access.daily_text_messages_limit ?? access.daily_messages_limit ?? 0;
  const textUsed =
    access.daily_text_messages_used ?? access.daily_messages_used ?? 0;
  if (textLimit > 0) {
    const pct = usagePercent(textUsed, textLimit);
    items.push({
      id: "text",
      label: "Mensagens de texto (hoje)",
      used: textUsed,
      limit: textLimit,
      unlimited: false,
      percent: pct,
      level: usageLevel(pct),
      detail: `${textUsed} / ${textLimit}`,
    });
  }

  const voiceLimit = access.daily_voice_messages_limit ?? 0;
  const voiceUsed = access.daily_voice_messages_used ?? 0;
  if (voiceLimit > 0) {
    const pct = usagePercent(voiceUsed, voiceLimit);
    items.push({
      id: "voice",
      label: "Mensagens de voz (hoje)",
      used: voiceUsed,
      limit: voiceLimit,
      unlimited: false,
      percent: pct,
      level: usageLevel(pct),
      detail: `${voiceUsed} / ${voiceLimit}`,
    });
  }

  const ttsLimit = access.daily_tts_limit ?? 0;
  const ttsUsed = access.daily_tts_used ?? 0;
  if (ttsLimit > 0) {
    const pct = usagePercent(ttsUsed, ttsLimit);
    items.push({
      id: "tts",
      label: "Respostas em áudio (hoje)",
      used: ttsUsed,
      limit: ttsLimit,
      unlimited: false,
      percent: pct,
      level: usageLevel(pct),
      detail: `${ttsUsed} / ${ttsLimit}`,
    });
  }

  const agLimit = access.agenda_limit ?? 0;
  const agUsed = access.agenda_used ?? 0;
  if (agLimit > 0) {
    const pct = usagePercent(agUsed, agLimit);
    items.push({
      id: "agenda",
      label: "Hábitos na agenda",
      used: agUsed,
      limit: agLimit,
      unlimited: false,
      percent: pct,
      level: usageLevel(pct),
      detail: `${agUsed} / ${agLimit}`,
    });
  }

  const remLimit = access.reminders_limit ?? 0;
  const remUsed = access.reminders_used ?? 0;
  if (remLimit > 0) {
    const pct = usagePercent(remUsed, remLimit);
    items.push({
      id: "reminders",
      label: "Lembretes ativos",
      used: remUsed,
      limit: remLimit,
      unlimited: false,
      percent: pct,
      level: usageLevel(pct),
      detail: `${remUsed} / ${remLimit}`,
    });
  }

  return items;
}

/** Estimativa quando o servidor ainda não devolveu access atualizado. */
export function estimateTokenDelta(userText: string, assistantReply: string): number {
  const chars = (userText || "").length + (assistantReply || "").length;
  return Math.max(80, Math.round(chars * 0.4));
}

export function patchAccessWithTokenDelta(
  access: AccessInfo | null,
  delta: number
): AccessInfo | null {
  if (!access || delta <= 0) return access;
  const limit = access.monthly_tokens_limit ?? 0;
  if (limit <= 0) return access;
  const used = Math.min(limit, (access.monthly_tokens_used ?? 0) + delta);
  const pct = usagePercent(used, limit);
  return {
    ...access,
    monthly_tokens_used: used,
    monthly_tokens_ok: access.is_test_total ? true : used < limit,
    monthly_tokens_message:
      used >= limit && !access.is_test_total
        ? "Limite mensal de tokens atingido."
        : access.monthly_tokens_message,
  };
}

export function primaryTokenPercent(access: AccessInfo | null): number {
  if (!access) return 0;
  const percents: number[] = [];

  if ((access.monthly_tokens_limit ?? 0) > 0) {
    percents.push(
      usagePercent(access.monthly_tokens_used ?? 0, access.monthly_tokens_limit ?? 0)
    );
  }

  const textLimit = access.daily_text_messages_limit ?? access.daily_messages_limit ?? 0;
  const textUsed = access.daily_text_messages_used ?? access.daily_messages_used ?? 0;
  if (textLimit > 0) {
    percents.push(usagePercent(textUsed, textLimit));
  }

  const voiceLimit = access.daily_voice_messages_limit ?? 0;
  const voiceUsed = access.daily_voice_messages_used ?? 0;
  if (voiceLimit > 0) {
    percents.push(usagePercent(voiceUsed, voiceLimit));
  }

  const ttsLimit = access.daily_tts_limit ?? 0;
  const ttsUsed = access.daily_tts_used ?? 0;
  if (ttsLimit > 0) {
    percents.push(usagePercent(ttsUsed, ttsLimit));
  }

  if (!percents.length) return 0;
  return Math.max(...percents);
}
