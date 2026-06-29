import AsyncStorage from "@react-native-async-storage/async-storage";
import { deleteSecureItem, getSecureItem, saveSecureItem } from "@/storage/sessionStorage";

const KEY_PREFIX = "ego_profile_phone_v1_";
const SIGNUP_CACHE_PREFIX = "ego_signup_phone_async_v1_";

function keyFor(userId: string): string {
  return `${KEY_PREFIX}${userId.trim()}`;
}

function signupCacheKey(userId: string): string {
  return `${SIGNUP_CACHE_PREFIX}${userId.trim()}`;
}

export async function saveLocalProfilePhone(userId: string, phone: string): Promise<void> {
  const uid = userId.trim();
  const ph = phone.trim();
  if (!uid || !ph) return;
  await saveSecureItem(keyFor(uid), ph);
  await AsyncStorage.setItem(signupCacheKey(uid), ph);
}

export async function getLocalProfilePhone(userId: string): Promise<string | null> {
  const uid = userId.trim();
  if (!uid) return null;
  const raw = await getSecureItem(keyFor(uid));
  if (raw?.trim()) return raw.trim();
  const cached = await AsyncStorage.getItem(signupCacheKey(uid));
  return cached?.trim() || null;
}

/** Backup AsyncStorage — cadastro na mesma sessão antes do dashboard carregar. */
export async function getSignupPhoneCache(userId: string): Promise<string | null> {
  const uid = userId.trim();
  if (!uid) return null;
  const cached = await AsyncStorage.getItem(signupCacheKey(uid));
  return cached?.trim() || null;
}

export async function clearSignupPhoneCache(userId: string): Promise<void> {
  const uid = userId.trim();
  if (!uid) return;
  await AsyncStorage.removeItem(signupCacheKey(uid));
}

export async function clearLocalProfilePhone(userId: string): Promise<void> {
  const uid = userId.trim();
  if (!uid) return;
  await deleteSecureItem(keyFor(uid));
  await clearSignupPhoneCache(uid);
}
