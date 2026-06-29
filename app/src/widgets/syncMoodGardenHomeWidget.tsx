import React from "react";
import { Platform } from "react-native";
import type { DailyCareInfo } from "@/api/types";
import {
  buildMoodGardenWidgetSnapshot,
  defaultMoodGardenWidgetSnapshot,
  MOOD_GARDEN_ANDROID_WIDGET_NAME,
  MOOD_GARDEN_APP_GROUP,
  MOOD_GARDEN_WIDGET_STORAGE_KEY,
  persistMoodGardenWidgetSnapshot,
} from "@/storage/moodGardenWidgetSnapshot";

async function refreshAndroidWidget(
  snapshot: ReturnType<typeof defaultMoodGardenWidgetSnapshot>
): Promise<void> {
  if (Platform.OS !== "android") return;
  try {
    const { requestWidgetUpdate } = await import("react-native-android-widget");
    const { MoodGardenAndroidWidget } = await import("@/widgets/MoodGardenAndroidWidget");
    await requestWidgetUpdate({
      widgetName: MOOD_GARDEN_ANDROID_WIDGET_NAME,
      renderWidget: () => <MoodGardenAndroidWidget snapshot={snapshot} />,
    });
  } catch {
    // Build EAS apenas — Expo Go ignora.
  }
}

async function refreshIosWidget(json: string): Promise<void> {
  if (Platform.OS !== "ios") return;
  try {
    const { ExtensionStorage } = await import("@bacons/apple-targets");
    const storage = new ExtensionStorage(MOOD_GARDEN_APP_GROUP);
    storage.set(MOOD_GARDEN_WIDGET_STORAGE_KEY, json);
    ExtensionStorage.reloadWidget();
  } catch {
    // Requer target widget no build iOS.
  }
}

/** Sincroniza snapshot do jardim para widgets nativos iOS/Android. */
export async function syncMoodGardenHomeWidget(
  care: DailyCareInfo | null | undefined
): Promise<void> {
  if (Platform.OS === "web") return;
  const snapshot = buildMoodGardenWidgetSnapshot(care) ?? defaultMoodGardenWidgetSnapshot();
  const json = await persistMoodGardenWidgetSnapshot(snapshot);
  await Promise.all([refreshAndroidWidget(snapshot), refreshIosWidget(json)]);
}
