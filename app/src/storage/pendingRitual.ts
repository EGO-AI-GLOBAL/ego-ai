import AsyncStorage from "@react-native-async-storage/async-storage";
import type { DailyRitualId } from "@/constants/dailyRituals";

const KEY = "ego_pending_ritual_v1";

const VALID: DailyRitualId[] = ["morning", "afternoon", "evening"];

function isRitual(v: string): v is DailyRitualId {
  return (VALID as string[]).includes(v);
}

export async function savePendingRitual(ritual: DailyRitualId): Promise<void> {
  try {
    await AsyncStorage.setItem(KEY, ritual);
  } catch {
    /* ignore */
  }
}

export async function consumePendingRitual(): Promise<DailyRitualId | null> {
  try {
    const v = await AsyncStorage.getItem(KEY);
    await AsyncStorage.removeItem(KEY);
    if (!v || !isRitual(v)) return null;
    return v;
  } catch {
    return null;
  }
}
