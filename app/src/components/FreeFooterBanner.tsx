import type { AccessInfo } from "@/api/types";
import { ShapeScanCrossPromoBanner } from "@/components/ShapeScanCrossPromoBanner";
import { bannerAdUnitId, isUsingAdMobTestIds } from "@/constants/admob";
import { shouldShowChatAds } from "@/utils/shouldShowChatAds";
import React, { useEffect, useState } from "react";
import { Platform, StyleSheet, View } from "react-native";

type AdsModule = typeof import("react-native-google-mobile-ads");

type Props = {
  access: AccessInfo | null | undefined;
};

type FooterMode = "pending" | "admob" | "crosspromo";

/**
 * Rodapé ~60px — espelho ShapeScan (2026-08-04):
 * 1) Premium EGO → sem promo
 * 2) Free + AdMob com fill → mantém AdMob
 * 3) Free + AdMob sem fill / erro / web / IDs teste → banner ShapeScan
 * Nunca empilha AdMob + ShapeScan. Sem IAP ShapeScan.
 */
export function FreeFooterBanner({ access }: Props) {
  const show = shouldShowChatAds(access);
  const useRealAds = show && !isUsingAdMobTestIds() && Platform.OS !== "web";
  const [ads, setAds] = useState<AdsModule | null>(null);
  const [mode, setMode] = useState<FooterMode>("pending");

  useEffect(() => {
    if (!show || !useRealAds) {
      setAds(null);
      setMode("crosspromo");
      return;
    }

    let cancelled = false;
    let fallbackTimer: ReturnType<typeof setTimeout> | null = null;

    void (async () => {
      try {
        const mod = await import("react-native-google-mobile-ads");
        const { ensureAdMobInitialized } = await import("@/ads/adMobBootstrap");
        await ensureAdMobInitialized();
        if (cancelled) return;
        setAds(mod);
        setMode("pending");
        fallbackTimer = setTimeout(() => {
          if (!cancelled) {
            setMode((m) => (m === "admob" ? m : "crosspromo"));
          }
        }, 4000);
      } catch {
        if (!cancelled) {
          setAds(null);
          setMode("crosspromo");
        }
      }
    })();

    return () => {
      cancelled = true;
      if (fallbackTimer) clearTimeout(fallbackTimer);
    };
  }, [show, useRealAds]);

  if (!show) return null;

  // Teste Google / web / sem fill → só ShapeScan (nunca empilha com AdMob)
  if (!useRealAds || mode === "crosspromo" || !ads) {
    return (
      <View style={styles.wrap} accessibilityLabel="Promoção ShapeScan">
        <ShapeScanCrossPromoBanner />
      </View>
    );
  }

  const { BannerAd, BannerAdSize } = ads;

  if (mode === "admob") {
    return (
      <View style={styles.wrap} accessibilityLabel="Anúncio">
        <View style={styles.adVisible}>
          <BannerAd
            unitId={bannerAdUnitId()}
            size={BannerAdSize.ANCHORED_ADAPTIVE_BANNER}
            requestOptions={{ requestNonPersonalizedAdsOnly: true }}
            onAdLoaded={() => setMode("admob")}
            onAdFailedToLoad={() => setMode("crosspromo")}
          />
        </View>
      </View>
    );
  }

  // A carregar AdMob real: ShapeScan visível; AdMob offscreen até fill
  return (
    <View style={styles.wrap} accessibilityLabel="Promoção ShapeScan">
      <ShapeScanCrossPromoBanner />
      <View style={styles.adHidden} pointerEvents="none">
        <BannerAd
          unitId={bannerAdUnitId()}
          size={BannerAdSize.ANCHORED_ADAPTIVE_BANNER}
          requestOptions={{ requestNonPersonalizedAdsOnly: true }}
          onAdLoaded={() => setMode("admob")}
          onAdFailedToLoad={() => setMode("crosspromo")}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: "100%",
    minHeight: 60,
    alignItems: "center",
    justifyContent: "center",
  },
  adVisible: {
    width: "100%",
    alignItems: "center",
  },
  adHidden: {
    position: "absolute",
    opacity: 0,
    width: 1,
    height: 1,
    overflow: "hidden",
  },
});
