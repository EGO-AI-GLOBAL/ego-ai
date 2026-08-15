import { Platform } from "react-native";
import { TestIds } from "react-native-google-mobile-ads";

/**
 * AdMob — EGO-AI (publisher pub-6748248434426888)
 *
 * Blocos sugeridos na consola:
 *   banner-chat-free · interstitial-pause-free · rewarded-dica-dia
 *
 * Regra free:
 * 1. Premium → zero ads
 * 2. Unit AdMob real + fill → AdMob
 * 3. Sem fill / erro → fallback ShapeScan (banner)
 *
 * __DEV__ → TestIds Google. Produção → só env (nunca TestIds na loja).
 */

export const ADMOB_BANNER_UNIT_NAME = "banner-chat-free";
export const ADMOB_INTERSTITIAL_UNIT_NAME = "interstitial-pause-free";
export const ADMOB_REWARDED_UNIT_NAME = "rewarded-dica-dia";

export const ADMOB_TEST_ANDROID_APP_ID = "ca-app-pub-3940256099942544~3347511713";
export const ADMOB_TEST_IOS_APP_ID = "ca-app-pub-3940256099942544~1458002511";

export const ADMOB_ANDROID_APP_ID =
  process.env.EXPO_PUBLIC_ADMOB_ANDROID_APP_ID || ADMOB_TEST_ANDROID_APP_ID;

export const ADMOB_IOS_APP_ID =
  process.env.EXPO_PUBLIC_ADMOB_IOS_APP_ID || ADMOB_TEST_IOS_APP_ID;

const TEST_BANNER_ANDROID = "ca-app-pub-3940256099942544/6300978111";
const TEST_BANNER_IOS = "ca-app-pub-3940256099942544/2934735716";

const envBanner =
  Platform.OS === "ios"
    ? process.env.EXPO_PUBLIC_ADMOB_IOS_BANNER_ID
    : process.env.EXPO_PUBLIC_ADMOB_ANDROID_BANNER_ID;

const envInterstitial =
  Platform.OS === "ios"
    ? process.env.EXPO_PUBLIC_ADMOB_IOS_INTERSTITIAL_ID
    : process.env.EXPO_PUBLIC_ADMOB_ANDROID_INTERSTITIAL_ID;

const envRewarded =
  Platform.OS === "ios"
    ? process.env.EXPO_PUBLIC_ADMOB_IOS_REWARDED_ID
    : process.env.EXPO_PUBLIC_ADMOB_ANDROID_REWARDED_ID;

function isGoogleTestUnit(id: string): boolean {
  const t = (id || "").trim();
  return (
    !t ||
    t === TestIds.BANNER ||
    t === TestIds.INTERSTITIAL ||
    t === TestIds.REWARDED ||
    t.includes("3940256099942544")
  );
}

/** Unit ID do banner do chat (FREE). */
export function bannerAdUnitId(): string {
  if (__DEV__) return TestIds.BANNER;
  const fromEnv = (envBanner || "").trim();
  if (fromEnv) return fromEnv;
  return Platform.OS === "ios" ? TEST_BANNER_IOS : TEST_BANNER_ANDROID;
}

/**
 * Interstitial: __DEV__ = teste Google; produção = só se env estiver definido.
 * Sem ID em produção → string vazia → interstitial desligado (UX segue).
 */
export const ADMOB_INTERSTITIAL_UNIT_ID = __DEV__
  ? TestIds.INTERSTITIAL
  : (envInterstitial || "").trim();

export const ADMOB_REWARDED_UNIT_ID = __DEV__
  ? TestIds.REWARDED
  : (envRewarded || "").trim();

export function admobAppIdForPlatform(): string {
  return Platform.OS === "ios" ? ADMOB_IOS_APP_ID : ADMOB_ANDROID_APP_ID;
}

export function isUsingAdMobTestIds(): boolean {
  if (__DEV__) return true;
  const app = admobAppIdForPlatform();
  return app === ADMOB_TEST_ANDROID_APP_ID || app === ADMOB_TEST_IOS_APP_ID;
}

export function adMobBannerEnabled(): boolean {
  if (__DEV__) return true;
  return !isGoogleTestUnit(bannerAdUnitId());
}

export function adMobInterstitialEnabled(): boolean {
  if (__DEV__) return true;
  return !isGoogleTestUnit(ADMOB_INTERSTITIAL_UNIT_ID);
}

export function adMobRewardedEnabled(): boolean {
  if (__DEV__) return true;
  return !isGoogleTestUnit(ADMOB_REWARDED_UNIT_ID);
}
