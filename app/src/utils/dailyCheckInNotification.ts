import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import { getSession } from "@/api/client";
import { findAvatarInCatalog } from "@/constants/avatarCatalog";
import { accountPersona, isMaleAvatar } from "@/constants/personas";
import {
  pickWellnessPulseBody,
  WELLNESS_PULSE_HOURS,
  type WellnessPulseHour,
} from "@/constants/wellnessPulseMessages";
import { getLocalPersonaChoice } from "@/storage/personaPrefs";
import { isDailyCheckInEnabled } from "@/storage/chatHints";
import { ensureReminderNotificationPermission } from "@/utils/reminderNotifications";
import { resolveUserId } from "@/utils/resolveUserId";

function pulseNotificationId(hour: WellnessPulseHour): string {
  return `ego-wellness-pulse-${hour}h`;
}

async function resolveAssistantShortName(): Promise<string> {
  try {
    const session = getSession();
    const uid = resolveUserId(session, session?.user?.id);
    if (uid) {
      const local = await getLocalPersonaChoice(uid);
      if (local) {
        const persona = accountPersona(local);
        const entry = findAvatarInCatalog(persona.avatar_id);
        return (
          entry?.shortName ||
          (isMaleAvatar(persona.avatar_id) ? "Leo" : "Luna")
        );
      }
    }
  } catch {
    /* opcional */
  }
  return "EGO-AI";
}

/**
 * Pulsos de autoajuda locais: 8h, 12h, 16h e 20h (hora do telemóvel).
 * Não altera lembretes de compromissos (reminderNotifications.ts).
 */
export async function syncDailyCheckInNotification(): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    const enabled = await isDailyCheckInEnabled();
    for (const hour of WELLNESS_PULSE_HOURS) {
      const id = pulseNotificationId(hour);
      if (!enabled) {
        await Notifications.cancelScheduledNotificationAsync(id);
        continue;
      }
    }
    if (!enabled) return;

    const granted = await ensureReminderNotificationPermission();
    if (!granted) return;

    const assistantName = await resolveAssistantShortName();
    const now = new Date();

    for (const hour of WELLNESS_PULSE_HOURS) {
      const id = pulseNotificationId(hour);
      const body = pickWellnessPulseBody(hour, now);
      await Notifications.cancelScheduledNotificationAsync(id);
      await Notifications.scheduleNotificationAsync({
        identifier: id,
        content: {
          title: `${assistantName} · pulso de bem-estar`,
          body,
          sound: true,
        },
        trigger: {
          type: Notifications.SchedulableTriggerInputTypes.DAILY,
          hour,
          minute: 0,
        },
      });
    }
  } catch {
    /* opcional */
  }
}
