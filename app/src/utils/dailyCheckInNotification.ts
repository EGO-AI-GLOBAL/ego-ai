import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import { isDailyCheckInEnabled } from "@/storage/chatHints";
import { ensureReminderNotificationPermission } from "@/utils/reminderNotifications";

const CHECKIN_ID = "ego-daily-checkin-20h";

export async function syncDailyCheckInNotification(): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    const enabled = await isDailyCheckInEnabled();
    if (!enabled) {
      await Notifications.cancelScheduledNotificationAsync(CHECKIN_ID);
      return;
    }
    const granted = await ensureReminderNotificationPermission();
    if (!granted) return;

    await Notifications.cancelScheduledNotificationAsync(CHECKIN_ID);
    await Notifications.scheduleNotificationAsync({
      identifier: CHECKIN_ID,
      content: {
        title: "EGO-AI",
        body: "Como foi o seu dia? Abra o chat e conte ao Leo ou à Luna.",
        sound: true,
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DAILY,
        hour: 20,
        minute: 0,
      },
    });
  } catch {
    /* opcional */
  }
}
