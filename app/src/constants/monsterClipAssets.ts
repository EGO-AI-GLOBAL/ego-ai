import type { MoodKey } from "@/constants/moodMonsters";
import { moodKeyOrDefault } from "@/constants/moodMonsters";

/** Pasta WayIn → chave de humor da API. */
const MOOD_FOLDER: Record<MoodKey, string> = {
  calm: "brisa",
  good: "sol",
  ok: "neutro",
  anxious: "agita",
  heavy: "nublina",
};

export type MonsterClipAction =
  | "idle"
  | "mood-react"
  | "breathe"
  | "water"
  | "kind"
  | "surprise"
  | "all-goals";

const ACTION_FILE: Record<MonsterClipAction, string> = {
  idle: "01-idle",
  "mood-react": "02-mood-react",
  breathe: "03-breathe",
  water: "04-water",
  kind: "05-kind",
  surprise: "06-surprise",
  "all-goals": "07-all-goals",
};

/**
 * require() estáticos — Metro precisa de caminhos literais.
 * 5 humores × 7 clips = 35.
 */
const CLIPS: Record<MoodKey, Record<MonsterClipAction, number>> = {
  calm: {
    idle: require("../../assets/monstrinhos/brisa/01-idle-calm.mp4"),
    "mood-react": require("../../assets/monstrinhos/brisa/02-mood-react-calm.mp4"),
    breathe: require("../../assets/monstrinhos/brisa/03-breathe-calm.mp4"),
    water: require("../../assets/monstrinhos/brisa/04-water-calm.mp4"),
    kind: require("../../assets/monstrinhos/brisa/05-kind-calm.mp4"),
    surprise: require("../../assets/monstrinhos/brisa/06-surprise-calm.mp4"),
    "all-goals": require("../../assets/monstrinhos/brisa/07-all-goals-calm.mp4"),
  },
  good: {
    idle: require("../../assets/monstrinhos/sol/01-idle-good.mp4"),
    "mood-react": require("../../assets/monstrinhos/sol/02-mood-react-good.mp4"),
    breathe: require("../../assets/monstrinhos/sol/03-breathe-good.mp4"),
    water: require("../../assets/monstrinhos/sol/04-water-good.mp4"),
    kind: require("../../assets/monstrinhos/sol/05-kind-good.mp4"),
    surprise: require("../../assets/monstrinhos/sol/06-surprise-good.mp4"),
    "all-goals": require("../../assets/monstrinhos/sol/07-all-goals-good.mp4"),
  },
  ok: {
    idle: require("../../assets/monstrinhos/neutro/01-idle-ok.mp4"),
    "mood-react": require("../../assets/monstrinhos/neutro/02-mood-react-ok.mp4"),
    breathe: require("../../assets/monstrinhos/neutro/03-breathe-ok.mp4"),
    water: require("../../assets/monstrinhos/neutro/04-water-ok.mp4"),
    kind: require("../../assets/monstrinhos/neutro/05-kind-ok.mp4"),
    surprise: require("../../assets/monstrinhos/neutro/06-surprise-ok.mp4"),
    "all-goals": require("../../assets/monstrinhos/neutro/07-all-goals-ok.mp4"),
  },
  anxious: {
    idle: require("../../assets/monstrinhos/agita/01-idle-anxious.mp4"),
    "mood-react": require("../../assets/monstrinhos/agita/02-mood-react-anxious.mp4"),
    breathe: require("../../assets/monstrinhos/agita/03-breathe-anxious.mp4"),
    water: require("../../assets/monstrinhos/agita/04-water-anxious.mp4"),
    kind: require("../../assets/monstrinhos/agita/05-kind-anxious.mp4"),
    surprise: require("../../assets/monstrinhos/agita/06-surprise-anxious.mp4"),
    "all-goals": require("../../assets/monstrinhos/agita/07-all-goals-anxious.mp4"),
  },
  heavy: {
    idle: require("../../assets/monstrinhos/nublina/01-idle-heavy.mp4"),
    "mood-react": require("../../assets/monstrinhos/nublina/02-mood-react-heavy.mp4"),
    breathe: require("../../assets/monstrinhos/nublina/03-breathe-heavy.mp4"),
    water: require("../../assets/monstrinhos/nublina/04-water-heavy.mp4"),
    kind: require("../../assets/monstrinhos/nublina/05-kind-heavy.mp4"),
    surprise: require("../../assets/monstrinhos/nublina/06-surprise-heavy.mp4"),
    "all-goals": require("../../assets/monstrinhos/nublina/07-all-goals-heavy.mp4"),
  },
};

export function monsterClipModule(moodKey?: string, action: MonsterClipAction = "idle"): number {
  const key = moodKeyOrDefault(moodKey);
  return CLIPS[key][action] ?? CLIPS.ok.idle;
}

export function monsterClipFolder(moodKey?: string): string {
  return MOOD_FOLDER[moodKeyOrDefault(moodKey)];
}

export function monsterClipFileStem(action: MonsterClipAction): string {
  return ACTION_FILE[action];
}

/**
 * Missão → clip one-shot.
 * Só temos 5 ações (02–06); cada key do pool mapeada de propósito
 * para NÃO repetir o mesmo vídeo em missões distintas do mesmo dia.
 */
const GOAL_TO_CLIP: Record<string, Exclude<MonsterClipAction, "idle" | "all-goals">> = {
  checkin: "mood-react",
  smile: "mood-react",
  sun: "surprise", // luz/celebração — distinto de walk/pause
  window: "mood-react",
  breathe: "breathe",
  calm_breath: "breathe",
  pause: "breathe",
  music: "breathe",
  water: "water",
  hydrate: "water",
  plant: "water",
  walk: "water",
  stretch: "water",
  tidy: "water",
  snack: "water",
  gratitude: "kind",
  kind_self: "kind",
  note: "kind",
  adventure: "surprise",
};

const VARIETY_POOL: Exclude<MonsterClipAction, "idle">[] = [
  "mood-react",
  "breathe",
  "water",
  "kind",
  "surprise",
  "all-goals",
];

/** Fallback estável por hash — missões novas não caem todas em «kind». */
function clipFromKeyHash(goalKey: string): Exclude<MonsterClipAction, "idle" | "all-goals"> {
  const pool: Exclude<MonsterClipAction, "idle" | "all-goals">[] = [
    "mood-react",
    "breathe",
    "water",
    "kind",
    "surprise",
  ];
  let h = 0;
  for (let i = 0; i < goalKey.length; i += 1) {
    h = (h * 31 + goalKey.charCodeAt(i)) >>> 0;
  }
  return pool[h % pool.length];
}

/** Mapeia missão diária → clip one-shot. */
export function clipActionForGoalKey(goalKey: string, surprise?: boolean): MonsterClipAction {
  const key = (goalKey || "").trim().toLowerCase();
  if (surprise || key.startsWith("surprise")) return "surprise";
  if (key && GOAL_TO_CLIP[key]) return GOAL_TO_CLIP[key];
  if (!key) return "kind";
  return clipFromKeyHash(key);
}

/** Eventos do jardim com clip preferido (exclusivos quando possível). */
export function preferredClipForGardenEvent(
  event: "mood" | "shop" | "journal" | "goals-bonus" | "goal",
  goalKey?: string,
  surprise?: boolean
): MonsterClipAction {
  if (event === "mood") return "mood-react";
  if (event === "shop") return "all-goals"; // celebração loja — distinto das missões
  if (event === "journal") return "kind"; // carta íntima
  if (event === "goals-bonus") return "all-goals";
  return clipActionForGoalKey(goalKey ?? "", surprise);
}

/**
 * Evita repetir o mesmo vídeo seguidos (memória das últimas 4 ações).
 * Se o preferido já saiu há pouco, escolhe outro da pool.
 */
export function pickNonRepeatingClip(
  preferred: MonsterClipAction,
  recent: readonly MonsterClipAction[]
): MonsterClipAction {
  if (preferred === "idle") return "idle";
  if (!recent.includes(preferred)) return preferred;
  for (const candidate of VARIETY_POOL) {
    if (!recent.includes(candidate)) return candidate;
  }
  // Tudo recente — usa o menos recente possível
  for (let i = 0; i < recent.length; i += 1) {
    const older = recent[i];
    if (older && older !== "idle" && older !== preferred) return older;
  }
  return preferred;
}
