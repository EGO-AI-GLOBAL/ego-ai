import { deleteSecureItem, getSecureItem, saveSecureItem } from "@/storage/sessionStorage";

const KEY_PREFIX = "ego_profile_phone_v1_";

function keyFor(userId: string): string {
  return `${KEY_PREFIX}${userId.trim()}`;
}

export async function saveLocalProfilePhone(userId: string, phone: string): Promise<void> {
  const uid = userId.trim();
  const ph = phone.trim();
  if (!uid || !ph) return;
  await saveSecureItem(keyFor(uid), ph);
}

export async function getLocalProfilePhone(userId: string): Promise<string | null> {
  const uid = userId.trim();
  if (!uid) return null;
  const raw = await getSecureItem(keyFor(uid));
  return raw?.trim() || null;
}

export async function clearLocalProfilePhone(userId: string): Promise<void> {
  const uid = userId.trim();
  if (!uid) return;
  await deleteSecureItem(keyFor(uid));
}
