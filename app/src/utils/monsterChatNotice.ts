import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "ego_monster_chat_notice_v1";

/** Fila aviso no chat ao voltar do Jardim (dia completo / missões). */
export async function queueMonsterChatNotice(message: string): Promise<void> {
  const text = message.trim();
  if (!text) return;
  await AsyncStorage.setItem(KEY, text);
}

export async function consumeMonsterChatNotice(): Promise<string | null> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw?.trim()) return null;
    await AsyncStorage.removeItem(KEY);
    return raw.trim();
  } catch {
    return null;
  }
}
