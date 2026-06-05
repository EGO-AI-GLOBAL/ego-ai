import AsyncStorage from "@react-native-async-storage/async-storage";

const LAST_INTENT_KEY = "ego_last_schedule_intent_v1";
const CHECKIN_KEY = "ego_daily_checkin_enabled_v1";

export async function saveLastUserIntent(text: string): Promise<void> {
  const t = text.trim();
  if (!t || t.length < 4) return;
  if (/resumo da minha semana/i.test(t)) return;
  await AsyncStorage.setItem(LAST_INTENT_KEY, t.slice(0, 500));
}

export async function loadLastUserIntent(): Promise<string | null> {
  const v = await AsyncStorage.getItem(LAST_INTENT_KEY);
  return v?.trim() || null;
}

export async function isDailyCheckInEnabled(): Promise<boolean> {
  const v = await AsyncStorage.getItem(CHECKIN_KEY);
  return v !== "0";
}

export async function setDailyCheckInEnabled(enabled: boolean): Promise<void> {
  await AsyncStorage.setItem(CHECKIN_KEY, enabled ? "1" : "0");
}
