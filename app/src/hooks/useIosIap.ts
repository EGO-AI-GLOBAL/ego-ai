import { useCallback, useEffect, useRef, useState } from "react";
import { Alert } from "react-native";
import type { PlanTier } from "@/api/types";
import { verifyAppleIapPurchase } from "@/api/client";
import {
  IAP_PRODUCT_IDS,
  IAP_PRODUCTS,
  iapProductForTier,
  type IapProduct,
} from "@/constants/iapProducts";
import { usesAppleIap } from "@/utils/iosAppStoreBilling";
import {
  buildIosIapCardDisplay,
  type IosIapCardDisplay,
  type IosStoreSubscription,
} from "@/utils/iosIapPricing";
import { fetchIosSubscriptionProducts, requestIosSubscription } from "@/utils/iosIapStorekit";

type IapModule = typeof import("react-native-iap");

export type IosIapState = {
  ready: boolean;
  busy: boolean;
  productDisplay: Partial<Record<IapProduct["tier"], IosIapCardDisplay>>;
  purchaseTier: (tier: Exclude<PlanTier, "essential" | "enterprise">) => Promise<void>;
  restorePurchases: () => Promise<void>;
};

const noopAsync = async () => {};

export function useIosIap(
  onActivated?: () => void,
  options?: { showLaunchOffer?: boolean }
): IosIapState {
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [productDisplay, setProductDisplay] = useState<
    Partial<Record<IapProduct["tier"], IosIapCardDisplay>>
  >({});
  const iapRef = useRef<IapModule | null>(null);
  const purchaseInFlight = useRef(false);
  const onActivatedRef = useRef(onActivated);
  const showLaunchOffer = options?.showLaunchOffer === true;
  onActivatedRef.current = onActivated;

  const confirmPurchase = useCallback(
    async (purchase: {
      productId?: string | null;
      transactionId?: string | null;
      transactionReceipt?: string | null;
    }) => {
      const iap = iapRef.current;
      if (!iap || !purchase.productId) return;
      let receipt = (purchase.transactionReceipt || "").trim();
      if (!receipt && iap.getReceiptIOS) {
        receipt = (await iap.getReceiptIOS()) || "";
      }
      if (!receipt) {
        throw new Error("Recibo da App Store indisponível. Tente restaurar compras.");
      }
      await verifyAppleIapPurchase({
        receipt_data: receipt,
        product_id: purchase.productId,
        transaction_id: purchase.transactionId ?? undefined,
      });
      await iap.finishTransaction({ purchase, isConsumable: false });
      onActivatedRef.current?.();
      Alert.alert(
        "Plano ativado",
        "Sua assinatura foi confirmada. Se o plano não atualizar, puxe a tela para baixo."
      );
    },
    []
  );

  useEffect(() => {
    if (!usesAppleIap()) return;

    let purchaseUpdateSub: { remove: () => void } | null = null;
    let purchaseErrorSub: { remove: () => void } | null = null;
    let cancelled = false;

    const boot = async () => {
      try {
        const iap = await import("react-native-iap");
        if (cancelled) return;
        iapRef.current = iap;
        await iap.initConnection();
        const products = await fetchIosSubscriptionProducts(iap);
        const byId = new Map<string, IosStoreSubscription>();
        for (const item of products) {
          const id = String(item.productId || "").trim();
          if (id) byId.set(id, item);
        }
        const display: Partial<Record<IapProduct["tier"], IosIapCardDisplay>> = {};
        for (const product of IAP_PRODUCTS) {
          display[product.tier] = buildIosIapCardDisplay(
            product,
            byId.get(product.productId),
            { showLaunchOffer: showLaunchOffer && product.tier === "connection" }
          );
        }
        if (!cancelled) {
          setProductDisplay(display);
          setReady(true);
        }
      } catch {
        if (!cancelled) {
          const display: Partial<Record<IapProduct["tier"], IosIapCardDisplay>> = {};
          for (const product of IAP_PRODUCTS) {
            display[product.tier] = buildIosIapCardDisplay(product, null, {
              showLaunchOffer: showLaunchOffer && product.tier === "connection",
            });
          }
          setProductDisplay(display);
          setReady(false);
        }
      }
    };

    void boot();

    void import("react-native-iap").then((iap) => {
      if (cancelled) return;
      purchaseUpdateSub = iap.purchaseUpdatedListener(async (purchase) => {
        if (!purchaseInFlight.current) return;
        try {
          await confirmPurchase(purchase);
        } catch (e) {
          Alert.alert(
            "Compra",
            e instanceof Error ? e.message : "Não foi possível confirmar a compra."
          );
        } finally {
          purchaseInFlight.current = false;
          setBusy(false);
        }
      });
      purchaseErrorSub = iap.purchaseErrorListener((err) => {
        purchaseInFlight.current = false;
        setBusy(false);
        if (err.code !== "E_USER_CANCELLED") {
          Alert.alert("Compra", err.message || "Não foi possível concluir a compra.");
        }
      });
    });

    return () => {
      cancelled = true;
      purchaseUpdateSub?.remove();
      purchaseErrorSub?.remove();
      const iap = iapRef.current;
      iapRef.current = null;
      if (iap) void iap.endConnection();
    };
  }, [confirmPurchase, showLaunchOffer]);

  const purchaseTier = useCallback(
    async (tier: Exclude<PlanTier, "essential" | "enterprise">) => {
      if (!usesAppleIap() || purchaseInFlight.current) return;
      const product = iapProductForTier(tier);
      const iap = iapRef.current;
      if (!product || !iap) {
        Alert.alert("Planos", "Loja da App Store indisponível. Tente de novo em instantes.");
        return;
      }
      if (!ready) {
        Alert.alert(
          "Planos",
          "Ainda a ligar à App Store. Aguarde 2 segundos e tente de novo."
        );
        return;
      }
      purchaseInFlight.current = true;
      setBusy(true);
      try {
        await requestIosSubscription(iap, product.productId);
      } catch (e) {
        purchaseInFlight.current = false;
        setBusy(false);
        Alert.alert(
          "Compra",
          e instanceof Error ? e.message : "Não foi possível iniciar a compra."
        );
      }
    },
    [ready]
  );

  const restorePurchases = useCallback(async () => {
    if (!usesAppleIap()) return;
    const iap = iapRef.current;
    if (!iap) {
      Alert.alert("Restaurar", "Loja indisponível. Tente de novo em instantes.");
      return;
    }
    setBusy(true);
    try {
      const purchases = await iap.getAvailablePurchases();
      const ours = purchases.filter((p) =>
        IAP_PRODUCT_IDS.includes(String(p.productId || ""))
      );
      if (!ours.length) {
        Alert.alert("Restaurar", "Nenhuma assinatura EGO-AI encontrada nesta Apple ID.");
        return;
      }
      const latest = ours[ours.length - 1];
      await confirmPurchase(latest);
    } catch (e) {
      Alert.alert(
        "Restaurar",
        e instanceof Error ? e.message : "Não foi possível restaurar compras."
      );
    } finally {
      setBusy(false);
    }
  }, [confirmPurchase]);

  if (!usesAppleIap()) {
    return {
      ready: false,
      busy: false,
      productDisplay: {},
      purchaseTier: noopAsync as IosIapState["purchaseTier"],
      restorePurchases: noopAsync,
    };
  }

  return { ready, busy, productDisplay, purchaseTier, restorePurchases };
}

export function iosIapCatalog() {
  return IAP_PRODUCTS;
}
