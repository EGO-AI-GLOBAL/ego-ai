import { useCallback, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import { trackInterstitial } from "@/analytics/egoAnalytics";
import { ensureAdMobInitialized } from "@/ads/adMobBootstrap";
import {
  canShowInterstitialNow,
  markInterstitialShown,
} from "@/ads/interstitialCooldown";
import {
  ADMOB_INTERSTITIAL_UNIT_ID,
  adMobInterstitialEnabled,
} from "@/constants/admob";

type Options = {
  /** false = Premium / sem ads → sem preload. */
  enabled: boolean;
};

type AdsTypes = typeof import("react-native-google-mobile-ads");

/**
 * Interstitial só em pausa natural (check-in / PAUSA).
 * Cooldown ≥90s. Sem fill / erro / cooldown → onDone(false) para o pai mostrar ShapeScan.
 */
export function useNaturalPauseInterstitial({ enabled }: Options) {
  const adRef = useRef<InstanceType<AdsTypes["InterstitialAd"]> | null>(null);
  const [loaded, setLoaded] = useState(false);
  const onClosedRef = useRef<((didShowAd: boolean) => void) | null>(null);
  const unsubsRef = useRef<Array<() => void>>([]);
  const admobOn =
    enabled && adMobInterstitialEnabled() && Platform.OS !== "web";

  const teardown = useCallback(() => {
    for (const u of unsubsRef.current) {
      try {
        u();
      } catch {
        /* ok */
      }
    }
    unsubsRef.current = [];
    adRef.current = null;
    setLoaded(false);
  }, []);

  const loadAd = useCallback(async () => {
    if (!admobOn || !ADMOB_INTERSTITIAL_UNIT_ID) return;
    await ensureAdMobInitialized();
    teardown();
    try {
      const {
        InterstitialAd,
        AdEventType,
      } = await import("react-native-google-mobile-ads");
      const ad = InterstitialAd.createForAdRequest(ADMOB_INTERSTITIAL_UNIT_ID, {
        requestNonPersonalizedAdsOnly: true,
      });
      adRef.current = ad;
      unsubsRef.current = [
        ad.addAdEventListener(AdEventType.LOADED, () => setLoaded(true)),
        ad.addAdEventListener(AdEventType.ERROR, () => setLoaded(false)),
        ad.addAdEventListener(AdEventType.CLOSED, () => {
          setLoaded(false);
          const cb = onClosedRef.current;
          onClosedRef.current = null;
          cb?.(true);
          try {
            ad.load();
          } catch {
            /* ok */
          }
        }),
      ];
      ad.load();
    } catch {
      setLoaded(false);
    }
  }, [admobOn, teardown]);

  useEffect(() => {
    if (!admobOn) {
      teardown();
      return;
    }
    void loadAd();
    return () => teardown();
  }, [admobOn, loadAd, teardown]);

  const show = useCallback(
    (onDone: (didShowAd: boolean) => void): void => {
      const finish = (didShowAd: boolean) => {
        try {
          onDone(didShowAd);
        } catch {
          /* ok */
        }
      };

      if (!admobOn) {
        finish(false);
        return;
      }

      void (async () => {
        const ok = await canShowInterstitialNow();
        if (!ok) {
          trackInterstitial("skipped_cooldown");
          finish(false);
          return;
        }
        const ad = adRef.current;
        if (ad && loaded) {
          onClosedRef.current = finish;
          try {
            await markInterstitialShown();
            trackInterstitial("shown");
            void ad.show();
            return;
          } catch {
            onClosedRef.current = null;
            trackInterstitial("no_fill");
            finish(false);
            return;
          }
        }
        trackInterstitial("no_fill");
        finish(false);
      })();
    },
    [admobOn, loaded]
  );

  return { loaded, show, reload: loadAd };
}
