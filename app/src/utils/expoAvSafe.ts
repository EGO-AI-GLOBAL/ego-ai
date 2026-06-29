export type ExpoAv = typeof import("expo-av");

let cached: ExpoAv | null | undefined;

/** Carrega expo-av só quando necessário — evita crash ao abrir o chat. */
export function loadExpoAv(): ExpoAv | null {
  if (cached !== undefined) return cached;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    cached = require("expo-av") as ExpoAv;
  } catch {
    cached = null;
  }
  return cached;
}

export function getExpoAudio(): ExpoAv["Audio"] | null {
  return loadExpoAv()?.Audio ?? null;
}
