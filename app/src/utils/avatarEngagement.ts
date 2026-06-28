import AsyncStorage from "@react-native-async-storage/async-storage";
import { AVATAR_CATALOG } from "@/constants/avatarCatalog";

const WEEKLY_GOAL = 3;
const KEY_PREFIX = "ego_avatar_engagement:";

function weekKey(userId: string): string {
  const now = new Date();
  const onejan = new Date(now.getFullYear(), 0, 1);
  const week = Math.ceil(((now.getTime() - onejan.getTime()) / 86400000 + onejan.getDay() + 1) / 7);
  return `${KEY_PREFIX}week:${userId}:${now.getFullYear()}-W${week}`;
}

function dayKey(userId: string): string {
  const d = new Date().toISOString().slice(0, 10);
  return `${KEY_PREFIX}day:${userId}:${d}`;
}

/** Avatar sugerido do dia — determinístico por data + userId. */
export function pickAvatarOfDay(userId: string): (typeof AVATAR_CATALOG)[number] {
  const seed = `${userId}:${new Date().toISOString().slice(0, 10)}`;
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  const idx = hash % AVATAR_CATALOG.length;
  return AVATAR_CATALOG[idx]!;
}

export async function recordAvatarChat(userId: string, avatarId: string): Promise<void> {
  if (!userId || !avatarId) return;
  const key = weekKey(userId);
  const raw = await AsyncStorage.getItem(key);
  const set = new Set<string>(raw ? JSON.parse(raw) : []);
  set.add(avatarId.trim().toLowerCase());
  await AsyncStorage.setItem(key, JSON.stringify([...set]));
}

export async function getWeeklyAvatarStats(userId: string): Promise<{
  chattedIds: string[];
  goal: number;
  done: number;
}> {
  const raw = await AsyncStorage.getItem(weekKey(userId));
  const chattedIds: string[] = raw ? JSON.parse(raw) : [];
  return { chattedIds, goal: WEEKLY_GOAL, done: chattedIds.length };
}

export async function markAvatarOfDaySeen(userId: string): Promise<void> {
  await AsyncStorage.setItem(dayKey(userId), "1");
}

export async function wasAvatarOfDaySeenToday(userId: string): Promise<boolean> {
  return (await AsyncStorage.getItem(dayKey(userId))) === "1";
}

export function avatarsNotChattedThisWeek(
  chattedIds: string[]
): (typeof AVATAR_CATALOG)[number][] {
  const set = new Set(chattedIds.map((id) => id.toLowerCase()));
  return AVATAR_CATALOG.filter((a) => !set.has(a.avatar_id)).slice(0, 3);
}
