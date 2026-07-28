import * as Notifications from "expo-notifications";

/** Expo SDK 53: trigger DATE explícito — `trigger: new Date()` quebra tipagem e pode crashar no Android. */
export function dateNotificationTrigger(at: Date): Notifications.NotificationTriggerInput {
  return {
    type: Notifications.SchedulableTriggerInputTypes.DATE,
    date: at,
  };
}
