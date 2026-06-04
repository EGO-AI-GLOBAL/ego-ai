import type { PlanTier, StripeCheckoutLinks } from "@/api/types";
import {
  TEAM_CHECKOUT_FALLBACK,
  type TeamPlanTier,
  type TeamSeatCount,
} from "@/constants/teamStripeCheckout";

export type CheckoutMarket = "br" | "int";

const LAUNCH_CHECKOUT_FALLBACK =
  "https://buy.stripe.com/7sYfZjfeC3mWfu810S4ow0K";

export function launchCheckoutUrl(
  links: StripeCheckoutLinks | null | undefined
): string | null {
  return links?.launch_url?.trim() || LAUNCH_CHECKOUT_FALLBACK;
}

/** Stripe precisa do user id para activar o plano após pagamento (webhook). */
export function withCheckoutUserRef(
  url: string | null | undefined,
  userId: string
): string | null {
  const base = (url || "").trim();
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
    connection: "https://buy.stripe.com/5kQ6oJfeC3mWeq4cJA4ow00",
    premium: "https://buy.stripe.com/14A7sNgiG6z8chWgZQ4ow02",
    total: "https://buy.stripe.com/5kQeVf6I60aK95K6lc4ow03",
    enterprise: null,
  },
  int: {
    connection: "https://buy.stripe.com/00w3cx9UibTs0ze24W4ow04",
    premium: "https://buy.stripe.com/eVq4gBaYme1A0ze10S4ow08",
    total: "https://buy.stripe.com/4gM28t6I63mW2Hm6lc4ow09",
    enterprise: null,
  },
};

export function checkoutUrlForTier(
  tier: PlanTier,
  links: StripeCheckoutLinks | null | undefined,
  market: CheckoutMarket = "br"
): string | null {
  if (tier === "essential") return null;
  const fallback = FALLBACK_CHECKOUT_URLS[market][tier] ?? null;
  if (!links) return fallback;
  if (market === "int") {
    switch (tier) {
      case "connection":
        return links.int_connection_url || fallback;
      case "premium":
        return links.int_premium_url || fallback;
      case "total":
        return links.int_total_url || fallback;
      case "enterprise":
        return links.int_enterprise_url || fallback;
      default:
        return fallback;
    }
  }
  switch (tier) {
    case "connection":
      return links.connection_url || links.monthly_url || fallback;
    case "premium":
      return links.premium_url || fallback;
    case "total":
      return links.total_url || fallback;
    case "enterprise":
      return links.enterprise_url || fallback;
    default:
      return fallback;
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
  return fromApi || fallback;
}
