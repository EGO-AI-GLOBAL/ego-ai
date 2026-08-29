/**
 * «Volta amanhã às Xh» — notificação local após check-in do dia.
 * Deep link → daily-care (mesmo type funnel_checkin).
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

const ID_COMEBACK = "ego_comeback_tomorrow_v1";
const HOUR_KEY = "ego_comeback_hour_v1";
/** Hora default Finch-like (manhã). */
export const DEFAULT_COMEBACK_HOUR = 10;

export async function getComebackHour(): Promise<number> {
  try {
    const raw = await AsyncStorage.getItem(HOUR_KEY);
    const n = raw ? parseInt(raw, 10) : NaN;
    if (Number.isFinite(n) && n >= 6 && n <= 22) return n;
  } catch {
    /* ok */
  }
  return DEFAULT_COMEBACK_HOUR;
}

export async function setComebackHour(hour: number): Promise<void> {
  const h = Math.min(22, Math.max(6, Math.round(hour)));
  try {
    await AsyncStorage.setItem(HOUR_KEY, String(h));
  } catch {
    /* ok */
  }
}

function tomorrowAtHour(hour: number): Date {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(hour, 0, 0, 0);
  return d;
}

/** Agenda (ou reagenda) «volta amanhã às Xh». Cancela o anterior. */
export async function scheduleComeBackTomorrow(opts?: {
  hour?: number;
  body?: string;
}): Promise<number> {
  if (Platform.OS === "web") return DEFAULT_COMEBACK_HOUR;
  const hour = opts?.hour ?? (await getComebackHour());
  await setComebackHour(hour);
  try {
    await Notifications.cancelScheduledNotificationAsync(ID_COMEBACK);
  } catch {
    /* ok */
  }
  const ok = await Notifications.getPermissionsAsync();
  const granted =
    ok.granted || ok.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL;
  if (!granted) return hour;

  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("ego_funnel", {
      name: "Lembretes EGO-AI",
      importance: Notifications.AndroidImportance.DEFAULT,
      vibrationPattern: [0, 250],
      lightColor: "#7C6CF0",
    });
  }

  const at = tomorrowAtHour(hour);
  const body =
    opts?.body?.trim() ||
    `Seu monstrinho espera — 1 toque no humor · volta às ${hour}h.`;

  await Notifications.scheduleNotificationAsync({
    identifier: ID_COMEBACK,
    content: {
      title: "EGO-AI",
      body,
      data: { type: "funnel_checkin", kind: "engagement_comeback" },
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DATE,
      date: at,
      channelId: Platform.OS === "android" ? "ego_funnel" : undefined,
    },
  });
  return hour;
}

export function comebackLabel(hour: number): string {
  return `Volta amanhã às ${hour}h — 1 toque no humor`;
}
