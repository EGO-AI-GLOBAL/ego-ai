import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AppState, Platform, type AppStateStatus } from "react-native";
import { fetchPublicHealth } from "@/api/client";
import {
  clearUpdateBannerDismissedVersion,
  getUpdateBannerDismissedVersion,
  setUpdateBannerDismissedVersion,
} from "@/storage/updateBannerPrefs";
import {
  getInstalledAndroidVersionCode,
  getInstalledAppVersion,
  isAppUpdateAvailable,
  isAppVersionBehind,
} from "@/utils/appVersion";

type AppUpdateContextValue = {
  showBanner: boolean;
  needsUpdate: boolean;
  /** Bloqueio total — sem fechar até atualizar. */
  forceUpdate: boolean;
  forceMessage: string;
  message: string;
  latestVersion: string;
  playStoreUrl: string;
  iosUpdateUrl: string;
  currentVersion: string;
  refresh: () => Promise<void>;
  dismissBanner: () => Promise<void>;
};

const AppUpdateContext = createContext<AppUpdateContextValue | null>(null);

const POLL_MS = 60_000;

function mustForceUpdate(input: {
  installed: string;
  minVersion: string;
  minAndroidCode: number;
}): boolean {
  const min = input.minVersion.trim();
  if (min && isAppVersionBehind(input.installed, min)) {
    return true;
  }
  if (Platform.OS === "android" && input.minAndroidCode > 0) {
    const code = getInstalledAndroidVersionCode();
    if (code != null && code < input.minAndroidCode) return true;
  }
  return false;
}

export function AppUpdateProvider({ children }: { children: React.ReactNode }) {
  const [showBanner, setShowBanner] = useState(false);
  const [needsUpdate, setNeedsUpdate] = useState(false);
  const [forceUpdate, setForceUpdate] = useState(false);
  const [forceMessage, setForceMessage] = useState("");
  const [message, setMessage] = useState("");
  const [latestVersion, setLatestVersion] = useState("");
  const [playStoreUrl, setPlayStoreUrl] = useState("");
  const [iosUpdateUrl, setIosUpdateUrl] = useState("");
  const [currentVersion, setCurrentVersion] = useState(getInstalledAppVersion);
  const sessionDismissedRef = useRef(false);

  const refresh = useCallback(async () => {
    const installed = getInstalledAppVersion();
    setCurrentVersion(installed);

    try {
      const health = await fetchPublicHealth();
      const info = health?.app_update;
      const platformLatest =
        Platform.OS === "ios"
          ? (info?.latest_version_ios || info?.latest_version || "").trim()
          : (info?.latest_version_android || info?.latest_version || "").trim();
      const latest = platformLatest;
      const latestAndroidCode =
        typeof info?.android_version_code === "number"
          ? info.android_version_code
          : parseInt(String(info?.android_version_code || ""), 10);
      const androidCodeForCompare =
        Platform.OS === "android" &&
        Number.isFinite(latestAndroidCode) &&
        latestAndroidCode > 0
          ? latestAndroidCode
          : null;

      const minVersion = (info?.min_version || "").trim();
      const minAndroidCodeRaw =
        typeof info?.min_android_version_code === "number"
          ? info.min_android_version_code
          : parseInt(String(info?.min_android_version_code || ""), 10);
      const minAndroidCode =
        Number.isFinite(minAndroidCodeRaw) && minAndroidCodeRaw > 0
          ? minAndroidCodeRaw
          : 0;
      const apiForce = Boolean(info?.force_update) && (Boolean(minVersion) || minAndroidCode > 0);
      const blocked =
        apiForce &&
        mustForceUpdate({
          installed,
          minVersion,
          minAndroidCode,
        });

      setForceUpdate(blocked);
      setForceMessage(
        blocked
          ? (info?.force_message || "").trim() ||
              `Atualize para a v${minVersion || latest} para continuar.`
          : ""
      );

      if (!latest && !blocked) {
        setShowBanner(false);
        setNeedsUpdate(false);
        setLatestVersion("");
        return;
      }

      setLatestVersion(latest || minVersion);
      setPlayStoreUrl((info?.play_store_url || "").trim());
      setIosUpdateUrl((info?.ios_update_url || "").trim());
      const autoMsg = `${latest}: nova versão na loja. Toque em Atualizar agora.`;
      const apiMsg = (info?.message || "").trim();
      setMessage(apiMsg || autoMsg);

      if (blocked) {
        setNeedsUpdate(true);
        setShowBanner(false);
        return;
      }

      const behind = isAppUpdateAvailable(
        installed,
        latest,
        androidCodeForCompare
      );

      if (!behind) {
        sessionDismissedRef.current = false;
        await clearUpdateBannerDismissedVersion();
        setNeedsUpdate(false);
        setShowBanner(false);
        return;
      }

      setNeedsUpdate(true);

      const dismissed = await getUpdateBannerDismissedVersion();
      if (sessionDismissedRef.current || dismissed === latest) {
        sessionDismissedRef.current = true;
        setShowBanner(false);
        return;
      }

      setShowBanner(true);
    } catch {
      setShowBanner(false);
      setNeedsUpdate(false);
      setForceUpdate(false);
    }
  }, []);

  const dismissBanner = useCallback(async () => {
    if (forceUpdate) return;
    sessionDismissedRef.current = true;
    setShowBanner(false);
    const ver = latestVersion.trim();
    if (ver) {
      await setUpdateBannerDismissedVersion(ver);
    }
  }, [forceUpdate, latestVersion]);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), POLL_MS);
    const sub = AppState.addEventListener("change", (state: AppStateStatus) => {
      if (state === "active") void refresh();
    });
    return () => {
      clearInterval(id);
      sub.remove();
    };
  }, [refresh]);

  const value = useMemo(
    () => ({
      showBanner,
      needsUpdate,
      forceUpdate,
      forceMessage,
      message,
      latestVersion,
      playStoreUrl,
      iosUpdateUrl,
      currentVersion,
      refresh,
      dismissBanner,
    }),
    [
      showBanner,
      needsUpdate,
      forceUpdate,
      forceMessage,
      message,
      latestVersion,
      playStoreUrl,
      iosUpdateUrl,
      currentVersion,
      refresh,
      dismissBanner,
    ]
  );

  return (
    <AppUpdateContext.Provider value={value}>{children}</AppUpdateContext.Provider>
  );
}

export function useAppUpdate() {
  const ctx = useContext(AppUpdateContext);
  if (!ctx) {
    throw new Error("useAppUpdate fora do AppUpdateProvider");
  }
  return ctx;
}
