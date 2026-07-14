/**
 * Clips Calma 1 min (WayIn) — require() estáticos para Metro.
 * Fonte: marketing/wayin/CALMA-1-MIN-ANIMS/entregues/
 */
export const CALMA_CLIP_KEYS = [
  "breath44",
  "long_exh",
  "phys_sigh",
  "shoulders",
  "feet_floor",
  "pause1",
  "box_breath",
  "ground543",
  "sounds3",
  "colors3",
  "jaw_relax",
  "belly_br",
  "worry_later",
  "compassion",
  "control1",
  "hand_press",
  "feet_rel",
  "pace4",
  "mood_link",
  "avatar_1",
  "sos",
] as const;

export type CalmaClipKey = (typeof CALMA_CLIP_KEYS)[number];

const CLIPS: Record<CalmaClipKey, number> = {
  breath44: require("../../assets/calma-clips/01-breath44.mp4"),
  long_exh: require("../../assets/calma-clips/02-long_exh.mp4"),
  phys_sigh: require("../../assets/calma-clips/03-phys_sigh.mp4"),
  shoulders: require("../../assets/calma-clips/04-shoulders.mp4"),
  feet_floor: require("../../assets/calma-clips/05-feet_floor.mp4"),
  pause1: require("../../assets/calma-clips/06-pause1.mp4"),
  box_breath: require("../../assets/calma-clips/07-box_breath.mp4"),
  ground543: require("../../assets/calma-clips/08-ground543.mp4"),
  sounds3: require("../../assets/calma-clips/09-sounds3.mp4"),
  colors3: require("../../assets/calma-clips/10-colors3.mp4"),
  jaw_relax: require("../../assets/calma-clips/11-jaw_relax.mp4"),
  belly_br: require("../../assets/calma-clips/12-belly_br.mp4"),
  worry_later: require("../../assets/calma-clips/13-worry_later.mp4"),
  compassion: require("../../assets/calma-clips/14-compassion.mp4"),
  control1: require("../../assets/calma-clips/15-control1.mp4"),
  hand_press: require("../../assets/calma-clips/16-hand_press.mp4"),
  feet_rel: require("../../assets/calma-clips/17-feet_rel.mp4"),
  pace4: require("../../assets/calma-clips/18-pace4.mp4"),
  mood_link: require("../../assets/calma-clips/19-mood_link.mp4"),
  avatar_1: require("../../assets/calma-clips/20-avatar_1.mp4"),
  sos: require("../../assets/calma-clips/21-sos.mp4"),
};

export function isCalmaClipKey(key?: string | null): key is CalmaClipKey {
  return Boolean(key && key in CLIPS);
}

/** Fallback breath44 se key desconhecida. */
export function calmaClipModule(key?: string | null): number {
  if (key && isCalmaClipKey(key)) return CLIPS[key];
  return CLIPS.breath44;
}

export function resolveCalmaClipKey(key?: string | null, sosMode?: boolean): CalmaClipKey {
  if (sosMode) return "sos";
  if (key && isCalmaClipKey(key)) return key;
  return "breath44";
}
