import { Alert, Linking, Platform } from "react-native";

const PLAY_TESTING = "https://play.google.com/apps/testing/com.egoai.app";
const PLAY_STORE = "https://play.google.com/store/apps/details?id=com.egoai.app";
const PLAY_MARKET = "market://details?id=com.egoai.app";
const TESTFLIGHT_JOIN = "https://testflight.apple.com/join/eNDKdFWF";
const TESTFLIGHT_APP = "itms-beta://";

async function tryOpenUrl(url: string): Promise<boolean> {
  const trimmed = url?.trim();
  if (!trimmed) return false;
  try {
    if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
      const can = await Linking.canOpenURL(trimmed);
      if (!can) return false;
    }
    await Linking.openURL(trimmed);
    return true;
  } catch {
    return false;
  }
}

async function openFirstUrl(urls: string[]): Promise<boolean> {
  for (const url of urls) {
    if (await tryOpenUrl(url)) return true;
  }
  return false;
}

function iosUrls(iosUpdateUrl: string): string[] {
  const fromApi = iosUpdateUrl?.trim();
  const list = [TESTFLIGHT_APP];
  if (fromApi?.startsWith("http") && fromApi !== TESTFLIGHT_JOIN) list.push(fromApi);
  list.push(TESTFLIGHT_JOIN);
  return [...new Set(list)];
}

/** Abre Play (Android) ou TestFlight (iOS — app TestFlight, não link de convite). */
export async function openAppUpdate(opts?: {
  playStoreUrl?: string;
  iosUpdateUrl?: string;
}): Promise<void> {
  const playStoreUrl = opts?.playStoreUrl?.trim() || "";
  const iosUpdateUrl = opts?.iosUpdateUrl?.trim() || "";

  if (Platform.OS === "ios") {
    const opened = await openFirstUrl(iosUrls(iosUpdateUrl));
    if (!opened) {
      Alert.alert(
        "Atualizar no TestFlight",
        "Saia do EGO-AI, abra o app TestFlight (ícone azul) e toque em Atualizar no EGO-AI.",
        [
          { text: "OK", style: "cancel" },
          { text: "Abrir TestFlight", onPress: () => void openFirstUrl([TESTFLIGHT_APP]) },
        ]
      );
    }
    return;
  }

  const urls = [playStoreUrl, PLAY_TESTING, PLAY_STORE, PLAY_MARKET].filter(Boolean);
  const opened = await openFirstUrl(urls);
  if (!opened) {
    Alert.alert("Atualizar na Play", "Abra o link do teste fechado e toque em Atualizar.", [
      { text: "Cancelar", style: "cancel" },
      { text: "Abrir Play", onPress: () => void tryOpenUrl(PLAY_TESTING) },
    ]);
  }
}
