import * as SecureStore from "expo-secure-store";

const KEY = "ego_password_recovery_v1";

export type PasswordRecoveryTokens = {
  access_token: string;
  refresh_token: string;
};

export async function savePasswordRecoveryTokens(
  tokens: PasswordRecoveryTokens
): Promise<void> {
  await SecureStore.setItemAsync(KEY, JSON.stringify(tokens));
}

export async function loadPasswordRecoveryTokens(): Promise<PasswordRecoveryTokens | null> {
  try {
    const raw = await SecureStore.getItemAsync(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PasswordRecoveryTokens;
    if (!parsed?.access_token || !parsed?.refresh_token) return null;
    return parsed;
  } catch {
    return null;
  }
}

export async function clearPasswordRecoveryTokens(): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(KEY);
  } catch {
    /* ignore */
  }
}
