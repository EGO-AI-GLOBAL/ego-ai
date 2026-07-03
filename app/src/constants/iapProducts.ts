import type { PlanTier } from "@/api/types";

/**
 * Assinaturas In-App Purchase (iOS). Preço iOS = +30% do site/Android para cobrir
 * a taxa da Apple. Android/web continuam via Stripe (não usam este ficheiro).
 *
 * Os IDs abaixo têm de ser criados IGUAIS no App Store Connect
 * (Assinaturas → grupo → auto-renováveis).
 */

export type IapProduct = {
  productId: string;
  tier: Exclude<PlanTier, "essential" | "enterprise">;
  label: string;
  /** Preço-alvo BRL no iOS (+30%); no Connect escolher o tier de preço mais próximo. */
  priceBrl: number;
  /** Preço base site/Android, só para referência interna. */
  basePriceBrl: number;
};

export const IOS_SUBSCRIPTION_GROUP = "EGO-AI Planos";

/** Oferta introdutória na assinatura Conexão (App Store Connect → Oferta introdutória). */
export const IOS_LAUNCH_CONNECTION_PRODUCT_ID = "com.egoai.app.sub.connection.monthly";
export const IOS_LAUNCH_INTRO_MONTHS = 6;
export const IOS_LAUNCH_INTRO_PRICE_BRL = 19.9;
export const IOS_LAUNCH_REGULAR_PRICE_BRL = 39.9;

export const IAP_PRODUCTS: IapProduct[] = [
  {
    productId: "com.egoai.app.sub.connection.monthly",
    tier: "connection",
    label: "EGO Conexão",
    priceBrl: 39.9,
    basePriceBrl: 29.9,
  },
  {
    productId: "com.egoai.app.sub.premium.monthly",
    tier: "premium",
    label: "EGO Premium",
    priceBrl: 69.9,
    basePriceBrl: 49.9,
  },
  {
    productId: "com.egoai.app.sub.total.monthly",
    tier: "total",
    label: "EGO Total",
    priceBrl: 129.9,
    basePriceBrl: 99.9,
  },
];

export const IAP_PRODUCT_IDS = IAP_PRODUCTS.map((p) => p.productId);

export function iapProductForTier(tier: string): IapProduct | undefined {
  return IAP_PRODUCTS.find((p) => p.tier === tier);
}

export function tierForIapProduct(productId: string): IapProduct["tier"] | undefined {
  return IAP_PRODUCTS.find((p) => p.productId === productId)?.tier;
}
