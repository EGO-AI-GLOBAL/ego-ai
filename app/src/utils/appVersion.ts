import { Platform } from "react-native";
import Constants from "expo-constants";
import * as Application from "expo-application";

/** Compara versões semver simples (ex.: 1.0.9 vs 1.0.11). */
export function parseAppVersion(raw: string): number[] {
  const clean = (raw || "")
    .trim()
    .replace(/^ego-ai@/i, "")
    .split(/[+\s]/)[0];
  return clean.split(".").map((part) => {
    const n = parseInt(part.replace(/\D/g, ""), 10);
    return Number.isFinite(n) ? n : 0;
  });
}

export function isAppVersionBehind(current: string, latest: string): boolean {
  const a = parseAppVersion(current);
  const b = parseAppVersion(latest);
  const len = Math.max(a.length, b.length);
  for (let i = 0; i < len; i += 1) {
    const left = a[i] ?? 0;
    const right = b[i] ?? 0;
    if (left < right) return true;
    if (left > right) return false;
  }
  return false;
}

function configAppVersion(): string {
  const fromConfig = Constants.expoConfig?.version?.trim();
  const fromManifest2 = (
    Constants.manifest2 as { extra?: { expoClient?: { version?: string } } } | null
  )?.extra?.expoClient?.version?.trim();
  const fromManifest = (
    Constants.manifest as { version?: string } | null
  )?.version?.trim();
  return fromConfig || fromManifest2 || fromManifest || "";
}

/** Versão instalada (Play/TestFlight). */
export function getInstalledAppVersion(): string {
  const fromNative = Application.nativeApplicationVersion?.trim();
  if (fromNative && fromNative !== "0.0.0") return fromNative;
  const fromConfig = configAppVersion();
  if (fromConfig && fromConfig !== "0.0.0") return fromConfig;
  return fromNative || fromConfig || "0.0.0";
}

/** Version code Android (Play) — mais fiável que versionName em alguns builds. */
export function getInstalledAndroidVersionCode(): number | null {
  if (Platform.OS !== "android") return null;
  const raw = Application.nativeBuildVersion?.trim();
  if (!raw) return null;
  const n = parseInt(raw.replace(/\D/g, ""), 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function isAppUpdateAvailable(
  installed: string,
  latest: string,
  latestAndroidCode?: number | null
): boolean {
  const latestTrim = (latest || "").trim();
  if (!latestTrim || latestTrim === "0.0.0") return false;

  if (Platform.OS === "android" && latestAndroidCode != null && latestAndroidCode > 0) {
    const code = getInstalledAndroidVersionCode();
    if (code != null && code < latestAndroidCode) return true;
  }

  const installedTrim = (installed || "").trim();
  if (!installedTrim || installedTrim === "0.0.0") {
    return true;
  }
  return isAppVersionBehind(installedTrim, latestTrim);
}
