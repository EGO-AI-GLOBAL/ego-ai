import type { AccessInfo, PlanTier } from "@/api/types";
import { normalizePlanTier } from "@/constants/avatarCatalog";

/** Espelha ego_api/plans.py — fallback se a API vier incompleta. */
export const PLAN_MONTHLY_TOKEN_LIMITS: Record<PlanTier, number> = {
  essential: 200_000,
  connection: 800_000,
  premium: 2_500_000,
  total: 5_000_000,
  enterprise: 10_000_000,
};

export const PLAN_LABELS: Record<PlanTier, string> = {
  essential: "EGO Essencial",
  connection: "EGO Conexão",
  premium: "EGO Premium",
  total: "EGO Total",
  enterprise: "EGO Empresa",
};

export function normalizeAccessInfo(raw: AccessInfo | null | undefined): AccessInfo | null {
  if (!raw) return null;
  const tier = normalizePlanTier(raw.plan_tier);
  const limitFromServer = Number(raw.monthly_tokens_limit ?? 0);
  const limit =
    limitFromServer > 0 ? limitFromServer : PLAN_MONTHLY_TOKEN_LIMITS[tier] ?? 200_000;
  const used = Math.max(0, Number(raw.monthly_tokens_used ?? 0));
  return {
    ...raw,
    plan_tier: tier,
    plan_label: raw.plan_label?.trim() || PLAN_LABELS[tier],
    is_pro: raw.is_pro ?? tier !== "essential",
    monthly_tokens_limit: limit,
    monthly_tokens_used: used,
    monthly_tokens_ok:
      raw.is_test_total === true
        ? true
        : raw.monthly_tokens_ok !== false && used < limit,
  };
}
