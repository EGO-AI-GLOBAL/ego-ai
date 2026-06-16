import Constants from "expo-constants";
import { deleteSecureItem, getSecureItem, saveSecureItem } from "@/storage/sessionStorage";

const KEY = "ego_auth_app_version_v1";

export function currentAppVersion(): string {
  return String(Constants.expoConfig?.version || "0.0.0").trim();
}

export async function getStoredAuthAppVersion(): Promise<string | null> {
  const raw = await getSecureItem(KEY);
  return raw?.trim() || null;
}

export async function saveAuthAppVersion(version?: string): Promise<void> {
  await saveSecureItem(KEY, (version || currentAppVersion()).trim());
}

export async function clearAuthAppVersion(): Promise<void> {
  await deleteSecureItem(KEY);
}

/** Após instalar build nova, exige login uma vez (mesmo com token guardado). */
export async function shouldClearSessionForAppUpdate(): Promise<boolean> {
  const stored = await getStoredAuthAppVersion();
  if (!stored) return false;
  return stored !== currentAppVersion();
}
