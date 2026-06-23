import AsyncStorage from "@react-native-async-storage/async-storage";

const DISMISS_KEY = "ego_update_banner_dismissed_v1";

export async function getUpdateBannerDismissedVersion(): Promise<string | null> {
  const raw = await AsyncStorage.getItem(DISMISS_KEY);
  return raw?.trim() || null;
}

export async function setUpdateBannerDismissedVersion(version: string): Promise<void> {
  await AsyncStorage.setItem(DISMISS_KEY, version.trim());
}

export async function clearUpdateBannerDismissedVersion(): Promise<void> {
  await AsyncStorage.removeItem(DISMISS_KEY);
}
