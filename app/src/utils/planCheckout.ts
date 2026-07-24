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
    // Legado: redireciona para o mesmo Payment Link do Premium.
    connection: "https://buy.stripe.com/8x23cuguvbjB2Yn4gnfYY0d",
    premium: "https://buy.stripe.com/8x23cuguvbjB2Yn4gnfYY0d",
    total: "https://buy.stripe.com/8x23cuguvbjB2Yn4gnfYY0d",
    enterprise: null,
  },
  int: {
    connection: "https://buy.stripe.com/eVq4gBaYme1A0ze10S4ow08",
    premium: "https://buy.stripe.com/eVq4gBaYme1A0ze10S4ow08",
    total: "https://buy.stripe.com/eVq4gBaYme1A0ze10S4ow08",
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
