import { Platform } from "react-native";
import { IAP_PRODUCT_IDS } from "@/constants/iapProducts";
import type { IosStoreSubscription } from "@/utils/iosIapPricing";

type ExpoIapModule = typeof import("expo-iap");

function productIdFromRow(item: Record<string, unknown>): string {
  return String(item.id || item.productId || item.productIdentifier || "").trim();
}

/** Extrai o offerToken (Google Play Billing 5+) do 1º base plan/oferta. */
export function androidOfferToken(item?: IosStoreSubscription | null): string | undefined {
  const raw = item as Record<string, unknown> | null | undefined;
  const details = (raw?.subscriptionOfferDetails ||
    raw?.subscriptionOfferDetailsAndroid) as Array<Record<string, unknown>> | undefined;
  if (Array.isArray(details) && details.length) {
    const token = String(details[0]?.offerToken || "").trim();
    if (token) return token;
  }
  return undefined;
}

/** Carrega assinaturas via expo-iap (Billing 8 no Android). */
export async function fetchIosSubscriptionProducts(
  iap: ExpoIapModule
): Promise<IosStoreSubscription[]> {
  const iapAny = iap as ExpoIapModule & {
    requestProducts?: (opts: { skus: string[]; type: string }) => Promise<unknown[]>;
    getSubscriptions?: (skus: string[] | { skus: string[] }) => Promise<unknown[]>;
  };

  let items: unknown[] = [];

  if (typeof iapAny.requestProducts === "function") {
    items = (await iapAny.requestProducts({ skus: IAP_PRODUCT_IDS, type: "subs" })) || [];
  } else if (typeof iapAny.getSubscriptions === "function") {
    items = (await (iapAny.getSubscriptions as (skus: string[]) => Promise<unknown[]>)(
      IAP_PRODUCT_IDS
    )) || [];
  } else {
    throw new Error("Biblioteca IAP sem getSubscriptions/requestProducts.");
  }

  return items.map((row) => {
    const r = row as Record<string, unknown>;
    const productId = productIdFromRow(r);
    const localizedPrice = String(r.displayPrice || r.localizedPrice || "").trim() || null;
    return {
      ...r,
      productId,
      localizedPrice,
    } as IosStoreSubscription;
  });
}

/**
 * Inicia compra de assinatura (expo-iap).
 * iOS: request.ios.sku
 * Android (Billing 5+): skus + subscriptionOffers com offerToken
 */
export async function requestIosSubscription(
  iap: ExpoIapModule,
  productId: string,
  opts?: { offerToken?: string }
): Promise<void> {
  const isAndroid = Platform.OS === "android";
  const offerToken = (opts?.offerToken || "").trim();

  if (typeof iap.requestPurchase !== "function") {
    throw new Error("Não foi possível abrir a compra na loja.");
  }

  if (isAndroid) {
    if (!offerToken) {
      throw new Error("Oferta Google Play indisponível. Tente de novo em instantes.");
    }
    await iap.requestPurchase({
      request: {
        android: {
          skus: [productId],
          subscriptionOffers: [{ sku: productId, offerToken }],
        },
      },
      type: "subs",
    });
    return;
  }

  await iap.requestPurchase({
    request: {
      ios: { sku: productId },
    },
    type: "subs",
  });
}
