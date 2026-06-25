import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import { api } from "@/api/client";
import { isDailyCheckInEnabled } from "@/storage/chatHints";

let lastRegisteredToken = "";

/**
 * Guarda o token Expo Push no perfil (ui_state.expo_push_token) para avisos de agenda compartilhada.
 */
export async function registerExpoPushToken(): Promise<void> {
  if (Platform.OS === "web") return;

  const granted = await Notifications.getPermissionsAsync();
  let ok = granted.granted;
  if (!ok) {
    const req = await Notifications.requestPermissionsAsync();
    ok = req.granted;
  }
  if (!ok) return;

  const projectId =
    Constants.expoConfig?.extra?.eas?.projectId ??
    Constants.easConfig?.projectId;
  if (!projectId) return;

  try {
    const { data: token } = await Notifications.getExpoPushTokenAsync({
      projectId: String(projectId),
    });
    const trimmed = (token || "").trim();
    if (!trimmed || trimmed === lastRegisteredToken) return;
    lastRegisteredToken = trimmed;
    await api.patch("profile", {
      ui_state: {
        expo_push_token: trimmed,
        ego_daily_checkin_enabled: await isDailyCheckInEnabled(),
      },
    });
  } catch {
    /* token indisponível (simulador, Expo Go limitado, etc.) */
  }
}
