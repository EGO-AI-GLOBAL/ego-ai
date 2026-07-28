import { Platform } from "react-native";

/**
 * AdMob — EGO-AI
 *
 * Bloco Banner (consola AdMob): nome sugerido `banner-chat-free`
 * App Android: com.egoai.app · App iOS: com.egoai.app
 *
 * IDs de TESTE oficiais do Google validam o build EAS.
 * Produção: EXPO_PUBLIC_ADMOB_* no EAS (ver VOCE-SO-FAZ-FREEMIUM-ADMOB.txt).
 *
 * @see https://developers.google.com/admob/android/test-ads
 */
export const ADMOB_BANNER_UNIT_NAME = "banner-chat-free";

export const ADMOB_TEST_ANDROID_APP_ID = "ca-app-pub-3940256099942544~3347511713";
export const ADMOB_TEST_IOS_APP_ID = "ca-app-pub-3940256099942544~1458002511";

export const ADMOB_ANDROID_APP_ID =
  process.env.EXPO_PUBLIC_ADMOB_ANDROID_APP_ID || ADMOB_TEST_ANDROID_APP_ID;

export const ADMOB_IOS_APP_ID =
  process.env.EXPO_PUBLIC_ADMOB_IOS_APP_ID || ADMOB_TEST_IOS_APP_ID;

const TEST_BANNER_ANDROID = "ca-app-pub-3940256099942544/6300978111";
const TEST_BANNER_IOS = "ca-app-pub-3940256099942544/2934735716";

/** Unit ID do banner do chat (FREE). Override via env EAS. */
export function bannerAdUnitId(): string {
  const fromEnv =
    Platform.OS === "ios"
      ? process.env.EXPO_PUBLIC_ADMOB_IOS_BANNER_ID
      : process.env.EXPO_PUBLIC_ADMOB_ANDROID_BANNER_ID;
  if (fromEnv?.trim()) return fromEnv.trim();
  return Platform.OS === "ios" ? TEST_BANNER_IOS : TEST_BANNER_ANDROID;
}

export function admobAppIdForPlatform(): string {
  return Platform.OS === "ios" ? ADMOB_IOS_APP_ID : ADMOB_ANDROID_APP_ID;
}

export function isUsingAdMobTestIds(): boolean {
  const app = admobAppIdForPlatform();
  return app === ADMOB_TEST_ANDROID_APP_ID || app === ADMOB_TEST_IOS_APP_ID;
}
