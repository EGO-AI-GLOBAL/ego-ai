import AsyncStorage from "@react-native-async-storage/async-storage";
import { STORAGE_KEY } from "@/api/client";
import { clearAuthAppVersion } from "@/storage/authAppVersion";
import { deleteSecureItem } from "@/storage/sessionStorage";

const INSTALL_MARKER = "ego_async_install_marker_v1";
const POST_LOGIN_ROUTE_KEY = "ego_post_login_route_v1";

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
  await AsyncStorage.setItem(INSTALL_MARKER, String(Date.now()));
}
