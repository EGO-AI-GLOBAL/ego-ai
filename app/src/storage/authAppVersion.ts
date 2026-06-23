import { deleteSecureItem, getSecureItem, saveSecureItem } from "@/storage/sessionStorage";
import { getInstalledAppVersion } from "@/utils/appVersion";

const KEY = "ego_auth_app_version_v1";

export function currentAppVersion(): string {
  return getInstalledAppVersion();
}

/** Só força novo login em mudança de versão maior (ex. 1.0 → 1.1), não em patch (1.0.36 → 1.0.37). */
function versionMajorMinor(v: string): string {
  const parts = v.trim().split(".");
  if (parts.length >= 2) return `${parts[0]}.${parts[1]}`;
  return v.trim();
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

/** Após instalar build nova, exige login uma vez só em release maior (não em patch). */
export async function shouldClearSessionForAppUpdate(): Promise<boolean> {
  const stored = await getStoredAuthAppVersion();
  if (!stored) return false;
  const current = currentAppVersion();
  if (stored === current) return false;
  return versionMajorMinor(stored) !== versionMajorMinor(current);
}
