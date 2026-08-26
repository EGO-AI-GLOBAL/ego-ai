import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AppState, type AppStateStatus } from "react-native";
import {
  STORAGE_KEY,
  getSession,
  login as apiLogin,
  logoutApi,
  refreshSessionToken,
  saveLastLoginEmail,
  setSession,
  setAuthHydrationComplete,
  setOnAuthFailure,
  setSessionPersistHandler,
  signup as apiSignup,
} from "@/api/client";
import type { AuthSession } from "@/api/types";
import { saveLocalProfilePhone } from "@/storage/profilePhoneLocal";
import {
  deleteSecureItem,
  getSecureItem,
  saveSecureItem,
} from "@/storage/sessionStorage";
import {
  clearAuthAppVersion,
  saveAuthAppVersion,
  shouldClearSessionForAppUpdate,
} from "@/storage/authAppVersion";
import {
  clearSecureSessionIfFreshInstall,
  consumeSecureWipeIfNeeded,
  ensureInstallMarkers,
  runFreshInstallMigrations,
} from "@/storage/freshInstallGuard";
import { preloadDashboardCache } from "@/storage/dashboardCache";
import { sessionNeedsRefresh } from "@/storage/sessionRefresh";
import { preparePlayIntegrity } from "@/security/playIntegrity";
import { trackLogin, trackSignUp } from "@/analytics/egoAnalytics";

type AuthContextValue = {
  session: AuthSession | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (
    email: string,
    password: string,
    fullName?: string,
    phone?: string,
    referralCode?: string
  ) => Promise<{ needsEmailConfirm: boolean }>;
  applySession: (session: AuthSession) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setLocalSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshInFlight = useRef(false);

  const persist = useCallback(async (s: AuthSession | null) => {
    setSession(s);
    setLocalSession(s);
    if (s) {
      await saveSecureItem(STORAGE_KEY, JSON.stringify(s));
      await saveAuthAppVersion();
      await ensureInstallMarkers();
    } else {
      await deleteSecureItem(STORAGE_KEY);
      await clearAuthAppVersion();
    }
  }, []);

  useEffect(() => {
    setSession(session);
  }, [session]);

  useEffect(() => {
    setSessionPersistHandler(async (s) => {
      await persist(s);
    });
    setOnAuthFailure(() => {
      void persist(null);
    });
    return () => {
      setSessionPersistHandler(null);
      setOnAuthFailure(null);
    };
  }, [persist]);

  const refreshSessionIfNeeded = useCallback(
    async (current: AuthSession, opts?: { force?: boolean }): Promise<AuthSession | null> => {
      const refreshTok = current.refresh_token?.trim();
      if (!refreshTok) return current;
      if (!opts?.force && !sessionNeedsRefresh(current)) return current;
      // Não retornar cedo sem esperar: outro caminho pode estar a renovar.
      // refreshSessionToken deduplica; esperar evita 401 com token antigo.
      if (refreshInFlight.current) {
        try {
          const joined = await refreshSessionToken(refreshTok, current);
          const mem = getSession();
          return mem?.access_token ? mem : joined;
        } catch {
          const mem = getSession();
          if (mem?.refresh_token?.trim() && mem.refresh_token.trim() !== refreshTok) {
            return mem;
          }
          return getSession() ?? current;
        }
      }
      refreshInFlight.current = true;
      try {
        const next = await refreshSessionToken(refreshTok, current);
        const mem = getSession();
        const toSave = mem?.access_token ? mem : next;
        await persist(toSave);
        return toSave;
      } catch (e) {
        const rotated = getSession();
        if (
          rotated?.access_token?.trim() &&
          rotated.refresh_token?.trim() &&
          rotated.refresh_token.trim() !== refreshTok
        ) {
          await persist(rotated);
          return rotated;
        }
        const msg = (e instanceof Error ? e.message : String(e || "")).toLowerCase();
        const hardDead =
          msg.includes("sessão expirada") ||
          msg.includes("sessao expirada") ||
          msg.includes("entre de novo") ||
          msg.includes("already used") ||
          msg.includes("invalid refresh");
        if (hardDead) {
          // Só limpa se ninguém gravou tokens novos na corrida.
          const still = getSession();
          if (still?.refresh_token?.trim() && still.refresh_token.trim() !== refreshTok) {
            await persist(still);
            return still;
          }
          setSession(null);
          setLocalSession(null);
          await deleteSecureItem(STORAGE_KEY).catch(() => undefined);
          return null;
        }
        /* rede transitória — mantém sessão; interceptor trata 401 */
        return getSession() ?? current;
      } finally {
        refreshInFlight.current = false;
      }
    },
    [persist]
  );

  useEffect(() => {
    (async () => {
      let hydrated = false;
      try {
        await Promise.all([
          clearSecureSessionIfFreshInstall(),
          runFreshInstallMigrations(),
        ]);
        const raw = await getSecureItem(STORAGE_KEY);
        if (raw) {
          if (await shouldClearSessionForAppUpdate()) {
            await deleteSecureItem(STORAGE_KEY);
            await clearAuthAppVersion();
          } else {
            const parsed = JSON.parse(raw) as AuthSession;
            if (parsed?.access_token) {
              setSession(parsed);
              setLocalSession(parsed);
              hydrated = true;
              setAuthHydrationComplete(true);
              setLoading(false);

              const uid = parsed.user?.id?.trim();
              if (uid) {
                void consumeSecureWipeIfNeeded(uid);
                void preloadDashboardCache(uid);
              }
              void (async () => {
                const next = await refreshSessionIfNeeded(parsed);
                if (next == null) {
                  /* refresh morto */
                } else {
                  await persist(next);
                }
                void preparePlayIntegrity();
              })();
            }
          }
        }
      } catch {
        /* ignore */
      } finally {
        if (!hydrated) {
          setAuthHydrationComplete(true);
          setLoading(false);
        }
      }
    })();
  }, [persist, refreshSessionIfNeeded]);

  useEffect(() => {
    const sub = AppState.addEventListener("change", (state: AppStateStatus) => {
      if (state !== "active") return;
      const current = getSession();
      if (!current?.access_token) return;
      void refreshSessionIfNeeded(current);
    });
    return () => sub.remove();
  }, [refreshSessionIfNeeded]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const s = await apiLogin(email, password);
      if (!s?.access_token) {
        throw new Error("Resposta de login sem token.");
      }
      await saveLastLoginEmail(email.trim());
      const uid = s.user?.id?.trim();
      if (uid) await consumeSecureWipeIfNeeded(uid);
      await persist(s);
      trackLogin("email");
      void preparePlayIntegrity();
    },
    [persist]
  );

  const signUp = useCallback(
    async (
      email: string,
      password: string,
      fullName?: string,
      phone?: string,
      referralCode?: string
    ) => {
      const s = await apiSignup(email, password, fullName, phone, referralCode);
      if (s?.access_token) {
        const uid = s.user?.id?.trim();
        const ph = phone?.trim();
        await persist(s);
        if (uid && ph) {
          await saveLocalProfilePhone(uid, ph);
        }
        trackSignUp("email");
        void preparePlayIntegrity();
        return { needsEmailConfirm: false };
      }
      return { needsEmailConfirm: true };
    },
    [persist]
  );

  const signOut = useCallback(async () => {
    if (getSession()) {
      await logoutApi();
    }
    await persist(null);
  }, [persist]);

  const applySession = useCallback(
    async (s: AuthSession) => {
      if (!s?.access_token) {
        throw new Error("Sessão inválida.");
      }
      const uid = s.user?.id?.trim();
      if (uid) await consumeSecureWipeIfNeeded(uid);
      await persist(s);
      void preparePlayIntegrity();
    },
    [persist]
  );

  const value = useMemo(
    () => ({ session, loading, signIn, signUp, applySession, signOut }),
    [session, loading, signIn, signUp, applySession, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fora do AuthProvider");
  return ctx;
}
