import { noteSessionClosedForAd } from "@/ads/sessionClosedAdCounter";

/**
 * Após fechar check-in / PAUSA: conta sessão; a cada 2ª tenta interstitial.
 * onSkip = ímpar / erro de contador (não mostra ShapeScan de “no fill”).
 */
export function afterSessionClosedMaybeInterstitial(
  show: (onDone: (didShowAd: boolean) => void) => void,
  onInterstitialDone: (didShowAd: boolean) => void
): void {
  void (async () => {
    const shouldShow = await noteSessionClosedForAd();
    if (!shouldShow) return;
    show(onInterstitialDone);
  })();
}
