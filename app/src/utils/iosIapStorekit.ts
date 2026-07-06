import { IAP_PRODUCT_IDS } from "@/constants/iapProducts";
import type { IosStoreSubscription } from "@/utils/iosIapPricing";

type IapModule = typeof import("react-native-iap");

function productIdFromRow(item: Record<string, unknown>): string {
  return String(item.productId || item.productIdentifier || "").trim();
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

/** Inicia compra de assinatura — v12 usa requestSubscription; v14+ requestPurchase type subs. */
export async function requestIosSubscription(iap: IapModule, productId: string): Promise<void> {
  const iapAny = iap as IapModule & {
    requestSubscription?: (opts: { sku: string }) => Promise<void>;
    requestPurchase?: (opts: { sku: string; type?: string }) => Promise<void>;
  };

  if (typeof iapAny.requestSubscription === "function") {
    await iapAny.requestSubscription({ sku: productId });
    return;
  }

  if (typeof iapAny.requestPurchase === "function") {
    await iapAny.requestPurchase({ sku: productId, type: "subs" });
    return;
  }

  throw new Error("Não foi possível abrir a compra na App Store.");
}
