import { Platform } from "react-native";

/**
 * App IDs oficiais de TESTE do Google (validam o build EAS).
 * Substitui pelos teus reais via EXPO_PUBLIC_ADMOB_*_APP_ID antes da loja com monetização.
 * @see https://developers.google.com/admob/android/test-ads
 */
export const ADMOB_TEST_ANDROID_APP_ID = "ca-app-pub-3940256099942544~3347511713";
export const ADMOB_TEST_IOS_APP_ID = "ca-app-pub-3940256099942544~1458002511";

export const ADMOB_ANDROID_APP_ID =
  process.env.EXPO_PUBLIC_ADMOB_ANDROID_APP_ID || ADMOB_TEST_ANDROID_APP_ID;

export const ADMOB_IOS_APP_ID =
  process.env.EXPO_PUBLIC_ADMOB_IOS_APP_ID || ADMOB_TEST_IOS_APP_ID;

const TEST_BANNER_ANDROID = "ca-app-pub-3940256099942544/6300978111";
const TEST_BANNER_IOS = "ca-app-pub-3940256099942544/2934735716";

export function bannerAdUnitId(): string {
  const fromEnv =
    Platform.OS === "ios"
      ? process.env.EXPO_PUBLIC_ADMOB_IOS_BANNER_ID
      : process.env.EXPO_PUBLIC_ADMOB_ANDROID_BANNER_ID;
  if (fromEnv?.trim()) return fromEnv.trim();
  return Platform.OS === "ios" ? TEST_BANNER_IOS : TEST_BANNER_ANDROID;
}
