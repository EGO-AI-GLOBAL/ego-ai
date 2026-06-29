import { Platform } from "react-native";

if (Platform.OS === "android") {
  const { registerWidgetTaskHandler } = require("react-native-android-widget");
  const { androidWidgetTaskHandler } = require("./src/widgets/androidWidgetTaskHandler");
  registerWidgetTaskHandler(androidWidgetTaskHandler);
}

import "expo-router/entry";
