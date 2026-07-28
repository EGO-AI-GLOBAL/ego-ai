import type { AccessInfo } from "@/api/types";
import { ShapeScanCrossPromoBanner } from "@/components/ShapeScanCrossPromoBanner";
import { bannerAdUnitId } from "@/constants/admob";
import { shouldShowChatAds } from "@/utils/shouldShowChatAds";
import React, { useEffect, useState } from "react";
import { Platform, StyleSheet, View } from "react-native";

type AdsModule = typeof import("react-native-google-mobile-ads");

type Props = {
  access: AccessInfo | null | undefined;
};

type FooterMode = "pending" | "admob" | "crosspromo";

/**
 * Rodapé ~60px — mesma regra do ShapeScan:
 * 1) Premium / pago → nada
 * 2) Free + AdMob com fill → banner AdMob
 * 3) Free + AdMob sem fill / erro / web → cross-promo ShapeScan
 *
 * Nunca empilha AdMob + cross-promo visíveis.
 */
export function FreeFooterBanner({ access }: Props) {
  const show = shouldShowChatAds(access);
  const [ads, setAds] = useState<AdsModule | null>(null);
  const [mode, setMode] = useState<FooterMode>("pending");

  useEffect(() => {
    if (!show) {
      setAds(null);
      setMode("pending");
      return;
    }
    if (Platform.OS === "web") {
      setAds(null);
      setMode("crosspromo");
      return;
    }

    let cancelled = false;
    let fallbackTimer: ReturnType<typeof setTimeout> | null = null;

    void (async () => {
      try {
        const mod = await import("react-native-google-mobile-ads");
        await mod.default().initialize();
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
  }, [show]);

  if (!show) return null;

  // Cross-promo final (sem fill / web / erro) — desmonta AdMob
  if (mode === "crosspromo") {
    return (
      <View style={styles.wrap} accessibilityLabel="Promoção ShapeScan">
        <ShapeScanCrossPromoBanner />
      </View>
    );
  }

  // A aguardar AdMob: já mostra ShapeScan (sem buraco); AdMob carrega em offscreen
  if (!ads) {
    return (
      <View style={styles.wrap} accessibilityLabel="Promoção ShapeScan">
        <ShapeScanCrossPromoBanner />
      </View>
    );
  }

  const { BannerAd, BannerAdSize } = ads;

  return (
    <View
      style={styles.wrap}
      accessibilityLabel={mode === "admob" ? "Anúncio" : "Promoção ShapeScan"}
    >
      {mode !== "admob" ? <ShapeScanCrossPromoBanner /> : null}
      <View
        style={mode === "admob" ? styles.adVisible : styles.adHidden}
        pointerEvents={mode === "admob" ? "auto" : "none"}
      >
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
