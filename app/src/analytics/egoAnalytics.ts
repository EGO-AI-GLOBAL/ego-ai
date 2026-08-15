/**
 * Firebase Analytics (GA4) — project EGO (com.egoai.app).
 * Sem google-services / Firebase nativo → no-op seguro (não crasha Expo Go).
 *
 * Eventos mínimos: first_open, login, sign_up, session_or_checkin_completed,
 * paywall_view, trial_start, purchase, subscribe.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";

const FIRST_OPEN_KEY = "ego_analytics_first_open_v1";

type EventParams = Record<string, string | number | boolean | null | undefined>;

type AnalyticsModule = {
  logEvent: (name: string, params?: EventParams) => Promise<void>;
  setAnalyticsCollectionEnabled?: (enabled: boolean) => Promise<void>;
};

let analyticsPromise: Promise<AnalyticsModule | null> | null = null;
let firstOpenDone = false;

async function getAnalytics(): Promise<AnalyticsModule | null> {
  if (Platform.OS === "web") return null;
  if (!analyticsPromise) {
    analyticsPromise = (async () => {
      try {
        const mod = await import("@react-native-firebase/analytics");
        const analytics = mod.default;
        const instance = typeof analytics === "function" ? analytics() : analytics;
        if (instance?.setAnalyticsCollectionEnabled) {
          await instance.setAnalyticsCollectionEnabled(true);
        }
        return {
          logEvent: async (name, params) => {
            const clean: Record<string, string | number> = {};
            if (params) {
              for (const [k, v] of Object.entries(params)) {
                if (v === undefined || v === null) continue;
                clean[k] = typeof v === "boolean" ? (v ? 1 : 0) : v;
              }
            }
            await instance.logEvent(name, clean);
          },
        };
      } catch {
        return null;
      }
    })();
  }
  return analyticsPromise;
}

export async function logEgoEvent(
  name: string,
  params?: EventParams
): Promise<void> {
  try {
    const analytics = await getAnalytics();
    if (analytics) {
      await analytics.logEvent(name, params);
      return;
    }
    if (__DEV__) {
      // eslint-disable-next-line no-console
      console.log("[egoAnalytics:noop]", name, params || {});
    }
  } catch (err) {
    if (__DEV__) {
      // eslint-disable-next-line no-console
      console.warn("[egoAnalytics]", name, err);
    }
  }
}

/** first_open uma vez por instalação (além do automático do SDK quando Firebase existir). */
export async function trackFirstOpenIfNeeded(): Promise<void> {
  if (firstOpenDone) return;
  firstOpenDone = true;
  try {
    const seen = await AsyncStorage.getItem(FIRST_OPEN_KEY);
    if (seen) return;
    await AsyncStorage.setItem(FIRST_OPEN_KEY, "1");
    await logEgoEvent("first_open", { platform: Platform.OS });
  } catch {
    /* ignore */
  }
}

export function trackLogin(method = "email"): void {
  void logEgoEvent("login", { method });
}

export function trackSignUp(method = "email"): void {
  void logEgoEvent("sign_up", { method });
}

/** Check-in Monstrinhos, PAUSA, etc. */
export function trackSessionOrCheckinCompleted(
  kind: "checkin" | "pausa" | "chat" | "night_dump",
  extra?: EventParams
): void {
  void logEgoEvent("session_or_checkin_completed", { kind, ...extra });
}

export function trackPaywallView(source = "plans"): void {
  void logEgoEvent("paywall_view", { source });
}

export function trackTrialStart(plan = "premium"): void {
  void logEgoEvent("trial_start", { plan });
}

export function trackPurchase(params?: EventParams): void {
  void logEgoEvent("purchase", params);
}

export function trackSubscribe(params?: EventParams): void {
  void logEgoEvent("subscribe", { ...params });
  void logEgoEvent("purchase", { ...params, type: "subscribe" });
}

export function trackRewardedOptIn(action: "offer_shown" | "started" | "earned" | "dismissed"): void {
  void logEgoEvent("rewarded_ad", { action });
}

export function trackInterstitial(action: "shown" | "skipped_cooldown" | "no_fill"): void {
  void logEgoEvent("interstitial_ad", { action });
}
