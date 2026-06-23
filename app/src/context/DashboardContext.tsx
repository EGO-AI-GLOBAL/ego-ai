import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { fetchAccessInfo, fetchDashboard, getSession } from "@/api/client";
import { normalizeAccessInfo } from "@/constants/planLimits";
import type { AccessInfo } from "@/api/types";
import { loadLocalChatHistory } from "@/storage/chatHistoryLocal";
import { estimateTokenDelta } from "@/utils/usageStats";
import { resolveUserId } from "@/utils/resolveUserId";
import type { DashboardData, SendChatResult, WellnessJourney, DailyCareInfo } from "@/api/types";
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
import { syncDailyCheckInNotification } from "@/utils/dailyCheckInNotification";
import { saveStreakCache } from "@/storage/streakCache";
import {
  getLocalPersonaChoice,
  isPersonaConfiguredLocal,
  markPersonaConfiguredLocal,
  saveLocalPersonaChoice,
} from "@/storage/personaPrefs";
import { getLocalProfilePhone } from "@/storage/profilePhoneLocal";
import { profilePhoneFromMe } from "@/utils/profileComplete";

const empty: DashboardData = {
  health: null,
  me: null,
  access: null,
  reminders: [],
  agenda: [],
  agenda_drafts: [],
  shopping_orphans: [],
  delegation_requests: [],
  streak: { current: 0, longest: 0, active_today: false, at_risk: false },
  wellness_journey: undefined,
  daily_care: undefined,
  shared_calendars: [],
  pending_calendar_invites: [],
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
  /** Atualiza só limites/uso (rápido após chat). */
  refreshAccess: () => Promise<void>;
  setPersona: (avatarId: string, voiceId: string) => void | Promise<void>;
  /** Atualiza telefone no estado local após PATCH /profile (evita loop no gate). */
  mergeProfilePhone: (phone: string) => void;
  /** Atualiza jornada de bem-estar após passo concluído. */
  mergeWellnessJourney: (journey: WellnessJourney) => void;
  mergeDailyCare: (care: DailyCareInfo, journey?: WellnessJourney) => void;
  /** true se o servidor ou o telemóvel já registou escolha de assistente */
  personaGateOk: boolean;
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

async function mergeStoredProfilePhone(
  dashboard: DashboardData,
  uid: string | null
): Promise<DashboardData> {
  if (!uid) return dashboard;
  const localPh = await getLocalProfilePhone(uid).catch(() => null);
  if (!localPh?.trim() || profilePhoneFromMe(dashboard.me)) {
    return dashboard;
  }
  const phone = localPh.trim();
  if (dashboard.me) {
    return {
      ...dashboard,
      me: {
        ...dashboard.me,
        profile: {
          ...(dashboard.me.profile ?? {}),
          phone,
        },
      },
    };
  }
  return {
    ...dashboard,
    me: {
      user_id: uid,
      email: getSession()?.user?.email ?? null,
      profile: { phone },
      persona_configured: false,
      persona: { avatar_id: "f1", voice_id: "vf1" },
      access: { allowed: true, status: "ok" },
      stripe_checkout: {},
    },
  };
}

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
          dashboard = {
            ...dashboard,
            me: {
              ...dashboard.me,
              persona,
              persona_configured: true,
            },
          };
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
      if (uid && dashboard.access) {
        const msgs = await loadLocalChatHistory(uid).catch(() => []);
        let est = 0;
        for (let i = 0; i < msgs.length; i++) {
          const m = msgs[i];
          const prev = i > 0 ? msgs[i - 1] : null;
          if (m.role === "assistant" && prev?.role === "user") {
            est += estimateTokenDelta(prev.content || "", m.content || "");
          }
        }
        if (est > (dashboard.access.monthly_tokens_used ?? 0)) {
          dashboard = {
            ...dashboard,
            access: normalizeAccessInfo({
              ...dashboard.access,
              monthly_tokens_used: est,
            }),
          };
        }
      }
      dashboard = {
        ...dashboard,
        access: normalizeAccessInfo(dashboard.access),
      };
      dashboard = await mergeStoredProfilePhone(dashboard, uid);
      setData(dashboard);
      void saveStreakCache(dashboard.streak);
      setPersonaLocalOk(Boolean(uid && localChoice));
      if (dashboard.me || (dashboard.shared_calendars?.length ?? 0) > 0) {
        setError(null);
      }
      if (!options?.skipNotifications) {
        void syncReminderLocalNotifications(dashboard.reminders).catch(() => {});
        const shared = dashboard.shared_calendars ?? [];
        void registerExpoPushToken();
        void notifyNewSharedEventsFromOthers(shared, uid).catch(() => {});
        void syncSharedCalendarLocalNotifications(shared).catch(() => {});
        void syncDailyCheckInNotification().catch(() => {});
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

  const refreshAccess = useCallback(async () => {
    if (!enabled) return;
    try {
      const access = normalizeAccessInfo(await fetchAccessInfo());
      if (!access) return;
      setData((prev) => ({
        ...prev,
        access: normalizeAccessInfo({
          ...(prev.access ?? {}),
          ...access,
        } as AccessInfo),
      }));
    } catch {
      /* mantém valores locais */
    }
  }, [enabled]);

  const mergeChatResult = useCallback((result: SendChatResult) => {
    const hasData = chatResultChangedData(result);
    const hasAccess = Boolean(result.access);
    if (!hasData && !hasAccess) return;
    setData((prev) => {
      let next = hasData ? mergeChatIntoDashboard(prev, result) : prev;
      if (hasAccess && result.access) {
        next = {
          ...next,
          access: normalizeAccessInfo({
            ...(next.access ?? {}),
            ...result.access,
          } as AccessInfo),
        };
      }
      return next;
    });
  }, []);

  const mergeWellnessJourney = useCallback((journey: WellnessJourney) => {
    setData((prev) => ({ ...prev, wellness_journey: journey }));
  }, []);

  const mergeDailyCare = useCallback((care: DailyCareInfo, journey?: WellnessJourney) => {
    setData((prev) => ({
      ...prev,
      daily_care: care,
      ...(journey ? { wellness_journey: journey } : {}),
    }));
  }, []);

  const setPersona = useCallback(async (avatarId: string, voiceId: string) => {
    const persona = accountPersona({ avatar_id: avatarId, voice_id: voiceId });
    const uid = resolveUserId(session, data.me?.user_id);
    setPersonaLocalOk(true);
    if (uid) {
      await markPersonaConfiguredLocal(uid);
      await saveLocalPersonaChoice(uid, persona);
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

  /** Só conta escolha guardada neste telemóvel (reinstalar = escolher de novo). */
  const personaGateOk = personaLocalOk;

  const mergeProfilePhone = useCallback((phone: string) => {
    const normalized = phone.trim();
    if (!normalized) return;
    const uid = resolveUserId(session, data.me?.user_id);
    setData((prev) => {
      if (prev.me) {
        return {
          ...prev,
          me: {
            ...prev.me,
            profile: {
              ...(prev.me.profile ?? {}),
              phone: normalized,
            },
          },
        };
      }
      if (!uid) return prev;
      return {
        ...prev,
        me: {
          user_id: uid,
          email: getSession()?.user?.email ?? null,
          profile: { phone: normalized },
          persona_configured: false,
          persona: { avatar_id: "f1", voice_id: "vf1" },
          access: { allowed: true, status: "ok" },
          stripe_checkout: {},
        },
      };
    });
  }, [data.me?.user_id, session]);

  const value = useMemo(
    () => ({
      data,
      loading,
      refreshing,
      error,
      refresh,
      mergeChatResult,
      refreshAccess,
      setPersona,
      mergeProfilePhone,
      mergeWellnessJourney,
      mergeDailyCare,
      personaGateOk,
    }),
    [
      data,
      loading,
      refreshing,
      error,
      refresh,
      mergeChatResult,
      refreshAccess,
      setPersona,
      mergeProfilePhone,
      mergeWellnessJourney,
      mergeDailyCare,
      personaGateOk,
    ]
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
