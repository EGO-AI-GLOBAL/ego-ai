import * as Notifications from "expo-notifications";
import { router } from "expo-router";
import { useEffect } from "react";
import type { DailyRitualId } from "@/constants/dailyRituals";
import { savePendingRitual } from "@/storage/pendingRitual";

function ritualFromData(data: unknown): DailyRitualId | null {
  if (!data || typeof data !== "object") return null;
  const ritual = (data as { ritual?: string }).ritual;
  if (ritual === "morning" || ritual === "afternoon" || ritual === "evening") {
    return ritual;
  }
  return null;
}

async function openChatWithRitual(ritual: DailyRitualId): Promise<void> {
  await savePendingRitual(ritual);
  router.push("/(main)/chat");
}

/** Escuta toques nas notificações de ritual (app aberto ou em background). */
export function useDailyRitualNotifications(): void {
  useEffect(() => {
    const sub = Notifications.addNotificationResponseReceivedListener((response) => {
      const ritual = ritualFromData(response.notification.request.content.data);
      if (ritual) {
        void openChatWithRitual(ritual);
      }
    });
    return () => sub.remove();
  }, []);

  useEffect(() => {
    void (async () => {
      const last = await Notifications.getLastNotificationResponseAsync();
      if (!last) return;
      const ritual = ritualFromData(last.notification.request.content.data);
      if (ritual) {
        await openChatWithRitual(ritual);
        await Notifications.clearLastNotificationResponseAsync();
      }
    })();
  }, []);
}
