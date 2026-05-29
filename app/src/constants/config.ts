import { Platform } from "react-native";
import Constants from "expo-constants";
import { lightColors } from "@/theme/colors";

/** @deprecated Prefira useColors() em ecrãs novos */
export const COLORS = lightColors;

const ANDROID_EMULATOR = "http://10.0.2.2:5000";
const IOS_SIMULATOR = "http://localhost:5000";

function isPrivateLanHost(host: string): boolean {
  return (
    host.startsWith("192.168.") ||
    host.startsWith("10.") ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(host)
  );
}

function defaultHost(): string {
  if (Platform.OS === "web") return "http://localhost:5000";
  if (Platform.OS === "android") return ANDROID_EMULATOR;
  return IOS_SIMULATOR;
}

function resolveBaseUrl(): string {
  const envUrl = (process.env.EXPO_PUBLIC_API_URL || "").replace(/\/$/, "").trim();
  // Com Railway/produção definido: ligação direta (multipart de voz não passa bem no proxy Metro).
  if (envUrl) {
    return envUrl;
  }
  if (Platform.OS === "web") {
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      // Web dev sem URL externa: proxy Metro (/api/v1) para Flask local.
      if (
        host === "localhost" ||
        host === "127.0.0.1" ||
        isPrivateLanHost(host) ||
        window.location.protocol === "https:"
      ) {
        return "";
      }
    }
    return envUrl;
  }
  return envUrl || defaultHost();
}

export const API_BASE_URL = resolveBaseUrl();

export const API_V1 =
  Platform.OS === "web" && !API_BASE_URL
    ? "/api/v1"
    : `${API_BASE_URL}/api/v1`;

/** URL pública HTTPS para a ficha da Play Store (opcional; ecrã in-app usa API). */
export const PRIVACY_POLICY_URL =
  process.env.EXPO_PUBLIC_PRIVACY_POLICY_URL?.trim() ||
  (Constants.expoConfig?.extra?.privacyPolicyUrl as string) ||
  "";

export function isProductionApiOk(): boolean {
  if (Platform.OS === "web" && !process.env.EXPO_PUBLIC_API_URL) return true;
  const url = API_BASE_URL;
  if (!url) return false;
  if (url.startsWith("https://")) return true;
  return process.env.EXPO_PUBLIC_ALLOW_HTTP === "1";
}
