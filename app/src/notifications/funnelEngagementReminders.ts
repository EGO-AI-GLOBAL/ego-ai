/**
 * Funil 14 dias — lembretes locais (expo-notifications), espelho ShapeScan.
 * D0/D1 check-in · máximo 1 push/dia · sem FCM.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

const LAST_OPEN_KEY = "ego_funnel_last_open_ms";
const INSTALL_DAY_KEY = "ego_funnel_install_day";
const SENT_DAY_KEY = "ego_funnel_sent_day";
const SCHEDULE_META_KEY = "ego_funnel_schedule_v1";
const CHECKED_TODAY_CACHE_KEY = "ego_funnel_checked_today_day_v1";
const ID_FUNNEL = "ego_funnel_checkin_v1";

const COPY = {
  d0: "1 check-in de 1 minuto — abre o EGO",
  d1: "Como está tua cabeça hoje? 1 toque",
  retention: "Seu monstrinho espera — 1 toque no humor de hoje.",
} as const;

export type FunnelReminderKind = "d0" | "d1" | "retention";

export type FunnelReminderPick = {
  kind: FunnelReminderKind;
  at: Date;
  body: string;
};

type ScheduleMeta = {
  kind: FunnelReminderKind;
  atMs: number;
};

function atLocalHour(base: Date, hour: number, minute = 0): Date {
  const d = new Date(base);
  d.setHours(hour, minute, 0, 0);
  return d;
}

function localDayKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function daysBetween(installDay: string, today: string): number {
  try {
    const a = new Date(`${installDay}T12:00:00`);
    const b = new Date(`${today}T12:00:00`);
    return Math.max(0, Math.round((b.getTime() - a.getTime()) / 86400000));
  } catch {
    return 0;
  }
}

/** Próximo lembrete do funil (máx. 1 por dia). */
export function pickNextFunnelReminder(input: {
  now: Date;
  alreadySentToday: boolean;
  checkedToday: boolean;
  daysSinceInstall: number;
}): FunnelReminderPick | null {
  if (input.checkedToday) return null;

  const now = input.now;
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);

  if (input.alreadySentToday) {
    const kind: FunnelReminderKind = input.daysSinceInstall < 1 ? "d1" : "retention";
    return { kind, at: atLocalHour(tomorrow, 10), body: COPY[kind] };
  }

  if (input.daysSinceInstall === 0) {
    const six = atLocalHour(now, 18);
    if (six.getTime() > now.getTime()) {
      return { kind: "d0", at: six, body: COPY.d0 };
    }
    const minDelay = new Date(now.getTime() + 3 * 60 * 60 * 1000);
    if (localDayKey(minDelay) === localDayKey(now)) {
      return { kind: "d0", at: minDelay, body: COPY.d0 };
    }
    return { kind: "d1", at: atLocalHour(tomorrow, 10), body: COPY.d1 };
  }

  if (input.daysSinceInstall === 1) {
    const ten = atLocalHour(now, 10);
    if (ten.getTime() > now.getTime()) {
      return { kind: "d1", at: ten, body: COPY.d1 };
    }
    const six = atLocalHour(now, 18);
    if (six.getTime() > now.getTime()) {
      return { kind: "d1", at: six, body: COPY.d1 };
    }
  }

  const ten = atLocalHour(now, 10);
  if (ten.getTime() > now.getTime()) {
    return { kind: "retention", at: ten, body: COPY.retention };
  }
  const six = atLocalHour(now, 18);
  if (six.getTime() > now.getTime()) {
    return { kind: "retention", at: six, body: COPY.retention };
  }
  return { kind: "retention", at: atLocalHour(tomorrow, 10), body: COPY.retention };
}

async function ensurePermissions(request = false): Promise<boolean> {
  if (Platform.OS === "web") return false;
  const cur = await Notifications.getPermissionsAsync();
  if (cur.granted || cur.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL) {
    return true;
  }
  if (!request) return false;
  const req = await Notifications.requestPermissionsAsync();
  return Boolean(
    req.granted || req.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL,
  );
}

/** Cache local — index.tsx decide chat vs Monstrinhos sem esperar bootstrap. */
export async function cacheFunnelCheckedToday(checkedToday: boolean): Promise<void> {
  try {
    const day = localDayKey(new Date());
    await AsyncStorage.setItem(CHECKED_TODAY_CACHE_KEY, checkedToday ? day : "");
  } catch {
    /* ignore */
  }
}

export async function readFunnelNeedsCheckin(): Promise<boolean> {
  try {
    const day = localDayKey(new Date());
    const cached = await AsyncStorage.getItem(CHECKED_TODAY_CACHE_KEY);
    return cached !== day;
  } catch {
    return true;
  }
}

/** Pedir permissão só após onboarding (não no 1º segundo do app). */
export async function requestFunnelNotificationPermission(): Promise<boolean> {
  return ensurePermissions(true);
}

async function cancelOurs(): Promise<void> {
  try {
    await Notifications.cancelScheduledNotificationAsync(ID_FUNNEL);
  } catch {
    /* ok */
  }
}

async function loadMeta(): Promise<ScheduleMeta | null> {
  const raw = await AsyncStorage.getItem(SCHEDULE_META_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as ScheduleMeta;
    if (!parsed?.atMs || !parsed.kind) return null;
    return parsed;
  } catch {
    return null;
  }
}

async function ensureInstallDay(): Promise<string> {
  const existing = await AsyncStorage.getItem(INSTALL_DAY_KEY);
  if (existing) return existing;
  const today = localDayKey(new Date());
  await AsyncStorage.setItem(INSTALL_DAY_KEY, today);
  return today;
}

/**
 * Chamar ao abrir o app (sessão autenticada) e após check-in Monstrinhos.
 */
export async function refreshFunnelEngagementReminders(input?: {
  checkedToday?: boolean;
  /** true só após onboarding — evita popup no 1º open. */
  requestPermission?: boolean;
}): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    await AsyncStorage.setItem(LAST_OPEN_KEY, String(Date.now()));
    if (input?.checkedToday === true) {
      await cacheFunnelCheckedToday(true);
    } else if (input?.checkedToday === false) {
      await cacheFunnelCheckedToday(false);
    }
    const ok = await ensurePermissions(Boolean(input?.requestPermission));
    if (!ok) return;

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("ego_funnel", {
        name: "Lembretes EGO-AI",
        importance: Notifications.AndroidImportance.DEFAULT,
        vibrationPattern: [0, 250],
        lightColor: "#7C6CF0",
      });
    }

    const installDay = await ensureInstallDay();
    const todayLocal = localDayKey(new Date());
    const daysSinceInstall = daysBetween(installDay, todayLocal);
    const sentDay = (await AsyncStorage.getItem(SENT_DAY_KEY)) || "";
    let alreadySentToday = sentDay === todayLocal;
    const prev = await loadMeta();
    if (!alreadySentToday && prev && prev.atMs <= Date.now()) {
      const firedDay = localDayKey(new Date(prev.atMs));
      if (firedDay === todayLocal) {
        alreadySentToday = true;
        await AsyncStorage.setItem(SENT_DAY_KEY, todayLocal);
      }
    }

    const next = pickNextFunnelReminder({
      now: new Date(),
      alreadySentToday,
      checkedToday: Boolean(input?.checkedToday),
      daysSinceInstall,
    });

    await cancelOurs();
    if (!next) return;

    await Notifications.scheduleNotificationAsync({
      identifier: ID_FUNNEL,
      content: {
        title: "EGO-AI",
        body: next.body,
        sound: undefined,
        data: {
          type: "funnel_checkin",
          kind: `engagement_${next.kind}`,
        },
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DATE,
        date: next.at,
        channelId: Platform.OS === "android" ? "ego_funnel" : undefined,
      },
    });
    await AsyncStorage.setItem(
      SCHEDULE_META_KEY,
      JSON.stringify({ kind: next.kind, atMs: next.at.getTime() } satisfies ScheduleMeta),
    );
  } catch {
    /* não bloquear o app */
  }
}

export function pingFunnelEngagementReminders(
  checkedToday?: boolean,
  requestPermission = false
): void {
  void refreshFunnelEngagementReminders({ checkedToday, requestPermission });
}

export function funnelReminderRoute(kind: string | undefined): "/(main)/daily-care" | null {
  if (
    kind === "engagement_d0" ||
    kind === "engagement_d1" ||
    kind === "engagement_retention"
  ) {
    return "/(main)/daily-care";
  }
  return null;
}
