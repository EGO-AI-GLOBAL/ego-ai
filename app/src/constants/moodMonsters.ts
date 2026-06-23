export type MoodKey = "heavy" | "anxious" | "ok" | "good" | "calm";

export type MoodPalette = {
  body: string;
  bodyDark: string;
  cheek: string;
  eye: string;
  mouth: string;
  accent: string;
};

export const MOOD_PALETTES: Record<MoodKey, MoodPalette> = {
  heavy: {
    body: "#8B7EC8",
    bodyDark: "#6B5FA8",
    cheek: "#B8A9E8",
    eye: "#2D2640",
    mouth: "#4A3F6B",
    accent: "#C4B5FD",
  },
  anxious: {
    body: "#F5A962",
    bodyDark: "#E08840",
    cheek: "#FFD4A8",
    eye: "#3D2A14",
    mouth: "#8B4513",
    accent: "#FFE566",
  },
  ok: {
    body: "#94A3B8",
    bodyDark: "#64748B",
    cheek: "#CBD5E1",
    eye: "#1E293B",
    mouth: "#475569",
    accent: "#E2E8F0",
  },
  good: {
    body: "#FFE566",
    bodyDark: "#F5C842",
    cheek: "#FFF3A8",
    eye: "#3D3500",
    mouth: "#B8860B",
    accent: "#FFF9C4",
  },
  calm: {
    body: "#7DD3FC",
    bodyDark: "#38BDF8",
    cheek: "#BAE6FD",
    eye: "#0C4A6E",
    mouth: "#0369A1",
    accent: "#E0F2FE",
  },
};

export const GARDEN_GRADIENTS: Record<number, readonly [string, string, string]> = {
  1: ["#8B7355", "#A8C090", "#C8E6A0"],
  2: ["#6B8E5A", "#90C878", "#B8E8A0"],
  3: ["#5A9E6A", "#7ECF8A", "#A8F0B8"],
  4: ["#4A8E5A", "#6BBF7A", "#98E8A8"],
  5: ["#3A7E6A", "#5AAF9A", "#88DFC8"],
};

export const GARDEN_DECOR: Record<number, string[]> = {
  1: ["🌱"],
  2: ["🌱", "🪴"],
  3: ["🌸", "🦋", "🪴"],
  4: ["🌳", "🌸", "🍀"],
  5: ["🌈", "🌳", "🌺", "✨"],
};

/** Posições fixas para decorações desbloqueadas (estilo Finch). */
export const DECOR_POSITIONS: Record<string, { left: string; top: number; size: number }> = {
  flowers: { left: "8%", top: 52, size: 26 },
  butterfly: { left: "78%", top: 38, size: 24 },
  fountain: { left: "42%", top: 62, size: 28 },
  treehouse: { left: "68%", top: 48, size: 30 },
  rainbow: { left: "22%", top: 28, size: 32 },
};

export function moodKeyOrDefault(key?: string): MoodKey {
  if (key && key in MOOD_PALETTES) return key as MoodKey;
  return "ok";
}

export function gardenStageFromDays(days: number): number {
  if (days >= 30) return 5;
  if (days >= 14) return 4;
  if (days >= 7) return 3;
  if (days >= 3) return 2;
  return 1;
}
