import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { fetchDashboard, getSession } from "@/api/client";
import type { DashboardData } from "@/api/types";
import { accountPersona } from "@/constants/personas";
import { useAuth } from "@/context/AuthContext";

const empty: DashboardData = {
  health: null,
  me: null,
  access: null,
  reminders: [],
  agenda: [],
  shared_calendars: [],
  messages: [],
};

type DashboardContextValue = {
  data: DashboardData;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  setPersona: (avatarId: string, voiceId: string) => void;
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  const enabled = Boolean(session?.access_token?.trim());
  const [data, setData] = useState<DashboardData>(empty);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!enabled) {
      setData(empty);
      setLoading(false);
      return;
    }
    if (!getSession()?.access_token?.trim()) {
      setError("Sessão expirada. Saia e entre novamente.");
      return;
    }
    setError(null);
    try {
      const dashboard = await fetchDashboard();
      setData(dashboard);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro ao carregar dados.";
      if (/token ausente|sessão inválida|sessão expirada/i.test(msg)) {
        setError("Sessão expirada. Saia e entre novamente.");
      } else {
        setError(msg);
      }
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      setData(empty);
      setLoading(false);
      return;
    }
    setLoading(true);
    load().finally(() => setLoading(false));
  }, [enabled, load]);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [enabled, load]);

  const setPersona = useCallback((avatarId: string, voiceId: string) => {
    const persona = accountPersona({ avatar_id: avatarId, voice_id: voiceId });
    setData((prev) => ({
      ...prev,
      me: prev.me
        ? {
            ...prev.me,
            persona,
            persona_configured: true,
          }
        : prev.me,
    }));
  }, []);

  const value = useMemo(
    () => ({ data, loading, refreshing, error, refresh, setPersona }),
    [data, loading, refreshing, error, refresh, setPersona]
  );

  return (
    <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>
  );
}

export function useDashboard() {
  const ctx = useContext(DashboardContext);
  if (!ctx) {
    throw new Error("useDashboard deve ser usado dentro de DashboardProvider");
  }
  return ctx;
}
