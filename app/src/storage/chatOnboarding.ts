import AsyncStorage from "@react-native-async-storage/async-storage";

const PREFIX = "ego_chat_onboarding_done_v1_";

function key(userId: string): string {
  return `${PREFIX}${userId.replace(/[^a-zA-Z0-9_-]/g, "_")}`;
}

export async function isChatOnboardingDone(userId: string): Promise<boolean> {
  if (!userId.trim()) return true;
  try {
    return (await AsyncStorage.getItem(key(userId))) === "1";
  } catch {
    return false;
  }
}

export async function markChatOnboardingDone(userId: string): Promise<void> {
  if (!userId.trim()) return;
  try {
    await AsyncStorage.setItem(key(userId), "1");
  } catch {
    /* ignore */
  }
}
