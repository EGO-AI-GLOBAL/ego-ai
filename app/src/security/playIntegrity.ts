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
/** Não atrasar chat/voz se o módulo Play Integrity travar no Android. */
const TOKEN_REQUEST_MS = 4_000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T | null> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(null), ms);
    promise
      .then((value) => {
        clearTimeout(timer);
        resolve(value);
      })
      .catch(() => {
        clearTimeout(timer);
        resolve(null);
      });
  });
}

function integrityConfigured(): boolean {
  return Platform.OS === "android" && PROJECT_NUMBER.length > 0;
}

async function loadModule(): Promise<IntegrityModule | null> {
  if (!integrityConfigured()) return null;
  try {
    // Opcional: npm install react-native-google-play-integrity (dev build / EAS)
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const raw = require("react-native-google-play-integrity");
    const mod = (raw?.default ?? raw) as IntegrityModule;
    if (
      typeof mod?.isPlayServicesAvailable !== "function" ||
      typeof mod?.prepareIntegrityToken !== "function" ||
      typeof mod?.requestIntegrityToken !== "function"
    ) {
      return null;
    }
    return mod;
  } catch {
    return null;
  }
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
    const token = await withTimeout(mod.requestIntegrityToken(), TOKEN_REQUEST_MS);
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
  prepared = false;
}
