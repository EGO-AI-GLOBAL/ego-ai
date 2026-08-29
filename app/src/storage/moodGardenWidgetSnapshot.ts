import AsyncStorage from "@react-native-async-storage/async-storage";
import type { DailyCareInfo } from "@/api/types";

export const MOOD_GARDEN_WIDGET_STORAGE_KEY = "ego_mood_garden_widget_v1";
export const MOOD_GARDEN_APP_GROUP = "group.com.egoai.app.widget";
export const MOOD_GARDEN_ANDROID_WIDGET_NAME = "MoodGarden";

export type MoodGardenWidgetSnapshot = {
  title: string;
  subtitle: string;
  emoji: string;
  atRisk: boolean;
  goalsLine: string;
};

export function defaultMoodGardenWidgetSnapshot(): MoodGardenWidgetSnapshot {
  return {
    title: "Jardim dos Monstrinhos",
    subtitle: "1 toque — humor de hoje",
    emoji: "🌱",
    atRisk: false,
    goalsLine: "",
  };
}

export function buildMoodGardenWidgetSnapshot(
  care: DailyCareInfo | null | undefined
): MoodGardenWidgetSnapshot | null {
  if (!care?.question) return null;

  const goals = care.daily_goals ?? [];
  const done = goals.filter((g) => g.done).length;
  const total = goals.length || 5;
  const seeds = care.seeds ?? 0;
  const streak = care.current ?? 0;
  const atRisk = Boolean(care.at_risk);

  const remaining = Math.max(0, total - done);

  let subtitle = "1 toque — humor de hoje";
  const congrats = care.avatar_congrats?.trim();
  if (congrats) {
    subtitle = congrats;
  } else if (atRisk) {
    if (!care.checked_today) {
      subtitle =
        streak > 0
          ? `🔥 ${streak}d em risco — 1 toque agora`
          : "Check-in pendente — 1 toque";
    } else if (remaining > 0) {
      subtitle = `Faltam ${remaining} missões · ${streak}d em risco`;
    } else {
      subtitle = `Dia completo · ${streak} dias`;
    }
  } else if (!care.checked_today) {
    subtitle = "1 toque — humor de hoje";
  } else if (remaining > 0) {
    subtitle = `Faltam ${remaining} missões · ${seeds} sementes`;
  } else {
    subtitle = `Dia completo · ${streak} dias seguidos`;
  }

  const goalsLine = care.checked_today
    ? remaining > 0
      ? `Faltam ${remaining}/${total} · ${streak}d`
      : `${total}/${total} missões · ${streak}d`
    : atRisk && streak > 0
      ? `Streak ${streak}d em risco`
      : "Check-in pendente";

  const emoji =
    care.checked_today && care.last_mood_emoji
      ? String(care.last_mood_emoji)
      : String(care.garden_emoji ?? "🌱");

  return {
    title: "Jardim dos Monstrinhos",
    subtitle,
    emoji,
    atRisk,
    goalsLine,
  };
}

export async function readMoodGardenWidgetSnapshot(): Promise<MoodGardenWidgetSnapshot> {
  try {
    const raw = await AsyncStorage.getItem(MOOD_GARDEN_WIDGET_STORAGE_KEY);
    if (!raw) return defaultMoodGardenWidgetSnapshot();
    const parsed = JSON.parse(raw) as MoodGardenWidgetSnapshot;
    if (!parsed?.title) return defaultMoodGardenWidgetSnapshot();
    return parsed;
  } catch {
    return defaultMoodGardenWidgetSnapshot();
  }
}

export async function persistMoodGardenWidgetSnapshot(
  snapshot: MoodGardenWidgetSnapshot
): Promise<string> {
  const json = JSON.stringify(snapshot);
  await AsyncStorage.setItem(MOOD_GARDEN_WIDGET_STORAGE_KEY, json);
  return json;
}
