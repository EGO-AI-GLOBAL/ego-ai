import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import type { PausaEgoInfo } from "@/api/types";
import { isDailyCheckInEnabled } from "@/storage/chatHints";
import { ensureReminderNotificationPermission } from "@/utils/reminderNotifications";
import { formatPausaDuration, resolveDailyExercise } from "@/utils/pausaDailyExercise";

const MORNING_ID = "pausa-ego-morning-10h";
const EVENING_ID = "pausa-ego-evening-18h";
const MORNING_HOUR = 10;
const EVENING_HOUR = 18;

function pausaNotificationCopy(pausa: PausaEgoInfo, slot: "morning" | "evening"): {
  title: string;
  body: string;
} {
  const daily = resolveDailyExercise(pausa);
  const streak = pausa.streak_current ?? 0;
  const dur = formatPausaDuration(daily.duration_seconds);
  if (slot === "morning") {
    return {
      title: `${daily.emoji} PAUSA de hoje`,
      body: `${daily.title} · ${dur} — casa, escritório ou onde estiver`,
    };
  }
  if (streak >= 2) {
    return {
      title: `${daily.emoji} Falta sua PAUSA`,
      body: `${daily.title} · sequência 🔥 ${streak} dias`,
    };
  }
  return {
    title: `${daily.emoji} Pausa da tarde`,
    body: `${daily.title} · ${dur} — em casa, no trabalho ou na rua`,
  };
}

async function scheduleDaily(
  id: string,
  hour: number,
  copy: { title: string; body: string }
): Promise<void> {
  await Notifications.cancelScheduledNotificationAsync(id);
  await Notifications.scheduleNotificationAsync({
    identifier: id,
    content: {
      title: copy.title,
      body: copy.body,
      sound: true,
      data: {
        type: "pausa_ego",
        screen: "wellness-journey",
      },
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DAILY,
      hour,
      minute: 0,
    },
  });
}

/** Lembretes locais 10h/18h — retenção mesmo offline (complementa push servidor). */
export async function syncPausaLocalNotifications(
  pausa?: PausaEgoInfo | null
): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    await Notifications.cancelScheduledNotificationAsync(MORNING_ID);
    await Notifications.cancelScheduledNotificationAsync(EVENING_ID);
    if (!pausa || pausa.today_done) return;

    const ritualsOn = await isDailyCheckInEnabled();
    if (!ritualsOn) return;

    const granted = await ensureReminderNotificationPermission();
    if (!granted) return;

    await scheduleDaily(MORNING_ID, MORNING_HOUR, pausaNotificationCopy(pausa, "morning"));
    await scheduleDaily(EVENING_ID, EVENING_HOUR, pausaNotificationCopy(pausa, "evening"));
  } catch {
    /* opcional */
  }
}

export async function cancelPausaLocalNotifications(): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    await Notifications.cancelScheduledNotificationAsync(MORNING_ID);
    await Notifications.cancelScheduledNotificationAsync(EVENING_ID);
  } catch {
    /* ignore */
  }
}
