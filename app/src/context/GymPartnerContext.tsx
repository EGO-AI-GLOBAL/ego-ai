import AsyncStorage from "@react-native-async-storage/async-storage";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  fetchMyGymPartner,
  type GymPartnerPublic,
} from "@/api/client";
import { useAuth } from "@/context/AuthContext";

const GYM_CODE_KEY = "ego_gym_code";

type GymPartnerContextValue = {
  partner: GymPartnerPublic | null;
  gymCode: string | null;
  ready: boolean;
  /** Aluno com academia → pagar só via Stripe Connect (esconder IAP). */
  usesGymStripe: boolean;
  refreshGymPartner: () => Promise<void>;
};

const GymPartnerContext = createContext<GymPartnerContextValue | null>(null);

export function GymPartnerProvider({ children }: { children: ReactNode }) {
  const { session, loading: authLoading } = useAuth();
  const [partner, setPartner] = useState<GymPartnerPublic | null>(null);
  const [gymCode, setGymCode] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const refreshGymPartner = useCallback(async () => {
    if (!session?.access_token) {
      setPartner(null);
      setGymCode(null);
      setReady(true);
      return;
    }
    const cached = await AsyncStorage.getItem(GYM_CODE_KEY);
    if (cached) setGymCode(cached);
    setReady(true);
    try {
      const row = await fetchMyGymPartner();
      setPartner(row.partner);
      setGymCode(row.gym_code);
      if (row.gym_code) await AsyncStorage.setItem(GYM_CODE_KEY, row.gym_code);
      else await AsyncStorage.removeItem(GYM_CODE_KEY);
    } catch {
      if (cached) setGymCode(cached);
    }
  }, [session?.access_token]);

  useEffect(() => {
    if (authLoading) return;
    void refreshGymPartner();
  }, [authLoading, refreshGymPartner, session?.user?.id]);

  const value = useMemo(
    () => ({
      partner,
      gymCode,
      ready,
      usesGymStripe: Boolean((gymCode || "").trim()),
      refreshGymPartner,
    }),
    [partner, gymCode, ready, refreshGymPartner]
  );

  return (
    <GymPartnerContext.Provider value={value}>{children}</GymPartnerContext.Provider>
  );
}

export function useGymPartner(): GymPartnerContextValue {
  const ctx = useContext(GymPartnerContext);
  if (!ctx) throw new Error("useGymPartner fora do GymPartnerProvider");
  return ctx;
}
