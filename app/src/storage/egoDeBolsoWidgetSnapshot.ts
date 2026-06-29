import AsyncStorage from "@react-native-async-storage/async-storage";
import type { WellnessJourney } from "@/api/types";
import { egoDeBolsoMissionsComplete } from "@/utils/egoDeBolsoCompanionMood";
import { resolveCompanionDisplayName } from "@/utils/egoDeBolsoCompanionName";

export const EGO_DE_BOLSO_WIDGET_STORAGE_KEY = "ego_de_bolso_widget_v1";
export const EGO_DE_BOLSO_ANDROID_WIDGET_NAME = "EgoDeBolso";

export type EgoDeBolsoWidgetSnapshot = {
  title: string;
  missionsLine: string;
  weeklyLine: string;
  emoji: string;
  dayComplete: boolean;
};

export function defaultEgoDeBolsoWidgetSnapshot(): EgoDeBolsoWidgetSnapshot {
  return {
    title: "EGO de Bolso",
    missionsLine: "Abra o app para ver as missões do dia",
    weeklyLine: "",
    emoji: "🥚",
    dayComplete: false,
  };
}

export function buildEgoDeBolsoWidgetSnapshot(
  journey: WellnessJourney | null | undefined,
): EgoDeBolsoWidgetSnapshot | null {
  if (!journey) return null;

  const pet = resolveCompanionDisplayName(journey);
  const missionsToday = journey.missions_today ?? 0;
  const missionsPerDay = journey.missions_per_day ?? 5;
  const dayComplete = egoDeBolsoMissionsComplete(journey);
  const weekly = journey.weekly_challenge;
  const emoji = journey.companion_sprite_emoji ?? journey.emoji ?? "🥚";

  let missionsLine = dayComplete
    ? `${missionsPerDay}/${missionsPerDay} missões — dia completo`
    : `${missionsToday}/${missionsPerDay} missões hoje`;

  if (!dayComplete && journey.today_task) {
    missionsLine += ` · ${journey.today_task}`;
  }

  let weeklyLine = "";
  if (weekly) {
    weeklyLine = weekly.complete
      ? `Desafio da semana: ${weekly.days_done}/${weekly.days_goal} dias`
      : `Semana: ${weekly.days_done}/${weekly.days_goal} dias com 5/5`;
  }

  return {
    title: `${pet} · Nível ${journey.level}/${journey.max_level}`,
    missionsLine,
    weeklyLine,
    emoji: String(emoji),
    dayComplete,
  };
}

export async function readEgoDeBolsoWidgetSnapshot(): Promise<EgoDeBolsoWidgetSnapshot> {
  try {
    const raw = await AsyncStorage.getItem(EGO_DE_BOLSO_WIDGET_STORAGE_KEY);
    if (!raw) return defaultEgoDeBolsoWidgetSnapshot();
    const parsed = JSON.parse(raw) as EgoDeBolsoWidgetSnapshot;
    if (!parsed?.title) return defaultEgoDeBolsoWidgetSnapshot();
    return parsed;
  } catch {
    return defaultEgoDeBolsoWidgetSnapshot();
  }
}

export async function persistEgoDeBolsoWidgetSnapshot(
  snapshot: EgoDeBolsoWidgetSnapshot,
): Promise<string> {
  const json = JSON.stringify(snapshot);
  await AsyncStorage.setItem(EGO_DE_BOLSO_WIDGET_STORAGE_KEY, json);
  return json;
}
