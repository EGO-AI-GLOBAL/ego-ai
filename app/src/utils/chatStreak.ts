import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "ego_chat_streak:";

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function yesterdayStr(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

type StreakState = { lastDate: string; count: number };

export async function recordChatStreakDay(userId: string): Promise<number> {
  if (!userId) return 0;
  const key = `${KEY}${userId}`;
  const raw = await AsyncStorage.getItem(key);
  const prev: StreakState = raw ? JSON.parse(raw) : { lastDate: "", count: 0 };
  const today = todayStr();
  if (prev.lastDate === today) return prev.count;
  const next =
    prev.lastDate === yesterdayStr() ? prev.count + 1 : 1;
  await AsyncStorage.setItem(key, JSON.stringify({ lastDate: today, count: next }));
  return next;
}

export async function getChatStreak(userId: string): Promise<number> {
  if (!userId) return 0;
  const raw = await AsyncStorage.getItem(`${KEY}${userId}`);
  if (!raw) return 0;
  const st: StreakState = JSON.parse(raw);
  if (st.lastDate === todayStr() || st.lastDate === yesterdayStr()) {
    return st.count;
  }
  return 0;
}

export function chatStreakSubtitle(streak: number, assistantName: string): string | null {
  if (streak < 2) return null;
  return `${assistantName}: ${streak} dias seguidos no chat — orgulho de você.`;
}
