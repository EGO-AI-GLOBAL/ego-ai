import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const SESSION_MIRROR_KEY = "ego_auth_session_mirror_v1";
/** Chunks no SecureStore — Android limita ~2048 bytes por chave (JWTs juntos passam). */
const SESSION_ACCESS_KEY = "ego_auth_access_v1";
const SESSION_REFRESH_KEY = "ego_auth_refresh_v1";
const SESSION_META_KEY = "ego_auth_meta_v1";

function usesSessionMirror(key: string): boolean {
  return key === "ego_auth_session";
}

function sessionLooksComplete(raw: string | null): boolean {
  if (!raw?.trim()) return false;
  try {
    const parsed = JSON.parse(raw) as {
      access_token?: string;
      refresh_token?: string;
    };
    return Boolean(parsed.access_token?.trim() && parsed.refresh_token?.trim());
  } catch {
    return false;
  }
}

function pickBetterSessionRaw(a: string | null, b: string | null): string | null {
  const aOk = sessionLooksComplete(a);
  const bOk = sessionLooksComplete(b);
  if (aOk && !bOk) return a;
  if (bOk && !aOk) return b;
  if (a && b) return a.length >= b.length ? a : b;
  return a || b;
}

async function saveSessionChunks(value: string): Promise<void> {
  try {
    const parsed = JSON.parse(value) as {
      access_token?: string;
      refresh_token?: string;
      expires_at?: number | null;
      user?: { id?: string; email?: string };
    };
    const access = String(parsed.access_token || "").trim();
    const refresh = String(parsed.refresh_token || "").trim();
    if (!access) return;
    const meta = JSON.stringify({
      expires_at: parsed.expires_at ?? null,
      user: {
        id: String(parsed.user?.id || ""),
        email: String(parsed.user?.email || ""),
      },
    });
    await Promise.all([
      SecureStore.setItemAsync(SESSION_ACCESS_KEY, access, {
        keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK,
      }),
      SecureStore.setItemAsync(SESSION_REFRESH_KEY, refresh, {
        keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK,
      }),
      SecureStore.setItemAsync(SESSION_META_KEY, meta, {
        keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK,
      }),
    ]);
  } catch {
    /* chunks opcionais — espelho AsyncStorage é a rede de segurança */
  }
}

async function readSessionFromChunks(): Promise<string | null> {
  try {
    const [access, refresh, metaRaw] = await Promise.all([
      SecureStore.getItemAsync(SESSION_ACCESS_KEY),
      SecureStore.getItemAsync(SESSION_REFRESH_KEY),
      SecureStore.getItemAsync(SESSION_META_KEY),
    ]);
    if (!access?.trim()) return null;
    let meta: {
      expires_at?: number | null;
      user?: { id?: string; email?: string };
    } = {};
    try {
      meta = metaRaw ? JSON.parse(metaRaw) : {};
    } catch {
      meta = {};
    }
    return JSON.stringify({
      access_token: access,
      refresh_token: refresh || "",
      expires_at: meta.expires_at ?? null,
      user: {
        id: String(meta.user?.id || ""),
        email: String(meta.user?.email || ""),
      },
    });
  } catch {
    return null;
  }
}

async function deleteSessionChunks(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(SESSION_ACCESS_KEY).catch(() => undefined),
    SecureStore.deleteItemAsync(SESSION_REFRESH_KEY).catch(() => undefined),
    SecureStore.deleteItemAsync(SESSION_META_KEY).catch(() => undefined),
  ]);
}

export async function saveSecureItem(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    await AsyncStorage.setItem(key, value);
    return;
  }

  // Sessão: espelho AsyncStorage PRIMEIRO.
  // No Android o SecureStore falha acima de ~2048 bytes; se o espelho só
  // gravasse depois, o login ficava só em memória e sumia ao reabrir.
  if (usesSessionMirror(key)) {
    try {
      await AsyncStorage.setItem(SESSION_MIRROR_KEY, value);
    } catch {
      /* ignore */
    }
    await saveSessionChunks(value);
  }

  try {
    await SecureStore.setItemAsync(key, value, {
      keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK,
    });
  } catch {
    // Tamanho/Keychain — sessão já tem espelho + chunks; outros keys usam fallback.
    if (!usesSessionMirror(key)) {
      try {
        await AsyncStorage.setItem(`ego_secure_fallback_${key}`, value);
      } catch {
        /* ignore */
      }
    }
  }
}

export async function getSecureItem(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    return AsyncStorage.getItem(key);
  }

  if (usesSessionMirror(key)) {
    let secure: string | null = null;
    let mirror: string | null = null;
    let chunks: string | null = null;
    try {
      secure = await SecureStore.getItemAsync(key);
    } catch {
      /* Keychain indisponível */
    }
    try {
      mirror = await AsyncStorage.getItem(SESSION_MIRROR_KEY);
    } catch {
      /* ignore */
    }
    chunks = await readSessionFromChunks();
    return pickBetterSessionRaw(pickBetterSessionRaw(secure, mirror), chunks);
  }

  try {
    const secure = await SecureStore.getItemAsync(key);
    if (secure) return secure;
  } catch {
    /* Keychain indisponível */
  }
  try {
    return await AsyncStorage.getItem(`ego_secure_fallback_${key}`);
  } catch {
    return null;
  }
}

export async function deleteSecureItem(key: string): Promise<void> {
  if (Platform.OS === "web") {
    await AsyncStorage.removeItem(key);
    return;
  }
  try {
    await SecureStore.deleteItemAsync(key);
  } catch {
    /* ignore */
  }
  if (usesSessionMirror(key)) {
    try {
      await AsyncStorage.removeItem(SESSION_MIRROR_KEY);
    } catch {
      /* ignore */
    }
    await deleteSessionChunks();
  } else {
    try {
      await AsyncStorage.removeItem(`ego_secure_fallback_${key}`);
    } catch {
      /* ignore */
    }
  }
}
