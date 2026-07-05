import * as Notifications from "expo-notifications";
import { router } from "expo-router";
import { useEffect } from "react";
import type { DailyRitualId } from "@/constants/dailyRituals";
import { savePendingRitual } from "@/storage/pendingRitual";

function screenFromData(data: unknown): "chat" | "agenda" | null {
  if (!data || typeof data !== "object") return null;
  const screen = (data as { screen?: string }).screen;
  if (screen === "agenda") return "agenda";
  if (screen === "chat") return "chat";
  return null;
}

function ritualFromData(data: unknown): DailyRitualId | null {
  if (!data || typeof data !== "object") return null;
  const ritual = (data as { ritual?: string }).ritual;
  if (
    ritual === "reveal" ||
    ritual === "morning" ||
    ritual === "afternoon" ||
    ritual === "evening"
  ) {
    return ritual;
  }
  return null;
}

async function openChatWithRitual(ritual: DailyRitualId): Promise<void> {
  await savePendingRitual(ritual);
  router.push("/(main)/chat");
}

function handleNotificationData(data: unknown): void {
  const ritual = ritualFromData(data);
  if (ritual === "reveal") {
    router.push("/(main)/agenda");
    return;
  }
  if (ritual) {
    void openChatWithRitual(ritual);
    return;
  }
  const type = data && typeof data === "object" ? (data as { type?: string }).type : "";
  if (type === "mood_monster") {
    router.push("/(main)/daily-care");
    return;
  }
  if (type === "pausa_ego" || type === "ego_de_bolso") {
    router.push("/(main)/wellness-journey");
    return;
  }
  if (
    type === "delegation_request" ||
    type === "entre_nos_invite" ||
    type === "entre_nos_response" ||
    type === "shared_calendar_invite" ||
    type === "shared_calendar_response" ||
    type === "shared_calendar_event" ||
    screenFromData(data) === "agenda"
  ) {
    router.push("/(main)/agenda");
  }
}

/** Escuta toques nas notificações de ritual e delegação familiar. */
export function useDailyRitualNotifications(): void {
  useEffect(() => {
    const sub = Notifications.addNotificationResponseReceivedListener((response) => {
      handleNotificationData(response.notification.request.content.data);
    });
    return () => sub.remove();
  }, []);

  useEffect(() => {
    void (async () => {
      const last = await Notifications.getLastNotificationResponseAsync();
      if (!last) return;
      handleNotificationData(last.notification.request.content.data);
      await Notifications.clearLastNotificationResponseAsync();
    })();
  }, []);
}
