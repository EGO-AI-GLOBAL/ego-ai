import Constants from "expo-constants";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { AppState, type AppStateStatus } from "react-native";
import { fetchPublicHealth } from "@/api/client";
import { isAppVersionBehind } from "@/utils/appVersion";

type AppUpdateContextValue = {
  showBanner: boolean;
  message: string;
  latestVersion: string;
  playStoreUrl: string;
  iosUpdateUrl: string;
  currentVersion: string;
  refresh: () => Promise<void>;
};

const AppUpdateContext = createContext<AppUpdateContextValue | null>(null);

const POLL_MS = 60_000;

function currentAppVersion(): string {
  return String(Constants.expoConfig?.version || "0.0.0").trim();
}

export function AppUpdateProvider({ children }: { children: React.ReactNode }) {
  const [showBanner, setShowBanner] = useState(false);
  const [message, setMessage] = useState("Nova versão disponível na Play Store.");
  const [latestVersion, setLatestVersion] = useState("");
  const [playStoreUrl, setPlayStoreUrl] = useState("");
  const [iosUpdateUrl, setIosUpdateUrl] = useState("");
  const currentVersion = currentAppVersion();

  const refresh = useCallback(async () => {
    const health = await fetchPublicHealth();
    const info = health?.app_update;
    if (!info?.latest_version?.trim()) {
      setShowBanner(false);
      return;
    }
    const latest = info.latest_version.trim();
    const url = (info.play_store_url || "").trim();
    const iosUrl = (info.ios_update_url || "").trim();
    setLatestVersion(latest);
    setPlayStoreUrl(url);
    setIosUpdateUrl(iosUrl);
    setMessage(
      (info.message || "").trim() ||
        `Versão ${latest} disponível. Você está na ${currentVersion}.`
    );
    setShowBanner(isAppVersionBehind(currentVersion, latest));
  }, [currentVersion]);

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
      message,
      latestVersion,
      playStoreUrl,
      iosUpdateUrl,
      currentVersion,
      refresh,
    }),
    [showBanner, message, latestVersion, playStoreUrl, iosUpdateUrl, currentVersion, refresh]
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
