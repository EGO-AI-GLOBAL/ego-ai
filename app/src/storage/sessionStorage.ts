import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

export async function saveSecureItem(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    await AsyncStorage.setItem(key, value);
    return;
  }
  // AFTER_FIRST_UNLOCK: sessão persiste ao reabrir o app (iOS Keychain).
  await SecureStore.setItemAsync(key, value, {
    keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK,
  });
}

export async function getSecureItem(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    return AsyncStorage.getItem(key);
  }
  return SecureStore.getItemAsync(key);
}

export async function deleteSecureItem(key: string): Promise<void> {
  if (Platform.OS === "web") {
    await AsyncStorage.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}
