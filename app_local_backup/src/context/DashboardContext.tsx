import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { fetchDashboard, getSession } from "@/api/client";
import { resolveUserId } from "@/utils/resolveUserId";
import type { DashboardData, SendChatResult } from "@/api/types";
import { chatResultChangedData, mergeChatIntoDashboard } from "@/utils/mergeChatDashboard";
import { accountPersona } from "@/constants/personas";
import { useAuth } from "@/context/AuthContext";
import { registerExpoPushToken } from "@/utils/pushRegistration";
import {
  cancelAllReminderLocalNotifications,
  syncReminderLocalNotifications,
} from "@/utils/reminderNotifications";
import {
  notifyNewSharedEventsFromOthers,
  syncSharedCalendarLocalNotifications,
} from "@/utils/sharedCalendarNotifications";
import {
  getLocalPersonaChoice,
  isPersonaConfiguredLocal,
  markPersonaConfiguredLocal,
  saveLocalPersonaChoice,
} from "@/storage/personaPrefs";

const empty: DashboardData = {
  health: null,
  me: null,
  access: null,
  reminders: [],
  agenda: [],
  shared_calendars: [],
  messages: [],
};

type RefreshOptions = {
  /** Evita expo-notifications após chat (agenda compartilhada costuma crashar no Android). */
  skipNotifications?: boolean;
};

type DashboardContextValue = {
  data: DashboardData;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refresh: (options?: RefreshOptions) => Promise<void>;
  /** Atualiza agenda/lembretes a partir da resposta do chat (sem rede). */
  mergeChatResult: (result: SendChatResult) => void;
  setPersona: (avatarId: string, voiceId: string) => void;
  /** true se o servidor ou o telemóvel já registou escolha de assistente */
  personaGateOk: boolean;
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  const enabled = Boolean(session?.access_token?.trim());
  const [data, setData] = useState<DashboardData>(empty);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [personaLocalOk, setPersonaLocalOk] = useState(false);

  const load = useCallback(async (options?: RefreshOptions) => {
    if (!enabled) {
      setData(empty);
      setLoading(false);
      setPersonaLocalOk(false);
      void cancelAllReminderLocalNotifications();
      return;
    }
    if (!getSession()?.access_token?.trim()) {
      setError("Sessão expirada. Saia e entre novamente.");
      return;
    }
    setError(null);
    try {
      let dashboard = await fetchDashboard();
      const uid = resolveUserId(session, dashboard.me?.user_id);
      const localChoice = uid ? await getLocalPersonaChoice(uid) : null;
      if (localChoice) {
        const persona = accountPersona(localChoice);
        if (dashboard.me) {
          const server = dashboard.me.persona;
          const serverAid = (server?.avatar_id || "f1").toLowerCase();
          const localAid = localChoice.avatar_id.toLowerCase();
          if (serverAid !== localAid || !dashboard.me.persona_configured) {
            dashboard = {
              ...dashboard,
              me: {
                ...dashboard.me,
                persona,
                persona_configured: true,
              },
            };
          }
        } else {
          dashboard = {
            ...dashboard,
            me: {
              user_id: uid,
              email: getSession()?.user?.email ?? null,
              persona,
              persona_configured: true,
              profile: {},
              access: { allowed: true, status: "ok" },
              stripe_checkout: {},
            },
          };
        }
      }
      setData(dashboard);
      if (dashboard.me?.persona_configured === true && uid) {
        setPersonaLocalOk(true);
        void markPersonaConfiguredLocal(uid);
      } else if (uid) {
        const local = await isPersonaConfiguredLocal(uid);
        setPersonaLocalOk(local);
      } else {
        setPersonaLocalOk(false);
      }
      if (!options?.skipNotifications) {
        void syncReminderLocalNotifications(dashboard.reminders).catch(() => {});
        const shared = dashboard.shared_calendars ?? [];
        void registerExpoPushToken();
        void notifyNewSharedEventsFromOthers(shared, uid).catch(() => {});
        void syncSharedCalendarLocalNotifications(shared).catch(() => {});
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro ao carregar dados.";
      const uid = resolveUserId(session);
      if (uid) {
        const local = await getLocalPersonaChoice(uid);
        if (local) {
          const persona = accountPersona(local);
          setData((prev) => ({
            ...prev,
            me: prev.me ?? {
              user_id: uid,
              email: getSession()?.user?.email ?? null,
              persona,
              persona_configured: true,
              profile: {},
              access: { allowed: true, status: "ok" },
              stripe_checkout: {},
            },
          }));
          setPersonaLocalOk(true);
        }
      }
      if (/token ausente|sessão inválida|sessão expirada/i.test(msg)) {
        setError("Sessão expirada. Saia e entre novamente.");
      } else if (!uid || !(await isPersonaConfiguredLocal(uid))) {
        setError(msg);
      }
    }
  }, [enabled, session]);

  useEffect(() => {
    if (!enabled) {
      setData(empty);
      setLoading(false);
      setPersonaLocalOk(false);
      void cancelAllReminderLocalNotifications();
      return;
    }
    setLoading(true);
    load().finally(() => setLoading(false));
  }, [enabled, load]);

  const refresh = useCallback(async (options?: RefreshOptions) => {
    if (!enabled) return;
    setRefreshing(true);
    await load(options);
    setRefreshing(false);
  }, [enabled, load]);

  const mergeChatResult = useCallback((result: SendChatResult) => {
    if (!chatResultChangedData(result)) return;
    setData((prev) => mergeChatIntoDashboard(prev, result));
  }, []);

  const setPersona = useCallback((avatarId: string, voiceId: string) => {
    const persona = accountPersona({ avatar_id: avatarId, voice_id: voiceId });
    const uid = resolveUserId(session, data.me?.user_id);
    setPersonaLocalOk(true);
    if (uid) {
      void markPersonaConfiguredLocal(uid);
      void saveLocalPersonaChoice(uid, persona);
    }
    setData((prev) => ({
      ...prev,
      me: prev.me
        ? {
            ...prev.me,
            persona,
            persona_configured: true,
          }
        : uid
          ? {
              user_id: uid,
              email: getSession()?.user?.email ?? null,
              persona,
              persona_configured: true,
              profile: {},
              access: { allowed: true, status: "ok" },
              stripe_checkout: {},
            }
          : prev.me,
    }));
  }, [data.me?.user_id, session]);

  const personaGateOk =
    personaLocalOk ||
    data.me?.persona_configured === true ||
    (data.me?.persona_configured == null && Boolean(data.me?.persona));

  const value = useMemo(
    () => ({
      data,
      loading,
      refreshing,
      error,
      refresh,
      mergeChatResult,
      setPersona,
      personaGateOk,
    }),
    [data, loading, refreshing, error, refresh, mergeChatResult, setPersona, personaGateOk]
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
