import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  fetchAccessInfo,
  fetchDashboard,
  getSession,
  refreshSessionToken,
  setSession,
} from "@/api/client";
import { normalizeAccessInfo } from "@/constants/planLimits";
import type { AccessInfo } from "@/api/types";
import { loadLocalChatHistory } from "@/storage/chatHistoryLocal";
import { estimateTokenDelta } from "@/utils/usageStats";
import { resolveUserId } from "@/utils/resolveUserId";
import type { DashboardData, SendChatResult, WellnessJourney, DailyCareInfo, PausaEgoInfo } from "@/api/types";
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
import { cacheFunnelCheckedToday } from "@/notifications/funnelEngagementReminders";
import {
  cancelMoodMonsterNotifications,
  syncMoodMonsterNotifications,
} from "@/utils/moodMonsterNotifications";
import {
  cancelPausaLocalNotifications,
  syncPausaLocalNotifications,
} from "@/utils/pausaLocalNotifications";
import { cancelEgoDeBolsoCareNotification } from "@/utils/egoDeBolsoNotifications";
import { syncMoodGardenHomeWidget } from "@/widgets/syncMoodGardenHomeWidget";
import { saveStreakCache } from "@/storage/streakCache";
import {
  loadDashboardCache,
  saveDashboardCache,
} from "@/storage/dashboardCache";
import {
  getLocalPersonaChoice,
  isPersonaConfiguredLocal,
  markPersonaConfiguredLocal,
  saveLocalPersonaChoice,
} from "@/storage/personaPrefs";
import {
  clearSignupPhoneCache,
  getLocalProfilePhone,
} from "@/storage/profilePhoneLocal";
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
  pausa_ego: undefined,
  daily_care: undefined,
  shared_calendars: [],
  pending_calendar_invites: [],
  messages: [],
};

type RefreshOptions = {
  /** Evita expo-notifications após chat (agenda compartilhada costuma crashar no Android). */
  skipNotifications?: boolean;
  /** Carga inicial: adia syncs pesados para o chat abrir mais rápido. */
  deferNotifications?: boolean;
  /** Abertura do app: timeout curto + cache local se rede lenta. */
  initialOpen?: boolean;
  /** Já pintámos cache — timeout não bloqueia ecrã. */
  cacheHit?: boolean;
};

const DEFER_BACKGROUND_SYNC_MS = 2000;
const BOOTSTRAP_OPEN_TIMEOUT_MS = 2000;
const TOKEN_ESTIMATE_MSG_CAP = 50;
const OPEN_TIMEOUT = "__ego_open_timeout__";

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
  mergePausaEgo: (pausa: PausaEgoInfo) => void;
  mergeDailyCare: (care: DailyCareInfo, journey?: WellnessJourney) => void;
  /** true se o servidor ou o telemóvel já registou escolha de assistente */
  personaGateOk: boolean;
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

async function mergeStoredProfilePhone(
  dashboard: DashboardData,
  uid: string | null,
  localPhPreload?: string | null
): Promise<DashboardData> {
  if (!uid) return dashboard;
  const localPh =
    localPhPreload !== undefined
      ? localPhPreload
      : await getLocalProfilePhone(uid).catch(() => null);
  if (!localPh?.trim() || profilePhoneFromMe(dashboard.me)) {
    return dashboard;
  }
  const phone = localPh.trim();
  if (dashboard.me) {
    return {
      ...dashboard,
      me: {
        ...dashboard.me,
        profile_phone: phone,
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
      profile_phone: phone,
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
  const sessionRef = useRef(session);
  sessionRef.current = session;
  const accessTok = session?.access_token?.trim() || "";
  const enabled = Boolean(accessTok);
  const [data, setData] = useState<DashboardData>(empty);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [personaLocalOk, setPersonaLocalOk] = useState(false);
  /** Evita sync de notificações logo após convite/evento no chat (crash Android). */
  const notificationCooldownUntilRef = useRef(0);
  const syncRetryAtRef = useRef(0);

  const applyDashboard = useCallback(
    async (dashboardIn: DashboardData, options?: RefreshOptions) => {
      let dashboard = dashboardIn;
      const uid = resolveUserId(getSession(), dashboard.me?.user_id);
      const [localChoice, msgs, localPh] = await Promise.all([
        uid ? getLocalPersonaChoice(uid) : Promise.resolve(null),
        uid && dashboardIn.access
          ? loadLocalChatHistory(uid).catch(() => [] as Awaited<ReturnType<typeof loadLocalChatHistory>>)
          : Promise.resolve([] as Awaited<ReturnType<typeof loadLocalChatHistory>>),
        uid ? getLocalProfilePhone(uid).catch(() => null) : Promise.resolve(null),
      ]);
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
        const recent =
          msgs.length > TOKEN_ESTIMATE_MSG_CAP
            ? msgs.slice(-TOKEN_ESTIMATE_MSG_CAP)
            : msgs;
        let est = 0;
        for (let i = 0; i < recent.length; i++) {
          const m = recent[i];
          const prev = i > 0 ? recent[i - 1] : null;
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
      dashboard = await mergeStoredProfilePhone(dashboard, uid, localPh);
      if (uid && profilePhoneFromMe(dashboard.me)) {
        void clearSignupPhoneCache(uid);
      }
      setData(dashboard);
      if (uid) {
        void saveDashboardCache(uid, dashboard);
      }
      void saveStreakCache(dashboard.streak);
      void cacheFunnelCheckedToday(Boolean(dashboard.daily_care?.checked_today));
      setPersonaLocalOk(Boolean(uid && localChoice));
      if (dashboard.me || (dashboard.shared_calendars?.length ?? 0) > 0) {
        setError(null);
      }
      if (!options?.skipNotifications) {
        const skipForCooldown = Date.now() < notificationCooldownUntilRef.current;
        const runBackgroundSyncs = () => {
          if (Date.now() < notificationCooldownUntilRef.current) return;
          void syncReminderLocalNotifications(dashboard.reminders).catch(() => {});
          const shared = dashboard.shared_calendars ?? [];
          void registerExpoPushToken();
          void notifyNewSharedEventsFromOthers(shared, uid).catch(() => {});
          void syncSharedCalendarLocalNotifications(shared).catch(() => {});
          void syncDailyCheckInNotification().catch(() => {});
          void cancelEgoDeBolsoCareNotification();
          void syncMoodMonsterNotifications(dashboard.daily_care).catch(() => {});
          void syncPausaLocalNotifications(dashboard.pausa_ego).catch(() => {});
          void syncMoodGardenHomeWidget(dashboard.daily_care).catch(() => {});
        };
        if (skipForCooldown) {
          /* cooldown ativo — não dispara sync imediato */
        } else if (options?.deferNotifications) {
          setTimeout(runBackgroundSyncs, DEFER_BACKGROUND_SYNC_MS);
        } else {
          runBackgroundSyncs();
        }
      }
    },
    []
  );

  const load = useCallback(async (options?: RefreshOptions) => {
    if (!enabled) {
      setData(empty);
      setLoading(false);
      setError(null);
      setPersonaLocalOk(false);
      void cancelAllReminderLocalNotifications();
      void cancelMoodMonsterNotifications();
      void cancelPausaLocalNotifications();
      return;
    }
    // Corrida ao abrir: React tem sessão, memória do axios ainda vazia —
    // semear e esperar (80ms era curto demais e gerava falso «expirada»).
    const authSession = sessionRef.current;
    if (authSession?.access_token?.trim()) {
      if (!getSession()?.access_token?.trim()) {
        setSession(authSession);
      }
    } else {
      for (let i = 0; i < 5 && !getSession()?.access_token?.trim(); i++) {
        const s = sessionRef.current;
        if (s?.access_token?.trim()) setSession(s);
        await new Promise((r) => setTimeout(r, 50));
      }
    }
    if (!getSession()?.access_token?.trim()) {
      if (!sessionRef.current?.access_token?.trim()) {
        setError("Sessão expirada. Saia e entre novamente.");
      }
      return;
    }
    setError(null);
    const skipNotifications =
      options?.skipNotifications || Date.now() < notificationCooldownUntilRef.current;

    const looksAuthMsg = (msg: string) =>
      /token ausente|sessão inválida|sessão expirada|não foi possível renovar|refresh_token/i.test(
        msg
      );

    const tryLoadOnce = async () => {
      let dashboard: DashboardData;
      if (options?.initialOpen) {
        const fetchPromise = fetchDashboard();
        const timed = Promise.race([
          fetchPromise,
          new Promise<never>((_, reject) => {
            setTimeout(() => reject(new Error(OPEN_TIMEOUT)), BOOTSTRAP_OPEN_TIMEOUT_MS);
          }),
        ]);
        try {
          dashboard = await timed;
        } catch (e) {
          const msg = e instanceof Error ? e.message : "";
          if (msg === OPEN_TIMEOUT && options?.cacheHit) {
            const now = Date.now();
            if (now - syncRetryAtRef.current > 15_000) {
              syncRetryAtRef.current = now;
              setTimeout(() => {
                void load({ skipNotifications: true, deferNotifications: true });
              }, 2500);
            }
            return;
          }
          throw e;
        }
      } else {
        dashboard = await fetchDashboard();
      }
      await applyDashboard(dashboard, {
        ...options,
        skipNotifications,
      });
    };

    /** Após update iOS+Android o refresh pode falhar em 503 transitório — tenta de novo. */
    const recoverSessionAndLoad = async () => {
      const cur = getSession() || sessionRef.current;
      const refreshTok = cur?.refresh_token?.trim();
      if (!refreshTok) throw new Error("Sessão expirada. Saia e entre novamente.");
      const next = await refreshSessionToken(refreshTok, cur);
      setSession(next);
      await tryLoadOnce();
    };

    try {
      await tryLoadOnce();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro ao carregar dados.";
      const looksAuth = looksAuthMsg(msg);
      let recovered = false;
      if (looksAuth) {
        for (let attempt = 0; attempt < 3 && !recovered; attempt++) {
          if (attempt > 0) {
            await new Promise((r) => setTimeout(r, 500 * attempt));
          }
          try {
            await recoverSessionAndLoad();
            recovered = true;
          } catch {
            /* tenta de novo */
          }
        }
      }
      if (recovered) return;

      const uid = resolveUserId(getSession() || sessionRef.current);
      if (uid) {
        const local = await getLocalPersonaChoice(uid);
        if (local) {
          const persona = accountPersona(local);
          setData((prev) => ({
            ...prev,
            me: prev.me ?? {
              user_id: uid,
              email: (getSession() || sessionRef.current)?.user?.email ?? null,
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
      if (looksAuth) {
        const stillRefresh = (getSession() || sessionRef.current)?.refresh_token?.trim();
        if (stillRefresh) {
          setError(
            "Não foi possível sincronizar. Puxe para atualizar. Se continuar, saia e entre de novo."
          );
          const now = Date.now();
          if (now - syncRetryAtRef.current > 15_000) {
            syncRetryAtRef.current = now;
            setTimeout(() => {
              void load({ skipNotifications: true });
            }, 2500);
          }
        } else {
          setError("Sessão expirada. Saia e entre novamente.");
        }
      } else if (!options?.cacheHit && (!uid || !(await isPersonaConfiguredLocal(uid)))) {
        setError(msg);
      }
    }
  }, [enabled, accessTok, applyDashboard]);

  useEffect(() => {
    if (!enabled) {
      setData(empty);
      setLoading(false);
      setError(null);
      setPersonaLocalOk(false);
      void cancelAllReminderLocalNotifications();
      void cancelMoodMonsterNotifications();
      void cancelPausaLocalNotifications();
      return;
    }

    let cancelled = false;
    const uid =
      session?.user?.id?.trim() || "";

    void (async () => {
      let cacheHit = false;
      if (uid) {
        const cached = await loadDashboardCache(uid);
        if (cached && !cancelled) {
          cacheHit = Boolean(cached.daily_care?.question || cached.me?.user_id);
          setData((prev) => ({ ...prev, ...cached }));
          if (cached.me?.persona_configured) {
            setPersonaLocalOk(true);
          } else {
            const local = await getLocalPersonaChoice(uid);
            if (local) setPersonaLocalOk(true);
          }
          if (cacheHit) {
            setLoading(false);
          }
        }
      }

      if (!cacheHit && !cancelled) {
        setLoading(true);
      }

      await load({
        deferNotifications: true,
        initialOpen: true,
        cacheHit,
      });
      if (!cancelled) {
        setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [enabled, load, session?.user?.id]);

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
    if (
      result.shared_members_saved?.length ||
      result.shared_events_saved?.length ||
      result.shared_calendars_saved?.length
    ) {
      notificationCooldownUntilRef.current = Date.now() + 5000;
    }
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

  const mergePausaEgo = useCallback((pausa: PausaEgoInfo) => {
    setData((prev) => ({ ...prev, pausa_ego: pausa }));
    void syncPausaLocalNotifications(pausa).catch(() => {});
  }, []);

  const mergeDailyCare = useCallback((care: DailyCareInfo, journey?: WellnessJourney) => {
    setData((prev) => {
      const next = {
        ...prev,
        daily_care: care,
        ...(journey ? { wellness_journey: journey } : {}),
      };
      const uid = resolveUserId(session, next.me?.user_id);
      if (uid) {
        void saveDashboardCache(uid, next);
      }
      return next;
    });
    void syncMoodMonsterNotifications(care).catch(() => {});
    void syncMoodGardenHomeWidget(care).catch(() => {});
    void cacheFunnelCheckedToday(Boolean(care.checked_today));
  }, [session]);

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
            profile_phone: normalized,
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
          profile_phone: normalized,
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
      mergePausaEgo,
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
      mergePausaEgo,
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
