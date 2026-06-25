import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import type { WellnessJourney } from "@/api/types";
import { api } from "@/api/client";
import { isDailyCheckInEnabled } from "@/storage/chatHints";

const EGO_BOLSO_CARE_ID = "ego-de-bolso-care-18h";

/** Preferências para push do servidor (18h) — cancela lembrete local antigo. */
export async function syncEgoDeBolsoCareNotification(
  _journey?: WellnessJourney | null
): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    await Notifications.cancelScheduledNotificationAsync(EGO_BOLSO_CARE_ID);
    const ritualsOn = await isDailyCheckInEnabled();
    await api.patch("profile", {
      ui_state: { ego_daily_checkin_enabled: ritualsOn },
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
