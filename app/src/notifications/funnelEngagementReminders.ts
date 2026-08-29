/**
 * Funil retenção — D0–D7 (novos) + Aha contínuo (quem já tem o app).
 * Máx 1 push/dia · deep link → daily-care.
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
/** One-shot: base instalada (já tinha o app antes desta versão). */
const ID_AHA_BASE = "ego_aha_base_instalada_v1";
const AHA_BASE_CAMPAIGN_KEY = "ego_aha_base_instalada_campaign_v1";
const LAST_SEEN_VERSION_KEY = "ego_funnel_last_seen_version_v1";

const COPY = {
  d0: "1 check-in de 1 minuto — abre o EGO",
  d1: "Como está tua cabeça hoje? 1 toque",
  d2: "Dia 2 — o monstrinho sente a tua falta. 1 toque.",
  d3: "3 dias fazem sequência. Como estás hoje?",
  d4: "Meio da semana — 1 minuto no jardim.",
  d5: "Quase lá: 1 toque e a ofensiva segue.",
  d6: "Amanhã fecha a semana — check-in de 1 minuto.",
  d7: "Dia 7 — celebra com 1 toque no humor.",
  /** Quem já tem o app (após D7) — Aha contínuo. */
  aha: "1 check-in de 1 minuto — o monstrinho reage já",
  aha_b: "Como está tua cabeça hoje? 1 toque no jardim",
  aha_c: "Ofensiva em jogo — 1 minuto e o jardim fica",
  /** One-shot para quem atualizou / já tinha o app. */
  aha_base:
    "Novidade no teu EGO: check-in de 1 minuto — toca e o monstrinho reage",
} as const;

export type FunnelReminderKind =
  | "d0"
  | "d1"
  | "d2"
  | "d3"
  | "d4"
  | "d5"
  | "d6"
  | "d7"
  | "aha";

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

function ahaBodyFor(now: Date): string {
  const i = now.getDay() % 3;
  if (i === 1) return COPY.aha_b;
  if (i === 2) return COPY.aha_c;
  return COPY.aha;
}

function copyForDay(daysSinceInstall: number): { kind: FunnelReminderKind; body: string } | null {
  if (daysSinceInstall === 0) return { kind: "d0", body: COPY.d0 };
  if (daysSinceInstall === 1) return { kind: "d1", body: COPY.d1 };
  if (daysSinceInstall === 2) return { kind: "d2", body: COPY.d2 };
  if (daysSinceInstall === 3) return { kind: "d3", body: COPY.d3 };
  if (daysSinceInstall === 4) return { kind: "d4", body: COPY.d4 };
  if (daysSinceInstall === 5) return { kind: "d5", body: COPY.d5 };
  if (daysSinceInstall === 6) return { kind: "d6", body: COPY.d6 };
  if (daysSinceInstall === 7) return { kind: "d7", body: COPY.d7 };
  return null;
}

function pickAhaSlot(now: Date, preferTomorrow: boolean): FunnelReminderPick {
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const body = ahaBodyFor(preferTomorrow ? tomorrow : now);

  if (preferTomorrow) {
    return { kind: "aha", at: atLocalHour(tomorrow, 10), body };
  }

  const ten = atLocalHour(now, 10);
  if (ten.getTime() > now.getTime()) {
    return { kind: "aha", at: ten, body };
  }
  const six = atLocalHour(now, 18);
  if (six.getTime() > now.getTime()) {
    return { kind: "aha", at: six, body };
  }
  return { kind: "aha", at: atLocalHour(tomorrow, 10), body: ahaBodyFor(tomorrow) };
}

/** Próximo lembrete: D0–D7 (novos) ou Aha contínuo (já tem o app). */
export function pickNextFunnelReminder(input: {
  now: Date;
  alreadySentToday: boolean;
  checkedToday: boolean;
  /** Abriu o app nesta sessão — D2+ e Aha não re-empurram hoje. */
  openedToday: boolean;
  daysSinceInstall: number;
}): FunnelReminderPick | null {
  if (input.checkedToday) return null;

  const now = input.now;
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);

  // Utilizadores antigos / pós D7 — Aha diário se falta check-in.
  if (input.daysSinceInstall > 7) {
    if (input.alreadySentToday) {
      return pickAhaSlot(now, true);
    }
    if (input.openedToday) {
      // Abriu sem check-in → ainda pode lembrar hoje às 18h (Aha para base instalada).
      const six = atLocalHour(now, 18);
      if (six.getTime() > now.getTime() + 30 * 60 * 1000) {
        return { kind: "aha", at: six, body: ahaBodyFor(now) };
      }
      return pickAhaSlot(now, true);
    }
    return pickAhaSlot(now, false);
  }

  // D2–D7: se já abriu hoje, não empurrar de novo hoje — agenda amanhã.
  if (input.daysSinceInstall >= 2 && input.openedToday) {
    const nextDay = input.daysSinceInstall + 1;
    if (nextDay > 7) return pickAhaSlot(now, true);
    const nextCopy = copyForDay(nextDay);
    if (!nextCopy) return pickAhaSlot(now, true);
    return { kind: nextCopy.kind, at: atLocalHour(tomorrow, 10), body: nextCopy.body };
  }

  const dayCopy = copyForDay(input.daysSinceInstall);
  if (!dayCopy) return pickAhaSlot(now, input.openedToday || input.alreadySentToday);

  if (input.alreadySentToday) {
    const nextDay = input.daysSinceInstall + 1;
    if (nextDay > 7) return pickAhaSlot(now, true);
    const nextCopy = copyForDay(nextDay);
    if (!nextCopy) return pickAhaSlot(now, true);
    return { kind: nextCopy.kind, at: atLocalHour(tomorrow, 10), body: nextCopy.body };
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

  const ten = atLocalHour(now, 10);
  if (ten.getTime() > now.getTime()) {
    return { kind: dayCopy.kind, at: ten, body: dayCopy.body };
  }
  const six = atLocalHour(now, 18);
  if (six.getTime() > now.getTime()) {
    return { kind: dayCopy.kind, at: six, body: dayCopy.body };
  }
  const nextDay = input.daysSinceInstall + 1;
  if (nextDay > 7) return pickAhaSlot(now, true);
  const nextCopy = copyForDay(nextDay);
  if (!nextCopy) return pickAhaSlot(now, true);
  return { kind: nextCopy.kind, at: atLocalHour(tomorrow, 10), body: nextCopy.body };
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
 * Base instalada: 1 push Aha na 1ª abertura desta versão
 * (update ou já tinha o app — não cadastro novo no dia 0).
 */
async function maybeScheduleBaseInstaladaAha(input: {
  daysSinceInstall: number;
  checkedToday: boolean;
}): Promise<void> {
  try {
    const done = await AsyncStorage.getItem(AHA_BASE_CAMPAIGN_KEY);
    if (done) return;

    const { getInstalledAppVersion } = await import("@/utils/appVersion");
    const cur = getInstalledAppVersion() || "0.0.0";
    const prev = (await AsyncStorage.getItem(LAST_SEEN_VERSION_KEY)) || "";
    await AsyncStorage.setItem(LAST_SEEN_VERSION_KEY, cur);

    const isUpdate = Boolean(prev && prev !== cur);
    const isReturningWithoutVersionMark = !prev && input.daysSinceInstall >= 1;
    if (!isUpdate && !isReturningWithoutVersionMark) {
      // Install fresco desta versão → D0 cobre; marca para não repetir.
      await AsyncStorage.setItem(AHA_BASE_CAMPAIGN_KEY, "skip_new_install");
      return;
    }

    const now = new Date();
    let at = new Date(now.getTime() + 2 * 60 * 60 * 1000);
    const six = atLocalHour(now, 18);
    if (six.getTime() > now.getTime() + 45 * 60 * 1000) {
      at = six;
    }
    if (localDayKey(at) !== localDayKey(now)) {
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      at = atLocalHour(tomorrow, 10);
    }

    try {
      await Notifications.cancelScheduledNotificationAsync(ID_AHA_BASE);
    } catch {
      /* ok */
    }

    await Notifications.scheduleNotificationAsync({
      identifier: ID_AHA_BASE,
      content: {
        title: "EGO-AI",
        body: COPY.aha_base,
        data: {
          type: "funnel_checkin",
          kind: "engagement_aha_base",
        },
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DATE,
        date: at,
        channelId: Platform.OS === "android" ? "ego_funnel" : undefined,
      },
    });
    await AsyncStorage.setItem(
      AHA_BASE_CAMPAIGN_KEY,
      input.checkedToday ? "scheduled_checked" : "scheduled"
    );
  } catch {
    /* não bloquear */
  }
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
    const installDay = await ensureInstallDay();
    const todayLocal = localDayKey(new Date());
    const daysSinceInstall = daysBetween(installDay, todayLocal);
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

    // Quem já tinha o app antes desta versão → 1 push Aha (one-shot).
    await maybeScheduleBaseInstaladaAha({
      daysSinceInstall,
      checkedToday: Boolean(input?.checkedToday),
    });

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

    // App aberto: D2+ / Aha não re-empurram de imediato; agenda tarde ou amanhã.
    const next = pickNextFunnelReminder({
      now: new Date(),
      alreadySentToday,
      checkedToday: Boolean(input?.checkedToday),
      openedToday: true,
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
  if (!kind?.startsWith("engagement_")) return null;
  return "/(main)/daily-care";
}
