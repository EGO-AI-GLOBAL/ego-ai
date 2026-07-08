import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const SESSION_MIRROR_KEY = "ego_auth_session_mirror_v1";

function usesSessionMirror(key: string): boolean {
  return key === "ego_auth_session";
}

export async function saveSecureItem(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    await AsyncStorage.setItem(key, value);
    return;
  }
  // AFTER_FIRST_UNLOCK: sessão persiste ao reabrir o app (iOS Keychain).
  await SecureStore.setItemAsync(key, value, {
    keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK,
  });
  if (usesSessionMirror(key)) {
    await AsyncStorage.setItem(SESSION_MIRROR_KEY, value);
  }
}

export async function getSecureItem(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    return AsyncStorage.getItem(key);
  }
  try {
    const secure = await SecureStore.getItemAsync(key);
    if (secure) return secure;
  } catch {
    /* Keychain indisponível — tenta espelho AsyncStorage */
  }
  if (usesSessionMirror(key)) {
    try {
      return await AsyncStorage.getItem(SESSION_MIRROR_KEY);
    } catch {
      return null;
    }
  }
  return null;
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
  }
}
