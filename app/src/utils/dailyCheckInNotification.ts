import * as Notifications from "expo-notifications";

import { Platform } from "react-native";

import { getSession } from "@/api/client";

import { findAvatarInCatalog } from "@/constants/avatarCatalog";

import {

  DAILY_RITUAL_HOURS,

  LEGACY_WELLNESS_HOURS,

  ritualNotificationCopy,

  ritualNotificationId,

  type DailyRitualId,

} from "@/constants/dailyRituals";

import { accountPersona, isMaleAvatar } from "@/constants/personas";

import { getLocalPersonaChoice } from "@/storage/personaPrefs";

import { isDailyCheckInEnabled } from "@/storage/chatHints";

import { loadStreakCache } from "@/storage/streakCache";

import { ensureReminderNotificationPermission } from "@/utils/reminderNotifications";

import { pickAvatarOfDay } from "@/utils/avatarEngagement";

import { resolveUserId } from "@/utils/resolveUserId";



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



function resolveUserDisplayName(): string | undefined {

  try {

    const session = getSession();
    const user = session?.user as { user_metadata?: Record<string, unknown>; email?: string } | undefined;
    const meta = user?.user_metadata;

    const fromMeta =

      (typeof meta?.full_name === "string" && meta.full_name.trim()) ||

      (typeof meta?.name === "string" && meta.name.trim()) ||

      (typeof meta?.first_name === "string" && meta.first_name.trim()) ||

      "";

    if (fromMeta) return fromMeta;

    const email = user?.email || "";

    if (email.includes("@")) {

      const alias = email.split("@")[0]?.trim();

      if (alias && alias.length > 2) return alias;

    }

  } catch {

    /* opcional */

  }

  return undefined;

}



async function cancelLegacyPulses(): Promise<void> {

  for (const hour of LEGACY_WELLNESS_HOURS) {

    try {

      await Notifications.cancelScheduledNotificationAsync(`ego-wellness-pulse-${hour}h`);

    } catch {

      /* ignore */

    }

  }

}



/**

 * Rituais locais: 8h briefing, 14h checkpoint, 21h descarrego (hora do telemóvel).

 * Não altera lembretes de compromissos (reminderNotifications.ts).

 */

export async function syncDailyCheckInNotification(): Promise<void> {

  if (Platform.OS === "web") return;

  try {

    const rituals = Object.keys(DAILY_RITUAL_HOURS) as DailyRitualId[];

    const enabled = await isDailyCheckInEnabled();



    await cancelLegacyPulses();



    for (const ritual of rituals) {

      const id = ritualNotificationId(ritual);

      if (!enabled) {

        await Notifications.cancelScheduledNotificationAsync(id);

      }

    }

    if (!enabled) return;



    const granted = await ensureReminderNotificationPermission();

    if (!granted) return;



    const assistantName = await resolveAssistantShortName();

    const userName = resolveUserDisplayName();

    const session = getSession();

    const uid = resolveUserId(session, session?.user?.id);

    const dayAvatar = uid ? pickAvatarOfDay(uid) : undefined;

    const avatarOfDay = dayAvatar
      ? { avatar_id: dayAvatar.avatar_id, shortName: dayAvatar.shortName }
      : undefined;

    const streakCache = await loadStreakCache();

    const streakCurrent = streakCache?.current ?? 0;
    const nightDumpStreak = streakCache?.night_dump?.current ?? 0;



    for (const ritual of rituals) {

      const hour = DAILY_RITUAL_HOURS[ritual];

      const id = ritualNotificationId(ritual);

      const copy = ritualNotificationCopy(
        ritual,
        assistantName,
        userName,
        ritual === "evening" ? streakCurrent : undefined,
        ritual === "reveal" || ritual === "evening" ? nightDumpStreak : undefined,
        ritual === "morning" ? avatarOfDay : undefined
      );

      await Notifications.cancelScheduledNotificationAsync(id);

      await Notifications.scheduleNotificationAsync({

        identifier: id,

        content: {

          title: copy.title,

          body: copy.body,

          sound: true,

          data: {
            ritual,
            screen: ritual === "reveal" ? "agenda" : "chat",
          },

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


