import React from "react";
import type { WidgetTaskHandlerProps } from "react-native-android-widget";
import { EgoDeBolsoAndroidWidget } from "@/widgets/EgoDeBolsoAndroidWidget";
import {
  defaultEgoDeBolsoWidgetSnapshot,
  EGO_DE_BOLSO_ANDROID_WIDGET_NAME,
  readEgoDeBolsoWidgetSnapshot,
} from "@/storage/egoDeBolsoWidgetSnapshot";

async function renderFromStorage(props: WidgetTaskHandlerProps) {
  props.renderWidget(<EgoDeBolsoAndroidWidget snapshot={defaultEgoDeBolsoWidgetSnapshot()} />);
  const snapshot = await readEgoDeBolsoWidgetSnapshot();
  props.renderWidget(<EgoDeBolsoAndroidWidget snapshot={snapshot} />);
}

export async function egoDeBolsoWidgetTaskHandler(props: WidgetTaskHandlerProps) {
  if (props.widgetInfo.widgetName !== EGO_DE_BOLSO_ANDROID_WIDGET_NAME) return;

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
