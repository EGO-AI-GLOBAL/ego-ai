import AsyncStorage from "@react-native-async-storage/async-storage";
import { STORAGE_KEY } from "@/api/client";
import { clearAuthAppVersion } from "@/storage/authAppVersion";
import { clearLocalPersonaForUser } from "@/storage/personaPrefs";
import { clearLocalProfilePhone } from "@/storage/profilePhoneLocal";
import { deleteSecureItem } from "@/storage/sessionStorage";

const INSTALL_MARKER = "ego_async_install_marker_v1";
const POST_LOGIN_ROUTE_KEY = "ego_post_login_route_v1";
const PERSONA_WIPE_FLAG = "ego_persona_wipe_next_auth_v1";
const PERSONA_KEYCHAIN_MIGRATION = "ego_persona_keychain_migration_v1";

async function markSecureWipeForNextAuth(): Promise<void> {
  await AsyncStorage.setItem(PERSONA_WIPE_FLAG, "1");
}

/**
 * iOS Keychain pode manter a sessão após apagar o app.
 * AsyncStorage é limpo no uninstall — usamos isso para detectar reinstall.
 */
export async function clearSecureSessionIfFreshInstall(): Promise<void> {
  const marker = await AsyncStorage.getItem(INSTALL_MARKER);
  if (marker) return;

  await deleteSecureItem(STORAGE_KEY);
  await deleteSecureItem(POST_LOGIN_ROUTE_KEY);
  await clearAuthAppVersion();
  await markSecureWipeForNextAuth();
  await AsyncStorage.setItem(INSTALL_MARKER, String(Date.now()));
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
 * Após login ou restauro de sessão: limpa persona/telefone local se reinstall ou migração pediu.
 */
export async function consumeSecureWipeIfNeeded(userId: string): Promise<void> {
  const uid = userId.trim();
  if (!uid) return;
  const flag = await AsyncStorage.getItem(PERSONA_WIPE_FLAG);
  if (flag !== "1") return;

  await clearLocalPersonaForUser(uid);
  await clearLocalProfilePhone(uid);
  await AsyncStorage.removeItem(PERSONA_WIPE_FLAG);
}
