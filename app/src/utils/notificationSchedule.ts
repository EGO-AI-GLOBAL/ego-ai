import * as Notifications from "expo-notifications";

/** Expo SDK 52 exige `type` explícito — `trigger: new Date()` pode crashar no Android release. */
export function dateNotificationTrigger(at: Date): Notifications.NotificationTriggerInput {
  return {
    type: Notifications.SchedulableTriggerInputTypes.DATE,
    date: at,
  };
}
