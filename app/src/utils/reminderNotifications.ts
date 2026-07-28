import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import type { Reminder } from "@/api/types";
import { dateNotificationTrigger } from "@/utils/notificationSchedule";

/** Minutos antes do compromisso (mesma ordem que ego_api/reminder_schedule.py). */
export const REMINDER_ALERT_OFFSETS_MINUTES = [60, 30, 10] as const;

const ANDROID_CHANNEL_ID = "ego-reminders";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

function formatLocalTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function notificationBody(
  minutesBefore: number,
  title: string,
  announce: string,
  whenLocal: string
): string {
  const t = (title || "Lembrete").trim();
  const a = (announce || "").trim();
  const when = whenLocal.trim();
  if (minutesBefore === 10) {
    return a || `${t}. Começa em dez minutos, às ${when}.`;
  }
  if (minutesBefore === 30) {
    return `Lembrete: ${t}. Daqui a trinta minutos, às ${when}.`;
  }
  if (minutesBefore === 60) {
    return `Lembrete: ${t}. Daqui a uma hora, às ${when}.`;
  }
  return t;
}

function notificationTitle(minutesBefore: number): string {
  if (minutesBefore === 60) return "EGO-AI · 1 hora antes";
  if (minutesBefore === 30) return "EGO-AI · 30 min antes";
  return "EGO-AI · 10 min antes";
}

function notificationIdentifier(reminderId: string, minutesBefore: number): string {
  return `ego-rem-${reminderId}-${minutesBefore}`;
}

async function ensureAndroidChannel(): Promise<void> {
  if (Platform.OS !== "android") return;
  try {
    await Notifications.setNotificationChannelAsync(ANDROID_CHANNEL_ID, {
      name: "Lembretes",
      importance: Notifications.AndroidImportance.HIGH,
      sound: "default",
      vibrationPattern: [0, 250, 120, 250],
    });
  } catch {
    /* canal opcional */
  }
}

export async function ensureReminderNotificationPermission(): Promise<boolean> {
  if (Platform.OS === "web") return false;
  try {
    await ensureAndroidChannel();
    const current = await Notifications.getPermissionsAsync();
    if (current.granted) return true;
    const requested = await Notifications.requestPermissionsAsync();
    return requested.granted;
  } catch {
    return false;
  }
}

/** Agenda notificações locais 1 h, 30 min e 10 min antes de cada lembrete ativo. */
export async function syncReminderLocalNotifications(
  reminders: Reminder[]
): Promise<void> {
  if (Platform.OS === "web") return;

  try {
    const granted = await ensureReminderNotificationPermission();
    if (!granted) return;

    const now = Date.now();
    const active = reminders.filter(
      (r) => r.id && r.scheduled_at && !r.dismissed
    );
    const wantedIds = new Set<string>();

    for (const r of active) {
      const rid = String(r.id);
      const scheduled = new Date(String(r.scheduled_at));
      if (Number.isNaN(scheduled.getTime())) continue;
      const title = String(r.title || "Lembrete");
      const announce = String(r.announce || "");
      const whenLocal = formatLocalTime(scheduled.toISOString());

      for (const minutesBefore of REMINDER_ALERT_OFFSETS_MINUTES) {
        const triggerAt = scheduled.getTime() - minutesBefore * 60_000;
        if (triggerAt <= now) continue;
        const id = notificationIdentifier(rid, minutesBefore);
        wantedIds.add(id);
        try {
          await Notifications.scheduleNotificationAsync({
            identifier: id,
            content: {
              title: notificationTitle(minutesBefore),
              body: notificationBody(minutesBefore, title, announce, whenLocal),
              sound: true,
              ...(Platform.OS === "android"
                ? { channelId: ANDROID_CHANNEL_ID }
                : {}),
            },
            trigger: dateNotificationTrigger(new Date(triggerAt)),
          });
        } catch {
          /* ignora lembrete individual */
        }
      }
    }

    const scheduled = await Notifications.getAllScheduledNotificationsAsync();
    for (const n of scheduled) {
      const id = n.identifier;
      if (id.startsWith("ego-rem-") && !wantedIds.has(id)) {
        try {
          await Notifications.cancelScheduledNotificationAsync(id);
        } catch {
          /* ignora cancelamento individual */
        }
      }
    }
  } catch {
    /* lembretes opcionais — não deve derrubar o app */
  }
}

export async function cancelAllReminderLocalNotifications(): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    const scheduled = await Notifications.getAllScheduledNotificationsAsync();
    await Promise.all(
      scheduled
        .filter((n) => n.identifier.startsWith("ego-rem-"))
        .map((n) => Notifications.cancelScheduledNotificationAsync(n.identifier))
    );
  } catch {
    /* opcional */
  }
}
