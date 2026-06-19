import AsyncStorage from "@react-native-async-storage/async-storage";
import type { StreakInfo } from "@/api/types";

const KEY = "ego-streak-cache";

export async function saveStreakCache(streak: StreakInfo | undefined): Promise<void> {
  if (!streak) return;
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(streak));
  } catch {
    /* opcional */
  }
}

export async function loadStreakCache(): Promise<StreakInfo | null> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StreakInfo;
    return parsed && typeof parsed.current === "number" ? parsed : null;
  } catch {
    return null;
  }
}
