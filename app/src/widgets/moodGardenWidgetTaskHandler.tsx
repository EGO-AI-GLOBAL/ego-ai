import React from "react";
import type { WidgetTaskHandlerProps } from "react-native-android-widget";
import { MoodGardenAndroidWidget } from "@/widgets/MoodGardenAndroidWidget";
import {
  defaultMoodGardenWidgetSnapshot,
  MOOD_GARDEN_ANDROID_WIDGET_NAME,
  readMoodGardenWidgetSnapshot,
} from "@/storage/moodGardenWidgetSnapshot";

async function renderFromStorage(props: WidgetTaskHandlerProps) {
  props.renderWidget(<MoodGardenAndroidWidget snapshot={defaultMoodGardenWidgetSnapshot()} />);
  const snapshot = await readMoodGardenWidgetSnapshot();
  props.renderWidget(<MoodGardenAndroidWidget snapshot={snapshot} />);
}

export async function moodGardenWidgetTaskHandler(props: WidgetTaskHandlerProps) {
  if (props.widgetInfo.widgetName !== MOOD_GARDEN_ANDROID_WIDGET_NAME) return;

  switch (props.widgetAction) {
    case "WIDGET_ADDED":
    case "WIDGET_UPDATE":
    case "WIDGET_RESIZED":
      await renderFromStorage(props);
      break;
    default:
      break;
  }
}
