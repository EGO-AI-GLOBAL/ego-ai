import type { PlanTier } from "@/api/types";

/**
 * Assinaturas In-App (lojas). Preço loja = +30% do site/Stripe para cobrir
 * taxa Apple/Google. Site/web continuam via Stripe.
 *
 * IDs IGUAIS no App Store Connect e no Google Play Console
 * (Assinaturas → auto-renováveis / Play Billing).
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

/** Nota curta no cartão de plano: o preço mostrado vem da loja. */
export const IOS_APP_STORE_PRICE_NOTE =
  "Preço cobrado pela loja (App Store / Google Play).";

export function iapProductForTier(tier: string): IapProduct | undefined {
  return IAP_PRODUCTS.find((p) => p.tier === tier);
}

export function tierForIapProduct(productId: string): IapProduct["tier"] | undefined {
  return IAP_PRODUCTS.find((p) => p.productId === productId)?.tier;
}
