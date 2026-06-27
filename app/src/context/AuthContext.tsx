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
  setOnAuthFailure,
  setSessionPersistHandler,
  signup as apiSignup,
} from "@/api/client";
import type { AuthSession } from "@/api/types";
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
import { sessionNeedsRefresh } from "@/storage/sessionRefresh";
import { preparePlayIntegrity } from "@/security/playIntegrity";

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
    async (current: AuthSession, opts?: { force?: boolean }) => {
      const refreshTok = current.refresh_token?.trim();
      if (!refreshTok) return current;
      if (!opts?.force && !sessionNeedsRefresh(current)) return current;
      if (refreshInFlight.current) return current;
      refreshInFlight.current = true;
      try {
        const next = await refreshSessionToken(refreshTok, current);
        await persist(next);
        return next;
      } catch {
        /* rede ou refresh inválido — mantém sessão; interceptor trata 401 */
        return current;
      } finally {
        refreshInFlight.current = false;
      }
    },
    [persist]
  );

  useEffect(() => {
    (async () => {
      try {
        const raw = await getSecureItem(STORAGE_KEY);
        if (raw) {
          if (await shouldClearSessionForAppUpdate()) {
            await deleteSecureItem(STORAGE_KEY);
            await clearAuthAppVersion();
          } else {
            const parsed = JSON.parse(raw) as AuthSession;
            if (parsed?.access_token) {
              const next = await refreshSessionIfNeeded(parsed);
              if (next === parsed) {
                await persist(parsed);
              }
              void preparePlayIntegrity();
            }
          }
        }
      } catch {
        /* ignore */
      } finally {
        setLoading(false);
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
      await persist(s);
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
        await persist(s);
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
