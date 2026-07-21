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

/** Clips core 01–07 (todos os humores). */
export type MonsterClipCoreAction =
  | "idle"
  | "mood-react"
  | "breathe"
  | "water"
  | "kind"
  | "surprise"
  | "all-goals";

/** Clips novos 08–24 (1:1 com missões / loja / carta). */
export type MonsterClipExtraAction =
  | "stretch"
  | "smile"
  | "tidy"
  | "sun"
  | "window"
  | "snack"
  | "adventure"
  | "walk"
  | "hydrate"
  | "plant"
  | "pause"
  | "music"
  | "gratitude"
  | "note"
  | "kind-self"
  | "letter"
  | "shop";

export type MonsterClipAction = MonsterClipCoreAction | MonsterClipExtraAction;

const ACTION_FILE: Record<MonsterClipAction, string> = {
  idle: "01-idle",
  "mood-react": "02-mood-react",
  breathe: "03-breathe",
  water: "04-water",
  kind: "05-kind",
  surprise: "06-surprise",
  "all-goals": "07-all-goals",
  stretch: "08-stretch",
  smile: "09-smile",
  tidy: "10-tidy",
  sun: "11-sun",
  window: "12-window",
  snack: "13-snack",
  adventure: "14-adventure",
  walk: "15-walk",
  hydrate: "16-hydrate",
  plant: "17-plant",
  pause: "18-pause",
  music: "19-music",
  gratitude: "20-gratitude",
  note: "21-note",
  "kind-self": "22-kind-self",
  letter: "23-letter",
  shop: "24-shop",
};

/**
 * require() estáticos — Metro precisa de caminhos literais.
 * Core: 5 × 7 = 35. Extra Sol/Brisa/Neutro/Agita/Nublina: 5 × 17.
 */
const CORE: Record<MoodKey, Record<MonsterClipCoreAction, number>> = {
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

/** Extra completo: Sol / Brisa / Neutro / Agita / Nublina (08–24). */
const EXTRA_FULL: Record<
  "calm" | "good" | "ok" | "anxious" | "heavy",
  Record<MonsterClipExtraAction, number>
> = {
  calm: {
    stretch: require("../../assets/monstrinhos/brisa/08-stretch-calm.mp4"),
    smile: require("../../assets/monstrinhos/brisa/09-smile-calm.mp4"),
    tidy: require("../../assets/monstrinhos/brisa/10-tidy-calm.mp4"),
    sun: require("../../assets/monstrinhos/brisa/11-sun-calm.mp4"),
    window: require("../../assets/monstrinhos/brisa/12-window-calm.mp4"),
    snack: require("../../assets/monstrinhos/brisa/13-snack-calm.mp4"),
    adventure: require("../../assets/monstrinhos/brisa/14-adventure-calm.mp4"),
    walk: require("../../assets/monstrinhos/brisa/15-walk-calm.mp4"),
    hydrate: require("../../assets/monstrinhos/brisa/16-hydrate-calm.mp4"),
    plant: require("../../assets/monstrinhos/brisa/17-plant-calm.mp4"),
    pause: require("../../assets/monstrinhos/brisa/18-pause-calm.mp4"),
    music: require("../../assets/monstrinhos/brisa/19-music-calm.mp4"),
    gratitude: require("../../assets/monstrinhos/brisa/20-gratitude-calm.mp4"),
    note: require("../../assets/monstrinhos/brisa/21-note-calm.mp4"),
    "kind-self": require("../../assets/monstrinhos/brisa/22-kind-self-calm.mp4"),
    letter: require("../../assets/monstrinhos/brisa/23-letter-calm.mp4"),
    shop: require("../../assets/monstrinhos/brisa/24-shop-calm.mp4"),
  },
  good: {
    stretch: require("../../assets/monstrinhos/sol/08-stretch-good.mp4"),
    smile: require("../../assets/monstrinhos/sol/09-smile-good.mp4"),
    tidy: require("../../assets/monstrinhos/sol/10-tidy-good.mp4"),
    sun: require("../../assets/monstrinhos/sol/11-sun-good.mp4"),
    window: require("../../assets/monstrinhos/sol/12-window-good.mp4"),
    snack: require("../../assets/monstrinhos/sol/13-snack-good.mp4"),
    adventure: require("../../assets/monstrinhos/sol/14-adventure-good.mp4"),
    walk: require("../../assets/monstrinhos/sol/15-walk-good.mp4"),
    hydrate: require("../../assets/monstrinhos/sol/16-hydrate-good.mp4"),
    plant: require("../../assets/monstrinhos/sol/17-plant-good.mp4"),
    pause: require("../../assets/monstrinhos/sol/18-pause-good.mp4"),
    music: require("../../assets/monstrinhos/sol/19-music-good.mp4"),
    gratitude: require("../../assets/monstrinhos/sol/20-gratitude-good.mp4"),
    note: require("../../assets/monstrinhos/sol/21-note-good.mp4"),
    "kind-self": require("../../assets/monstrinhos/sol/22-kind-self-good.mp4"),
    letter: require("../../assets/monstrinhos/sol/23-letter-good.mp4"),
    shop: require("../../assets/monstrinhos/sol/24-shop-good.mp4"),
  },
  ok: {
    stretch: require("../../assets/monstrinhos/neutro/08-stretch-ok.mp4"),
    smile: require("../../assets/monstrinhos/neutro/09-smile-ok.mp4"),
    tidy: require("../../assets/monstrinhos/neutro/10-tidy-ok.mp4"),
    sun: require("../../assets/monstrinhos/neutro/11-sun-ok.mp4"),
    window: require("../../assets/monstrinhos/neutro/12-window-ok.mp4"),
    snack: require("../../assets/monstrinhos/neutro/13-snack-ok.mp4"),
    adventure: require("../../assets/monstrinhos/neutro/14-adventure-ok.mp4"),
    walk: require("../../assets/monstrinhos/neutro/15-walk-ok.mp4"),
    hydrate: require("../../assets/monstrinhos/neutro/16-hydrate-ok.mp4"),
    plant: require("../../assets/monstrinhos/neutro/17-plant-ok.mp4"),
    pause: require("../../assets/monstrinhos/neutro/18-pause-ok.mp4"),
    music: require("../../assets/monstrinhos/neutro/19-music-ok.mp4"),
    gratitude: require("../../assets/monstrinhos/neutro/20-gratitude-ok.mp4"),
    note: require("../../assets/monstrinhos/neutro/21-note-ok.mp4"),
    "kind-self": require("../../assets/monstrinhos/neutro/22-kind-self-ok.mp4"),
    letter: require("../../assets/monstrinhos/neutro/23-letter-ok.mp4"),
    shop: require("../../assets/monstrinhos/neutro/24-shop-ok.mp4"),
  },
  anxious: {
    stretch: require("../../assets/monstrinhos/agita/08-stretch-anxious.mp4"),
    smile: require("../../assets/monstrinhos/agita/09-smile-anxious.mp4"),
    tidy: require("../../assets/monstrinhos/agita/10-tidy-anxious.mp4"),
    sun: require("../../assets/monstrinhos/agita/11-sun-anxious.mp4"),
    window: require("../../assets/monstrinhos/agita/12-window-anxious.mp4"),
    snack: require("../../assets/monstrinhos/agita/13-snack-anxious.mp4"),
    adventure: require("../../assets/monstrinhos/agita/14-adventure-anxious.mp4"),
    walk: require("../../assets/monstrinhos/agita/15-walk-anxious.mp4"),
    hydrate: require("../../assets/monstrinhos/agita/16-hydrate-anxious.mp4"),
    plant: require("../../assets/monstrinhos/agita/17-plant-anxious.mp4"),
    pause: require("../../assets/monstrinhos/agita/18-pause-anxious.mp4"),
    music: require("../../assets/monstrinhos/agita/19-music-anxious.mp4"),
    gratitude: require("../../assets/monstrinhos/agita/20-gratitude-anxious.mp4"),
    note: require("../../assets/monstrinhos/agita/21-note-anxious.mp4"),
    "kind-self": require("../../assets/monstrinhos/agita/22-kind-self-anxious.mp4"),
    letter: require("../../assets/monstrinhos/agita/23-letter-anxious.mp4"),
    shop: require("../../assets/monstrinhos/agita/24-shop-anxious.mp4"),
  },
  heavy: {
    stretch: require("../../assets/monstrinhos/nublina/08-stretch-heavy.mp4"),
    smile: require("../../assets/monstrinhos/nublina/09-smile-heavy.mp4"),
    tidy: require("../../assets/monstrinhos/nublina/10-tidy-heavy.mp4"),
    sun: require("../../assets/monstrinhos/nublina/11-sun-heavy.mp4"),
    window: require("../../assets/monstrinhos/nublina/12-window-heavy.mp4"),
    snack: require("../../assets/monstrinhos/nublina/13-snack-heavy.mp4"),
    adventure: require("../../assets/monstrinhos/nublina/14-adventure-heavy.mp4"),
    walk: require("../../assets/monstrinhos/nublina/15-walk-heavy.mp4"),
    hydrate: require("../../assets/monstrinhos/nublina/16-hydrate-heavy.mp4"),
    plant: require("../../assets/monstrinhos/nublina/17-plant-heavy.mp4"),
    pause: require("../../assets/monstrinhos/nublina/18-pause-heavy.mp4"),
    music: require("../../assets/monstrinhos/nublina/19-music-heavy.mp4"),
    gratitude: require("../../assets/monstrinhos/nublina/20-gratitude-heavy.mp4"),
    note: require("../../assets/monstrinhos/nublina/21-note-heavy.mp4"),
    "kind-self": require("../../assets/monstrinhos/nublina/22-kind-self-heavy.mp4"),
    letter: require("../../assets/monstrinhos/nublina/23-letter-heavy.mp4"),
    shop: require("../../assets/monstrinhos/nublina/24-shop-heavy.mp4"),
  },
};

/** Sem ficheiro extra → clip core equivalente (fallback genérico). */
const EXTRA_FALLBACK: Record<MonsterClipExtraAction, MonsterClipCoreAction> = {
  stretch: "water",
  smile: "mood-react",
  tidy: "water",
  sun: "surprise",
  window: "mood-react",
  snack: "water",
  adventure: "surprise",
  walk: "water",
  hydrate: "water",
  plant: "water",
  pause: "breathe",
  music: "breathe",
  gratitude: "kind",
  note: "kind",
  "kind-self": "kind",
  letter: "kind",
  shop: "all-goals",
};

function isCoreAction(action: MonsterClipAction): action is MonsterClipCoreAction {
  return (
    action === "idle" ||
    action === "mood-react" ||
    action === "breathe" ||
    action === "water" ||
    action === "kind" ||
    action === "surprise" ||
    action === "all-goals"
  );
}

export function monsterClipModule(moodKey?: string, action: MonsterClipAction = "idle"): number {
  const key = moodKeyOrDefault(moodKey);
  if (isCoreAction(action)) {
    return CORE[key][action] ?? CORE.ok.idle;
  }
  if (key === "calm" || key === "good" || key === "ok" || key === "anxious" || key === "heavy") {
    return EXTRA_FULL[key][action] ?? CORE[key][EXTRA_FALLBACK[action]] ?? CORE.ok.idle;
  }
  return CORE[key][EXTRA_FALLBACK[action]] ?? CORE.ok.idle;
}

export function monsterClipFolder(moodKey?: string): string {
  return MOOD_FOLDER[moodKeyOrDefault(moodKey)];
}

export function monsterClipFileStem(action: MonsterClipAction): string {
  return ACTION_FILE[action];
}

/** Missão → clip one-shot (1:1 quando o MP4 existe). */
const GOAL_TO_CLIP: Record<string, Exclude<MonsterClipAction, "idle">> = {
  checkin: "mood-react",
  smile: "smile",
  sun: "sun",
  window: "window",
  breathe: "breathe",
  calm_breath: "breathe",
  pause: "pause",
  music: "music",
  water: "water",
  hydrate: "hydrate",
  plant: "plant",
  walk: "walk",
  stretch: "stretch",
  tidy: "tidy",
  snack: "snack",
  gratitude: "gratitude",
  kind_self: "kind-self",
  note: "note",
  adventure: "adventure",
};

const VARIETY_POOL: Exclude<MonsterClipAction, "idle">[] = [
  "mood-react",
  "breathe",
  "water",
  "kind",
  "surprise",
  "all-goals",
  "stretch",
  "smile",
  "tidy",
  "sun",
  "window",
  "snack",
  "adventure",
  "walk",
  "hydrate",
  "plant",
  "pause",
  "music",
  "gratitude",
  "note",
  "kind-self",
  "letter",
  "shop",
];

/** Fallback estável por hash — missões novas não caem todas no mesmo clip. */
function clipFromKeyHash(goalKey: string): Exclude<MonsterClipAction, "idle" | "all-goals" | "shop" | "letter"> {
  const pool: Exclude<MonsterClipAction, "idle" | "all-goals" | "shop" | "letter">[] = [
    "mood-react",
    "breathe",
    "water",
    "kind",
    "surprise",
    "stretch",
    "smile",
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
  if (event === "shop") return "shop";
  if (event === "journal") return "letter";
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
  for (let i = 0; i < recent.length; i += 1) {
    const older = recent[i];
    if (older && older !== "idle" && older !== preferred) return older;
  }
  return preferred;
}
