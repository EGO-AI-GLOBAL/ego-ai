import {
  IOS_LAUNCH_INTRO_MONTHS,
  IOS_LAUNCH_INTRO_PRICE_BRL,
  IOS_LAUNCH_REGULAR_PRICE_BRL,
  type IapProduct,
} from "@/constants/iapProducts";
import { formatMonthlyPrice } from "@/constants/plans";

/** Campos opcionais devolvidos pela App Store via react-native-iap. */
export type IosStoreSubscription = {
  productId?: string | null;
  localizedPrice?: string | null;
  introductoryPrice?: string | null;
  introductoryPriceAsAmountIOS?: string | null;
  introductoryPriceNumberOfPeriodsIOS?: string | null;
  introductoryPriceSubscriptionPeriodIOS?: string | null;
  /** Google Play Billing 5+: base plans e ofertas (contém offerToken). */
  subscriptionOfferDetails?: Array<Record<string, unknown>> | null;
};

export type IosIapCardDisplay = {
  priceLine: string;
  badgeLabel?: string;
  footnote?: string;
  highlighted?: boolean;
};

function introMonthsFromStore(product?: IosStoreSubscription | null): number {
  const raw = product?.introductoryPriceNumberOfPeriodsIOS?.trim();
  if (!raw) return IOS_LAUNCH_INTRO_MONTHS;
  const n = parseInt(raw.replace(/\D/g, ""), 10);
  return Number.isFinite(n) && n > 0 ? n : IOS_LAUNCH_INTRO_MONTHS;
}

function introPriceLine(product?: IosStoreSubscription | null): string {
  const fromStore =
    product?.introductoryPrice?.trim() ||
    product?.introductoryPriceAsAmountIOS?.trim();
  if (fromStore) {
    const hasPerMonth = /m[eê]s|month/i.test(fromStore);
    return hasPerMonth ? fromStore : `${fromStore}/mês`;
  }
  return formatMonthlyPrice(IOS_LAUNCH_INTRO_PRICE_BRL);
}

function regularPriceLine(product: IapProduct, store?: IosStoreSubscription | null): string {
  const fromStore = store?.localizedPrice?.trim();
  if (fromStore) {
    const hasPerMonth = /m[eê]s|month/i.test(fromStore);
    return hasPerMonth ? fromStore : `${fromStore}/mês`;
  }
  return formatMonthlyPrice(product.priceBrl);
}

export function buildIosIapCardDisplay(
  product: IapProduct,
  store?: IosStoreSubscription | null,
  options?: { showLaunchOffer?: boolean }
): IosIapCardDisplay {
  const regular = regularPriceLine(product, store);

  if (product.tier === "connection" && options?.showLaunchOffer) {
    const months = introMonthsFromStore(store);
    const intro = introPriceLine(store);
    const after =
      store?.localizedPrice?.trim() ||
      formatMonthlyPrice(IOS_LAUNCH_REGULAR_PRICE_BRL);
    return {
      priceLine: intro,
      badgeLabel: `Lançamento · ${months} meses`,
      highlighted: true,
      footnote: `Oferta introdutória na App Store: ${intro} por ${months} meses para quem nunca assinou. Depois ${after}/mês (renovação automática até cancelar em Ajustes → Apple ID → Assinaturas).`,
    };
  }

  return { priceLine: regular };
}
