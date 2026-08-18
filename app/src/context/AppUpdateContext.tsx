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
  getInstalledAppVersion,
  isAppUpdateAvailable,
} from "@/utils/appVersion";

type AppUpdateContextValue = {
  showBanner: boolean;
  needsUpdate: boolean;
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

export function AppUpdateProvider({ children }: { children: React.ReactNode }) {
  const [showBanner, setShowBanner] = useState(false);
  const [needsUpdate, setNeedsUpdate] = useState(false);
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

      if (!latest) {
        setShowBanner(false);
        setNeedsUpdate(false);
        setLatestVersion("");
        return;
      }

      setLatestVersion(latest);
      setPlayStoreUrl((info?.play_store_url || "").trim());
      setIosUpdateUrl((info?.ios_update_url || "").trim());
      const autoMsg = `${latest}: nova versão na loja. Toque em Atualizar agora.`;
      const apiMsg = (info?.message || "").trim();
      setMessage(apiMsg || autoMsg);

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
    }
  }, []);

  const dismissBanner = useCallback(async () => {
    sessionDismissedRef.current = true;
    setShowBanner(false);
    const ver = latestVersion.trim();
    if (ver) {
      await setUpdateBannerDismissedVersion(ver);
    }
  }, [latestVersion]);

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
