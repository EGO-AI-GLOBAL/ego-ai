import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "ego_session_closed_ad_day_v1";

/** A cada N sessões fechadas (check-in / PAUSA) → interstitial. */
export const SESSION_CLOSED_AD_EVERY = 2;

function localDayKey(d = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * Conta sessões FECHADAS no dia civil do aparelho.
 * A cada 2ª → interstitial (cooldown ≥90s ainda aplica no show).
 * Nunca no launch · nunca a meio do chat/respiração.
 */
export async function noteSessionClosedForAd(): Promise<boolean> {
  try {
    const day = localDayKey();
    const raw = (await AsyncStorage.getItem(KEY)) || "";
    const sep = raw.indexOf("|");
    const storedDay = sep >= 0 ? raw.slice(0, sep) : "";
    const storedCount = sep >= 0 ? Number(raw.slice(sep + 1)) || 0 : 0;
    const count = storedDay === day ? storedCount : 0;
    const next = count + 1;
    await AsyncStorage.setItem(KEY, `${day}|${next}`);
    return next % SESSION_CLOSED_AD_EVERY === 0;
  } catch {
    return false;
  }
}
