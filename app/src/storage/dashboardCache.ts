import AsyncStorage from "@react-native-async-storage/async-storage";
import type { DashboardData } from "@/api/types";

const KEY_PREFIX = "ego-dashboard-cache-v1:";

/** Campos suficientes para pintar Monstrinhos / chat / menu sem rede. */
export type DashboardCacheSnapshot = Pick<
  DashboardData,
  | "me"
  | "access"
  | "daily_care"
  | "streak"
  | "wellness_journey"
  | "pausa_ego"
  | "reminders"
  | "agenda"
>;

function cacheKey(uid: string): string {
  return `${KEY_PREFIX}${uid.trim()}`;
}

export async function saveDashboardCache(
  uid: string,
  dashboard: DashboardData
): Promise<void> {
  const id = uid.trim();
  if (!id) return;
  const snapshot: DashboardCacheSnapshot = {
    me: dashboard.me,
    access: dashboard.access,
    daily_care: dashboard.daily_care,
    streak: dashboard.streak,
    wellness_journey: dashboard.wellness_journey,
    pausa_ego: dashboard.pausa_ego,
    reminders: dashboard.reminders,
    agenda: dashboard.agenda,
  };
  try {
    await AsyncStorage.setItem(cacheKey(id), JSON.stringify(snapshot));
  } catch {
    /* opcional */
  }
}

export async function loadDashboardCache(
  uid: string
): Promise<Partial<DashboardData> | null> {
  const id = uid.trim();
  if (!id) return null;
  try {
    const raw = await AsyncStorage.getItem(cacheKey(id));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as DashboardCacheSnapshot;
    if (!parsed || typeof parsed !== "object") return null;
    return parsed;
  } catch {
    return null;
  }
}

export async function clearDashboardCache(uid: string): Promise<void> {
  const id = uid.trim();
  if (!id) return;
  try {
    await AsyncStorage.removeItem(cacheKey(id));
  } catch {
    /* ok */
  }
}
