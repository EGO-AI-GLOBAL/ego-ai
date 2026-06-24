import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import type { DailyCareInfo } from "@/api/types";
import { ensureReminderNotificationPermission } from "@/utils/reminderNotifications";

const STREAK_RISK_ID = "mood-monster-streak-risk-20h";
const GOALS_NUDGE_ID = "mood-monster-goals-16h";
const STREAK_HOUR = 20;
const GOALS_HOUR = 16;

export function moodMonsterStreakAtRisk(care: DailyCareInfo): boolean {
  return Boolean(care.at_risk && (care.current ?? 0) >= 1);
}

export function moodMonsterGoalsPending(care: DailyCareInfo): boolean {
  if (!care.checked_today || care.all_goals_done) return false;
  const goals = care.daily_goals ?? [];
  return goals.some((g) => !g.done && !g.locked);
}

export function moodMonsterNotificationCopy(
  care: DailyCareInfo,
  kind: "streak" | "goals"
): { title: string; body: string } {
  const days = care.current ?? 0;
  const emoji = care.garden_emoji || care.last_mood_emoji || "💜";
  if (kind === "streak") {
    return {
      title: `${emoji} Streak em risco!`,
      body:
        days <= 1
          ? "Seu monstrinho espera o check-in de hoje — 1 minuto no jardim."
          : `Não perca ${days} dias seguidos! Abra o jardim e domine o humor.`,
    };
  }
  const pending = (care.daily_goals ?? []).filter((g) => !g.done && !g.locked).length;
  const bonus = care.all_goals_bonus ?? 3;
  return {
    title: `${emoji} Missões no jardim`,
    body:
      pending === 1
        ? `Falta 1 missão hoje — complete as 3 e ganhe +${bonus} sementes!`
        : `Faltam ${pending} missões — complete o dia perfeito no jardim!`,
  };
}

async function scheduleDaily(
  id: string,
  hour: number,
  copy: { title: string; body: string }
): Promise<void> {
  await Notifications.cancelScheduledNotificationAsync(id);
  await Notifications.scheduleNotificationAsync({
    identifier: id,
    content: {
      title: copy.title,
      body: copy.body,
      sound: true,
      data: {
        type: "mood_monster",
        screen: "daily-care",
      },
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DAILY,
      hour,
      minute: 0,
    },
  });
}

/** Push diário Monstrinhos — streak em risco (20h) e missões pendentes (16h). */
export async function syncMoodMonsterNotifications(
  care?: DailyCareInfo | null
): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    await Notifications.cancelScheduledNotificationAsync(STREAK_RISK_ID);
    await Notifications.cancelScheduledNotificationAsync(GOALS_NUDGE_ID);
    if (!care) return;

    const streak = moodMonsterStreakAtRisk(care);
    const goals = moodMonsterGoalsPending(care);
    if (!streak && !goals) return;

    const granted = await ensureReminderNotificationPermission();
    if (!granted) return;

    if (streak) {
      await scheduleDaily(STREAK_RISK_ID, STREAK_HOUR, moodMonsterNotificationCopy(care, "streak"));
    }
    if (goals) {
      await scheduleDaily(GOALS_NUDGE_ID, GOALS_HOUR, moodMonsterNotificationCopy(care, "goals"));
    }
  } catch {
    /* opcional */
  }
}

export async function cancelMoodMonsterNotifications(): Promise<void> {
  if (Platform.OS === "web") return;
  try {
    await Notifications.cancelScheduledNotificationAsync(STREAK_RISK_ID);
    await Notifications.cancelScheduledNotificationAsync(GOALS_NUDGE_ID);
  } catch {
    /* ignore */
  }
}
