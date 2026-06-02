import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  STORAGE_KEY,
  getSession,
  login as apiLogin,
  logoutApi,
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
import { preparePlayIntegrity } from "@/security/playIntegrity";

type AuthContextValue = {
  session: AuthSession | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (
    email: string,
    password: string,
    fullName?: string,
    referralCode?: string
  ) => Promise<{ needsEmailConfirm: boolean }>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setLocalSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);

  const persist = useCallback(async (s: AuthSession | null) => {
    setSession(s);
    setLocalSession(s);
    if (s) {
      await saveSecureItem(STORAGE_KEY, JSON.stringify(s));
    } else {
      await deleteSecureItem(STORAGE_KEY);
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

  useEffect(() => {
    (async () => {
      try {
        const raw = await getSecureItem(STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as AuthSession;
          if (parsed?.access_token) {
            await persist(parsed);
            void preparePlayIntegrity();
          }
        }
      } catch {
        /* ignore */
      } finally {
        setLoading(false);
      }
    })();
  }, [persist]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const s = await apiLogin(email, password);
      if (!s?.access_token) {
        throw new Error("Resposta de login sem token.");
      }
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
      referralCode?: string
    ) => {
      const s = await apiSignup(email, password, fullName, referralCode);
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

  const value = useMemo(
    () => ({ session, loading, signIn, signUp, signOut }),
    [session, loading, signIn, signUp, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fora do AuthProvider");
  return ctx;
}
