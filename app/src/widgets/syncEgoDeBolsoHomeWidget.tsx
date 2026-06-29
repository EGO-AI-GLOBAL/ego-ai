import React from "react";
import { Platform } from "react-native";
import type { WellnessJourney } from "@/api/types";
import {
  buildEgoDeBolsoWidgetSnapshot,
  defaultEgoDeBolsoWidgetSnapshot,
  EGO_DE_BOLSO_ANDROID_WIDGET_NAME,
  persistEgoDeBolsoWidgetSnapshot,
} from "@/storage/egoDeBolsoWidgetSnapshot";

async function refreshAndroidWidget(
  snapshot: ReturnType<typeof defaultEgoDeBolsoWidgetSnapshot>,
): Promise<void> {
  if (Platform.OS !== "android") return;
  try {
    const { requestWidgetUpdate } = await import("react-native-android-widget");
    const { EgoDeBolsoAndroidWidget } = await import("@/widgets/EgoDeBolsoAndroidWidget");
    await requestWidgetUpdate({
      widgetName: EGO_DE_BOLSO_ANDROID_WIDGET_NAME,
      renderWidget: () => <EgoDeBolsoAndroidWidget snapshot={snapshot} />,
    });
  } catch {
    // Build EAS apenas — Expo Go ignora.
  }
}

/** Sincroniza snapshot do bolso para widget Android na home screen. */
export async function syncEgoDeBolsoHomeWidget(
  journey: WellnessJourney | null | undefined,
): Promise<void> {
  if (Platform.OS !== "android") return;
  const snapshot =
    buildEgoDeBolsoWidgetSnapshot(journey) ?? defaultEgoDeBolsoWidgetSnapshot();
  await persistEgoDeBolsoWidgetSnapshot(snapshot);
  await refreshAndroidWidget(snapshot);
}
