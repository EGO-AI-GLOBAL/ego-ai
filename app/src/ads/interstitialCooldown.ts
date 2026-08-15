import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "ego_admob_interstitial_last_ms_v1";
/** Cooldown mínimo entre interstitials (pausa natural). */
export const INTERSTITIAL_COOLDOWN_MS = 90_000;

let memoryLastMs = 0;

export async function canShowInterstitialNow(
  cooldownMs = INTERSTITIAL_COOLDOWN_MS
): Promise<boolean> {
  const now = Date.now();
  if (memoryLastMs > 0 && now - memoryLastMs < cooldownMs) return false;
  try {
    const raw = await AsyncStorage.getItem(KEY);
    const last = raw ? parseInt(raw, 10) : 0;
    if (Number.isFinite(last) && last > 0 && now - last < cooldownMs) {
      memoryLastMs = last;
      return false;
    }
  } catch {
    /* ignore */
  }
  return true;
}

export async function markInterstitialShown(): Promise<void> {
  const now = Date.now();
  memoryLastMs = now;
  try {
    await AsyncStorage.setItem(KEY, String(now));
  } catch {
    /* ignore */
  }
}
