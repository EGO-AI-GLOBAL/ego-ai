import type { WidgetTaskHandlerProps } from "react-native-android-widget";
import { egoDeBolsoWidgetTaskHandler } from "@/widgets/egoDeBolsoWidgetTaskHandler";
import { moodGardenWidgetTaskHandler } from "@/widgets/moodGardenWidgetTaskHandler";

/** Router único — Android suporta vários widgets com um task handler. */
export async function androidWidgetTaskHandler(props: WidgetTaskHandlerProps) {
  await moodGardenWidgetTaskHandler(props);
  await egoDeBolsoWidgetTaskHandler(props);
}
