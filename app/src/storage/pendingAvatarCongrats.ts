import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "ego_pending_avatar_congrats_v1";

export async function savePendingAvatarCongrats(userId: string, message: string): Promise<void> {
  const line = message.trim();
  if (!userId || !line) return;
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify({ userId, message: line }));
  } catch {
    /* ignore */
  }
}

export async function consumePendingAvatarCongrats(userId: string): Promise<string | null> {
  if (!userId) return null;
  try {
    const raw = await AsyncStorage.getItem(KEY);
    await AsyncStorage.removeItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { userId?: string; message?: string };
    if (parsed.userId !== userId) return null;
    const line = parsed.message?.trim();
    return line || null;
  } catch {
    return null;
  }
}
