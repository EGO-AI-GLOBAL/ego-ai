import type { PlanTier, StripeCheckoutLinks } from "@/api/types";
import {
  TEAM_CHECKOUT_FALLBACK,
  type TeamPlanTier,
  type TeamSeatCount,
} from "@/constants/teamStripeCheckout";
import { usesStripeCheckout } from "@/utils/iosAppStoreBilling";

export type CheckoutMarket = "br" | "int";

export const LAUNCH_CHECKOUT_FALLBACK =
  "https://buy.stripe.com/7sY3cu923evNaqP6ovfYY04";

function gateCheckoutUrl(url: string | null | undefined): string | null {
  if (!usesStripeCheckout()) return null;
  const trimmed = (url || "").trim();
  return trimmed || null;
}

export function launchCheckoutUrl(
  links: StripeCheckoutLinks | null | undefined
): string | null {
  return gateCheckoutUrl(links?.launch_url?.trim() || LAUNCH_CHECKOUT_FALLBACK);
}

/** Stripe precisa do user id para activar o plano após pagamento (webhook). */
export function withCheckoutUserRef(
  url: string | null | undefined,
  userId: string
): string | null {
  const base = gateCheckoutUrl(url);
  if (!base) return null;
  const uid = (userId || "").trim();
  if (!uid) return base;
  if (base.includes("client_reference_id=")) return base;
  const sep = base.includes("?") ? "&" : "?";
  return `${base}${sep}client_reference_id=${encodeURIComponent(uid)}`;
}

const FALLBACK_CHECKOUT_URLS: Record<
  CheckoutMarket,
  Record<Exclude<PlanTier, "essential">, string | null>
> = {
  br: {
    connection: "https://buy.stripe.com/4gM5kC6TV4Vd6az3cjfYY05",
    premium: "https://buy.stripe.com/3cIeVc5PRevN56vcMTfYY02",
    total: "https://buy.stripe.com/14AeVcdijevN8iH3cjfYY03",
    enterprise: null,
  },
  int: {
    connection: "https://buy.stripe.com/00w3cx9UibTs0ze24W4ow04",
    premium: "https://buy.stripe.com/5kQbJ3eay7Dc81G7pg4ow06",
    total: "https://buy.stripe.com/eVqfZjaYm8Hg4Pu9xo4ow0L",
    enterprise: "https://buy.stripe.com/8x2dRbfeC9Lk4Pu6lc4ow0N",
  },
};

export function checkoutUrlForTier(
  tier: PlanTier,
  links: StripeCheckoutLinks | null | undefined,
  market: CheckoutMarket = "br"
): string | null {
  if (tier === "essential") return null;
  const fallback = FALLBACK_CHECKOUT_URLS[market][tier] ?? null;
  if (!links) return gateCheckoutUrl(fallback);
  if (market === "int") {
    switch (tier) {
      case "connection":
        return gateCheckoutUrl(links.int_connection_url || fallback);
      case "premium":
        return gateCheckoutUrl(links.int_premium_url || fallback);
      case "total":
        return gateCheckoutUrl(links.int_total_url || fallback);
      case "enterprise":
        return gateCheckoutUrl(links.int_enterprise_url || fallback);
      default:
        return gateCheckoutUrl(fallback);
    }
  }
  switch (tier) {
    case "connection":
      return gateCheckoutUrl(links.connection_url || links.monthly_url || fallback);
    case "premium":
      return gateCheckoutUrl(links.premium_url || fallback);
    case "total":
      return gateCheckoutUrl(links.total_url || fallback);
    case "enterprise":
      return gateCheckoutUrl(links.enterprise_url || fallback);
    default:
      return gateCheckoutUrl(fallback);
  }
}

export function teamCheckoutUrl(
  tier: TeamPlanTier,
  seats: TeamSeatCount,
  links: StripeCheckoutLinks | null | undefined,
  market: CheckoutMarket = "br"
): string | null {
  const fallback = TEAM_CHECKOUT_FALLBACK[market][tier][seats] ?? null;
  const fromApi = links?.team?.[market]?.[tier]?.[String(seats)];
  return gateCheckoutUrl(fromApi || fallback);
}
