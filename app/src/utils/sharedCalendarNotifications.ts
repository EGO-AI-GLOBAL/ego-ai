import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import type { SharedCalendar, SharedCalendarEvent } from "@/api/types";
import {
  REMINDER_ALERT_OFFSETS_MINUTES,
  ensureReminderNotificationPermission,
} from "@/utils/reminderNotifications";

const ANDROID_CHANNEL_ID = "ego-shared-calendars";
const SEEN_EVENTS_KEY = "ego_seen_shared_calendar_events_v1";

function formatWhen(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

async function ensureAndroidChannel(): Promise<void> {
  if (Platform.OS !== "android") return;
  try {
    await Notifications.setNotificationChannelAsync(ANDROID_CHANNEL_ID, {
      name: "Agendas compartilhadas",
      importance: Notifications.AndroidImportance.HIGH,
      sound: "default",
      vibrationPattern: [0, 250, 120, 250],
    });
  } catch {
    /* canal opcional */
  }
}

function scheduleId(eventId: string, minutesBefore: number): string {
  return `ego-sc-${eventId}-${minutesBefore}`;
}

/** Aviso imediato no aparelho (quem criou ou quem sincronizou e viu evento novo). */
export async function presentSharedCalendarEventNow(opts: {
  calendarName: string;
  title: string;
  scheduledAt: string;
  actorLabel?: string;
}): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    const granted = await ensureReminderNotificationPermission();
    if (!granted) return;
    await ensureAndroidChannel();
    const cal = (opts.calendarName || "Agenda").trim();
    const when = formatWhen(opts.scheduledAt);
    const who = (opts.actorLabel || "Alguém").trim();
    const title = (opts.title || "Compromisso").trim();
    let body = `${who} marcou: ${title}`;
    if (when) body += ` · ${when}`;
    await Notifications.scheduleNotificationAsync({
      identifier: `ego-sc-alert-${Date.now()}`,
      content: {
        title: `📅 ${cal}`,
        body,
        sound: true,
        ...(Platform.OS === "android" ? { channelId: ANDROID_CHANNEL_ID } : {}),
      },
      trigger: null,
    });
  } catch {
    /* aviso opcional */
  }
}

async function loadSeenEventIds(): Promise<Set<string>> {
  try {
    const raw = await AsyncStorage.getItem(SEEN_EVENTS_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as unknown;
    if (!Array.isArray(arr)) return new Set();
    return new Set(arr.map(String));
  } catch {
    return new Set();
  }
}

async function saveSeenEventIds(ids: Set<string>): Promise<void> {
  try {
    const trimmed = [...ids].slice(-500);
    await AsyncStorage.setItem(SEEN_EVENTS_KEY, JSON.stringify(trimmed));
  } catch {
    /* persistência opcional */
  }
}

/**
 * Notifica compromissos novos criados por outros (quando o app sincroniza o painel).
 */
export async function notifyNewSharedEventsFromOthers(
  calendars: SharedCalendar[],
  myUserId: string
): Promise<void> {
  if (Platform.OS === "web" || !myUserId) return;
  try {
    const seen = await loadSeenEventIds();
    const firstSync = seen.size === 0;
    const nextSeen = new Set(seen);

    for (const cal of calendars) {
      const calName = (cal.name || "Agenda compartilhada").trim();
      for (const ev of cal.events ?? []) {
        const eid = String(ev.id || "");
        if (!eid) continue;
        if (!seen.has(eid)) {
          nextSeen.add(eid);
          const creator = String(ev.created_by_user_id || "");
          if (!firstSync && creator && creator !== myUserId) {
            await presentSharedCalendarEventNow({
              calendarName: calName,
              title: String(ev.title || "Compromisso"),
              scheduledAt: String(ev.scheduled_at || ""),
            });
          }
        }
      }
    }

    await saveSeenEventIds(nextSeen);
  } catch {
    /* notificações opcionais — não deve derrubar o app */
  }
}

/** Lembretes locais 1 h / 30 min / 10 min antes (como lembretes pessoais). */
export async function syncSharedCalendarLocalNotifications(
  calendars: SharedCalendar[]
): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    const granted = await ensureReminderNotificationPermission();
    if (!granted) return;
    await ensureAndroidChannel();

    const now = Date.now();
    const wanted = new Set<string>();

    for (const cal of calendars) {
      const calName = (cal.name || "Agenda").trim();
      for (const ev of cal.events ?? []) {
        if (ev.dismissed) continue;
        const eid = String(ev.id || "");
        const scheduled = new Date(String(ev.scheduled_at || ""));
        if (!eid || Number.isNaN(scheduled.getTime())) continue;
        const title = String(ev.title || "Reunião");
        const whenLocal = formatWhen(scheduled.toISOString());

        for (const minutesBefore of REMINDER_ALERT_OFFSETS_MINUTES) {
          const triggerAt = scheduled.getTime() - minutesBefore * 60_000;
          if (triggerAt <= now) continue;
          const id = scheduleId(eid, minutesBefore);
          wanted.add(id);
          let offsetLabel = "10 min";
          if (minutesBefore === 60) offsetLabel = "1 h";
          if (minutesBefore === 30) offsetLabel = "30 min";
          try {
            await Notifications.scheduleNotificationAsync({
              identifier: id,
              content: {
                title: `📅 ${calName} · ${offsetLabel} antes`,
                body: `${title}${whenLocal ? ` · ${whenLocal}` : ""}`,
                sound: true,
                ...(Platform.OS === "android"
                  ? { channelId: ANDROID_CHANNEL_ID }
                  : {}),
              },
              trigger: new Date(triggerAt),
            });
          } catch {
            /* ignora lembrete individual */
          }
        }
      }
    }

    const scheduled = await Notifications.getAllScheduledNotificationsAsync();
    for (const n of scheduled) {
      if (n.identifier.startsWith("ego-sc-") && !wanted.has(n.identifier)) {
        try {
          await Notifications.cancelScheduledNotificationAsync(n.identifier);
        } catch {
          /* ignora cancelamento individual */
        }
      }
    }
  } catch {
    /* lembretes opcionais */
  }
}

export async function markSharedCalendarEventsSeen(
  calendars: SharedCalendar[]
): Promise<void> {
  try {
    const seen = await loadSeenEventIds();
    for (const cal of calendars) {
      for (const ev of cal.events ?? []) {
        const eid = String(ev.id || "");
        if (eid) seen.add(eid);
      }
    }
    await saveSeenEventIds(seen);
  } catch {
    /* opcional */
  }
}
