import AsyncStorage from "@react-native-async-storage/async-storage";
import { STORAGE_KEY } from "@/api/client";
import { clearAuthAppVersion } from "@/storage/authAppVersion";
import { clearLocalPersonaForUser } from "@/storage/personaPrefs";
import {
  deleteSecureItem,
  getSecureItem,
  saveSecureItem,
} from "@/storage/sessionStorage";

const INSTALL_MARKER = "ego_async_install_marker_v1";
const SECURE_INSTALL_MARKER = "ego_secure_install_marker_v1";
const POST_LOGIN_ROUTE_KEY = "ego_post_login_route_v1";
const PERSONA_WIPE_FLAG = "ego_persona_wipe_next_auth_v1";
const PERSONA_KEYCHAIN_MIGRATION = "ego_persona_keychain_migration_v1";

async function markSecureWipeForNextAuth(): Promise<void> {
  await AsyncStorage.setItem(PERSONA_WIPE_FLAG, "1");
}

async function readInstallMarkers(): Promise<{ async: string | null; secure: string | null }> {
  const [asyncMarker, secureMarker] = await Promise.all([
    AsyncStorage.getItem(INSTALL_MARKER),
    getSecureItem(SECURE_INSTALL_MARKER),
  ]);
  return { async: asyncMarker, secure: secureMarker };
}

/** Garante marcadores nos dois storages (AsyncStorage + Keychain). */
export async function ensureInstallMarkers(): Promise<void> {
  const { async: asyncMarker, secure: secureMarker } = await readInstallMarkers();
  const stamp = asyncMarker || secureMarker || String(Date.now());
  await Promise.all([
    AsyncStorage.setItem(INSTALL_MARKER, stamp),
    saveSecureItem(SECURE_INSTALL_MARKER, stamp),
  ]);
}

/**
 * iOS Keychain pode manter a sessão após apagar o app.
 * AsyncStorage é limpo no uninstall — usamos isso para detectar reinstall.
 *
 * Se só o marcador AsyncStorage sumir (bug OEM / limpeza parcial), não apagar sessão válida.
 */
export async function clearSecureSessionIfFreshInstall(): Promise<void> {
  const { async: asyncMarker, secure: secureMarker } = await readInstallMarkers();
  if (asyncMarker || secureMarker) {
    await ensureInstallMarkers();
    return;
  }

  const sessionRaw = await getSecureItem(STORAGE_KEY);
  if (sessionRaw?.trim()) {
    // Sessão válida no telefone, marcadores perdidos — recuperar sem deslogar.
    await ensureInstallMarkers();
    return;
  }

  await deleteSecureItem(STORAGE_KEY);
  await deleteSecureItem(POST_LOGIN_ROUTE_KEY);
  await clearAuthAppVersion();
  await markSecureWipeForNextAuth();
  await ensureInstallMarkers();
}

/**
 * Utilizadores que já tinham marcador da 1.0.53 sem wipe de persona —
 * força limpeza uma vez na 1.0.54+ para não saltar choose-avatar com lixo no Keychain.
 */
export async function runFreshInstallMigrations(): Promise<void> {
  const done = await AsyncStorage.getItem(PERSONA_KEYCHAIN_MIGRATION);
  if (done) return;
  await AsyncStorage.setItem(PERSONA_KEYCHAIN_MIGRATION, "1");
  await markSecureWipeForNextAuth();
}

/**
 * Após login ou restauro de sessão: limpa persona local se reinstall ou migração pediu.
 * Telefone fica no servidor — não apagar local para não pedir de novo após cadastro.
 */
export async function consumeSecureWipeIfNeeded(userId: string): Promise<void> {
  const uid = userId.trim();
  if (!uid) return;
  const flag = await AsyncStorage.getItem(PERSONA_WIPE_FLAG);
  if (flag !== "1") return;

  await clearLocalPersonaForUser(uid);
  await AsyncStorage.removeItem(PERSONA_WIPE_FLAG);
}
