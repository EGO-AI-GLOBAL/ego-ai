import AsyncStorage from "@react-native-async-storage/async-storage";

const AUTO_PLAY_VOICE_KEY = "ego_auto_play_voice";

/** Por defeito: texto primeiro; o utilizador toca para ouvir (mais rápido). */
export async function loadAutoPlayVoice(): Promise<boolean> {
  try {
    const raw = await AsyncStorage.getItem(AUTO_PLAY_VOICE_KEY);
    if (raw === "1" || raw === "true") return true;
    if (raw === "0" || raw === "false") return false;
  } catch {
    /* ignore */
  }
  return false;
}

export async function saveAutoPlayVoice(enabled: boolean): Promise<void> {
  try {
    await AsyncStorage.setItem(AUTO_PLAY_VOICE_KEY, enabled ? "1" : "0");
  } catch {
    /* ignore */
  }
}
