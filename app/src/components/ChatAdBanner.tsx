import type { AccessInfo } from "@/api/types";
import { bannerAdUnitId } from "@/constants/admob";
import React, { useEffect, useState } from "react";
import { Platform, StyleSheet, View } from "react-native";

type AdsModule = typeof import("react-native-google-mobile-ads");

type Props = {
  access: AccessInfo | null | undefined;
};

/** Essential grátis (não pago) → anúncios. Pagantes → nada. */
export function shouldShowChatAds(access: AccessInfo | null | undefined): boolean {
  if (!access) return false;
  if (access.show_ads === false) return false;
  if (access.show_ads === true) return true;
  const tier = access.plan_tier || "essential";
  return tier === "essential" && access.is_pro !== true;
}

/**
 * Banner AdMob fixo acima do ChatComposer.
 * Só monta em iOS/Android nativo e no plano freemium.
 */
export function ChatAdBanner({ access }: Props) {
  const [ads, setAds] = useState<AdsModule | null>(null);
  const show = shouldShowChatAds(access);

  useEffect(() => {
    if (!show || Platform.OS === "web") {
      setAds(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const mod = await import("react-native-google-mobile-ads");
        await mod.default().initialize();
        if (!cancelled) setAds(mod);
      } catch {
        if (!cancelled) setAds(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [show]);

  if (!show || Platform.OS === "web" || !ads) return null;

  const { BannerAd, BannerAdSize } = ads;

  return (
    <View style={styles.wrap} accessibilityLabel="Anúncio">
      <BannerAd
        unitId={bannerAdUnitId()}
        size={BannerAdSize.ANCHORED_ADAPTIVE_BANNER}
        requestOptions={{ requestNonPersonalizedAdsOnly: true }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: "100%",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 50,
  },
});
