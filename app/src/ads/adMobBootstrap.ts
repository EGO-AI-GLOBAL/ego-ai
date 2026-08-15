import { Platform } from "react-native";
import { useEffect, useRef } from "react";

let initPromise: Promise<void> | null = null;

/** Inicializa AdMob uma vez (no-op em web / Expo Go sem módulo nativo). */
export function ensureAdMobInitialized(): Promise<void> {
  if (Platform.OS === "web") return Promise.resolve();
  if (!initPromise) {
    initPromise = (async () => {
      try {
        const mod = await import("react-native-google-mobile-ads");
        await mod.default().initialize();
      } catch (err) {
        if (__DEV__) {
          // eslint-disable-next-line no-console
          console.warn("[AdMob] initialize falhou:", err);
        }
      }
    })();
  }
  return initPromise;
}

export function useAdMobBootstrap(enabled: boolean) {
  const started = useRef(false);
  useEffect(() => {
    if (!enabled || started.current) return;
    started.current = true;
    void ensureAdMobInitialized();
  }, [enabled]);
}
