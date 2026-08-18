import { useCallback, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import { trackRewardedOptIn } from "@/analytics/egoAnalytics";
import { ensureAdMobInitialized } from "@/ads/adMobBootstrap";
import {
  ADMOB_REWARDED_UNIT_ID,
  adMobRewardedEnabled,
} from "@/constants/admob";

type Options = {
  /** false = Premium → sem ads. */
  enabled: boolean;
};

type AdsTypes = typeof import("react-native-google-mobile-ads");

/**
 * Rewarded só com opt-in do utilizador (nunca auto-play).
 * Sem unit / sem fill → onFail; com reward → onEarned.
 */
export function useRewardedOptIn({ enabled }: Options) {
  const adRef = useRef<InstanceType<AdsTypes["RewardedAd"]> | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [noFill, setNoFill] = useState(false);
  const earnedRef = useRef(false);
  const onEarnedRef = useRef<(() => void) | null>(null);
  const onFailRef = useRef<(() => void) | null>(null);
  const unsubsRef = useRef<Array<() => void>>([]);
  const admobOn = enabled && adMobRewardedEnabled() && Platform.OS !== "web";

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
    setNoFill(false);
  }, []);

  const loadAd = useCallback(async () => {
    if (!admobOn || !ADMOB_REWARDED_UNIT_ID) {
      setNoFill(true);
      return;
    }
    await ensureAdMobInitialized();
    teardown();
    let filled = false;
    const fillTimer = setTimeout(() => {
      if (!filled) setNoFill(true);
    }, 4000);
    try {
      const {
        RewardedAd,
        RewardedAdEventType,
        AdEventType,
      } = await import("react-native-google-mobile-ads");
      const ad = RewardedAd.createForAdRequest(ADMOB_REWARDED_UNIT_ID, {
        requestNonPersonalizedAdsOnly: true,
      });
      adRef.current = ad;
      unsubsRef.current = [
        ad.addAdEventListener(RewardedAdEventType.LOADED, () => {
          filled = true;
          clearTimeout(fillTimer);
          setNoFill(false);
          setLoaded(true);
        }),
        ad.addAdEventListener(RewardedAdEventType.EARNED_REWARD, () => {
          earnedRef.current = true;
        }),
        ad.addAdEventListener(AdEventType.ERROR, () => {
          filled = true;
          clearTimeout(fillTimer);
          setLoaded(false);
          setNoFill(true);
          const fail = onFailRef.current;
          onFailRef.current = null;
          onEarnedRef.current = null;
          fail?.();
        }),
        ad.addAdEventListener(AdEventType.CLOSED, () => {
          setLoaded(false);
          const earned = earnedRef.current;
          earnedRef.current = false;
          const ok = onEarnedRef.current;
          const fail = onFailRef.current;
          onEarnedRef.current = null;
          onFailRef.current = null;
          if (earned) {
            trackRewardedOptIn("earned");
            ok?.();
          } else {
            trackRewardedOptIn("dismissed");
            fail?.();
          }
          try {
            ad.load();
          } catch {
            /* ok */
          }
        }),
        () => clearTimeout(fillTimer),
      ];
      ad.load();
    } catch {
      clearTimeout(fillTimer);
      setLoaded(false);
      setNoFill(true);
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

  const showOptIn = useCallback(
    (opts: { onEarned: () => void; onFail?: () => void }): boolean => {
      if (!admobOn) {
        opts.onFail?.();
        return false;
      }
      const ad = adRef.current;
      if (!ad || !loaded) {
        opts.onFail?.();
        return false;
      }
      earnedRef.current = false;
      onEarnedRef.current = opts.onEarned;
      onFailRef.current = opts.onFail || null;
      trackRewardedOptIn("started");
      try {
        void ad.show();
        return true;
      } catch {
        onEarnedRef.current = null;
        onFailRef.current = null;
        opts.onFail?.();
        return false;
      }
    },
    [admobOn, loaded]
  );

  return { loaded, ready: admobOn && loaded, noFill, showOptIn, reload: loadAd };
}
