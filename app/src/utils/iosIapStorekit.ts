import { Platform } from "react-native";
import { IAP_PRODUCT_IDS } from "@/constants/iapProducts";
import type { IosStoreSubscription } from "@/utils/iosIapPricing";

type IapModule = typeof import("react-native-iap");

function productIdFromRow(item: Record<string, unknown>): string {
  return String(item.productId || item.productIdentifier || "").trim();
}

/** Extrai o offerToken (Google Play Billing 5+) do 1º base plan/oferta. */
export function androidOfferToken(item?: IosStoreSubscription | null): string | undefined {
  const raw = item as Record<string, unknown> | null | undefined;
  const details = raw?.subscriptionOfferDetails as
    | Array<Record<string, unknown>>
    | undefined;
  if (Array.isArray(details) && details.length) {
    const token = String(details[0]?.offerToken || "").trim();
    if (token) return token;
  }
  return undefined;
}

/** Carrega assinaturas — compatível react-native-iap v12 (getSubscriptions) e v14+ (fetchProducts). */
export async function fetchIosSubscriptionProducts(
  iap: IapModule
): Promise<IosStoreSubscription[]> {
  const iapAny = iap as IapModule & {
    fetchProducts?: (opts: { skus: string[]; type: string }) => Promise<unknown[]>;
    getSubscriptions?: (opts: { skus: string[] }) => Promise<unknown[]>;
  };

  if (typeof iapAny.fetchProducts === "function") {
    const items = await iapAny.fetchProducts({ skus: IAP_PRODUCT_IDS, type: "subs" });
    return (items || []).map((row) => {
      const r = row as Record<string, unknown>;
      return { ...r, productId: productIdFromRow(r) } as IosStoreSubscription;
    });
  }

  if (typeof iapAny.getSubscriptions === "function") {
    const items = await iapAny.getSubscriptions({ skus: IAP_PRODUCT_IDS });
    return (items || []).map((row) => {
      const r = row as Record<string, unknown>;
      return { ...r, productId: productIdFromRow(r) } as IosStoreSubscription;
    });
  }

  throw new Error("Biblioteca IAP sem getSubscriptions/fetchProducts.");
}

/**
 * Inicia compra de assinatura.
 * iOS: requestSubscription({ sku }).
 * Android (Billing 5+): precisa subscriptionOffers com offerToken.
 */
export async function requestIosSubscription(
  iap: IapModule,
  productId: string,
  opts?: { offerToken?: string }
): Promise<void> {
  const iapAny = iap as IapModule & {
    requestSubscription?: (opts: Record<string, unknown>) => Promise<void>;
    requestPurchase?: (opts: Record<string, unknown>) => Promise<void>;
  };

  const isAndroid = Platform.OS === "android";
  const androidOffers =
    isAndroid && opts?.offerToken
      ? { subscriptionOffers: [{ sku: productId, offerToken: opts.offerToken }] }
      : {};

  if (typeof iapAny.requestSubscription === "function") {
    await iapAny.requestSubscription({ sku: productId, ...androidOffers });
    return;
  }

  if (typeof iapAny.requestPurchase === "function") {
    await iapAny.requestPurchase({ sku: productId, type: "subs", ...androidOffers });
    return;
  }

  throw new Error("Não foi possível abrir a compra na loja.");
}
