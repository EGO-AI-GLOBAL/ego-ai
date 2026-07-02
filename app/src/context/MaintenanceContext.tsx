import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { AppState, type AppStateStatus } from "react-native";
import {
  DEFAULT_UPDATING_MESSAGE,
  fetchPublicHealth,
} from "@/api/client";

type MaintenanceContextValue = {
  /** Faixa “Atualizando” visível no topo */
  showBanner: boolean;
  message: string;
  refresh: () => Promise<void>;
};

const MaintenanceContext = createContext<MaintenanceContextValue | null>(null);

const POLL_MS = 60_000;

export function MaintenanceProvider({ children }: { children: React.ReactNode }) {
  const [showBanner, setShowBanner] = useState(false);
  const [message, setMessage] = useState(DEFAULT_UPDATING_MESSAGE);

  const refresh = useCallback(async () => {
    const health = await fetchPublicHealth();
    if (!health) {
      setShowBanner(true);
      setMessage(DEFAULT_UPDATING_MESSAGE);
      return;
    }
    if (health.maintenance) {
      setShowBanner(true);
      setMessage(
        (health.maintenance_message || "").trim() || DEFAULT_UPDATING_MESSAGE
      );
      return;
    }
    setShowBanner(false);
  }, []);

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
    () => ({ showBanner, message, refresh }),
    [showBanner, message, refresh]
  );

  return (
    <MaintenanceContext.Provider value={value}>
      {children}
    </MaintenanceContext.Provider>
  );
}

export function useMaintenance() {
  const ctx = useContext(MaintenanceContext);
  if (!ctx) {
    throw new Error("useMaintenance fora do MaintenanceProvider");
  }
  return ctx;
}
