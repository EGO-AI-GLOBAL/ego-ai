import { Platform } from "react-native";

const PROJECT_NUMBER = (
  process.env.EXPO_PUBLIC_GOOGLE_CLOUD_PROJECT_NUMBER || ""
).trim();

type IntegrityModule = {
  isPlayServicesAvailable: () => Promise<boolean>;
  prepareIntegrityToken: (cloudProjectNumber: string) => Promise<void>;
  requestIntegrityToken: () => Promise<string>;
};

let prepared = false;
let preparePromise: Promise<boolean> | null = null;
let cachedToken: { token: string; at: number } | null = null;

const TOKEN_CACHE_MS = 90_000;

function integrityConfigured(): boolean {
  return Platform.OS === "android" && PROJECT_NUMBER.length > 0;
}

async function loadModule(): Promise<IntegrityModule | null> {
  // Play Integrity nativo removido do build v1 (evita falha Gradle no EAS).
  // Reativar quando EXPO_PUBLIC_GOOGLE_CLOUD_PROJECT_NUMBER estiver configurado.
  if (!integrityConfigured()) return null;
  return null;
}

/** Prepara Play Integrity (Android). Chamar após login ou no arranque. */
export async function preparePlayIntegrity(): Promise<boolean> {
  if (!integrityConfigured()) return false;
  if (prepared) return true;
  if (preparePromise) return preparePromise;

  preparePromise = (async () => {
    const mod = await loadModule();
    if (!mod) return false;
    try {
      const ok = await mod.isPlayServicesAvailable();
      if (!ok) return false;
      await mod.prepareIntegrityToken(PROJECT_NUMBER);
      prepared = true;
      return true;
    } catch {
      return false;
    } finally {
      preparePromise = null;
    }
  })();

  return preparePromise;
}

/** Token para header X-Play-Integrity (cache curto). */
export async function getPlayIntegrityToken(): Promise<string | null> {
  if (!integrityConfigured()) return null;
  if (!prepared) {
    const ok = await preparePlayIntegrity();
    if (!ok) return null;
  }
  if (cachedToken && Date.now() - cachedToken.at < TOKEN_CACHE_MS) {
    return cachedToken.token;
  }
  const mod = await loadModule();
  if (!mod) return null;
  try {
    const token = await mod.requestIntegrityToken();
    if (!token) return null;
    cachedToken = { token, at: Date.now() };
    return token;
  } catch {
    cachedToken = null;
    return null;
  }
}

export function playIntegrityAvailableOnDevice(): boolean {
  return integrityConfigured();
}

export function clearPlayIntegrityCache(): void {
  cachedToken = null;
}
