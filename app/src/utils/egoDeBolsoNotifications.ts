import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import type { WellnessJourney } from "@/api/types";
import { isDailyCheckInEnabled } from "@/storage/chatHints";
import {
  companionNeedsCare,
  egoDeBolsoNotificationCopy,
} from "@/utils/egoDeBolsoCompanionMood";
import { ensureReminderNotificationPermission } from "@/utils/reminderNotifications";

const EGO_BOLSO_CARE_ID = "ego-de-bolso-care-18h";
const CARE_HOUR = 18;

/** Push diário 18h — missão EGO de Bolso pendente (Fase 2 retenção). */
export async function syncEgoDeBolsoCareNotification(
  journey?: WellnessJourney | null
): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    await Notifications.cancelScheduledNotificationAsync(EGO_BOLSO_CARE_ID);
    if (!journey || !companionNeedsCare(journey)) return;

    const ritualsOn = await isDailyCheckInEnabled();
    if (!ritualsOn) return;

    const granted = await ensureReminderNotificationPermission();
    if (!granted) return;

    const copy = egoDeBolsoNotificationCopy(journey);
    await Notifications.scheduleNotificationAsync({
      identifier: EGO_BOLSO_CARE_ID,
      content: {
        title: copy.title,
        body: copy.body,
        sound: true,
        data: {
          type: "ego_de_bolso",
          screen: copy.screen,
        },
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DAILY,
        hour: CARE_HOUR,
        minute: 0,
      },
    });
  } catch {
    /* opcional */
  }
}

export async function cancelEgoDeBolsoCareNotification(): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    await Notifications.cancelScheduledNotificationAsync(EGO_BOLSO_CARE_ID);
  } catch {
    /* ignore */
  }
}
