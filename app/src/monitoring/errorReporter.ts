import Constants from "expo-constants";
import { Platform } from "react-native";
import { API_V1 } from "@/constants/config";
import { getSession } from "@/api/client";

type ReportPayload = {
  message: string;
  stack?: string;
  route?: string;
  level?: "error" | "warning";
  meta?: Record<string, unknown>;
};

let sentryModule: typeof import("@sentry/react-native") | null = null;

export function initMonitoring(): void {
  const dsn = (process.env.EXPO_PUBLIC_SENTRY_DSN || "").trim();
  if (!dsn) {
    return;
  }
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    sentryModule = require("@sentry/react-native");
    sentryModule.init({
      dsn,
      debug: __DEV__,
      enabled: !__DEV__ || process.env.EXPO_PUBLIC_SENTRY_DEV === "1",
      tracesSampleRate: 0.15,
      environment:
        process.env.EXPO_PUBLIC_SENTRY_ENV ||
        (process.env.EAS_BUILD_PROFILE as string) ||
        (__DEV__ ? "development" : "production"),
      release: `ego-ai@${Constants.expoConfig?.version || "?"}`,
    });
  } catch {
    sentryModule = null;
  }
}

export function captureException(error: unknown, context?: Record<string, unknown>): void {
  if (sentryModule && error instanceof Error) {
    sentryModule.captureException(error, { extra: context });
  }
  const msg = error instanceof Error ? error.message : String(error);
  const stack = error instanceof Error ? error.stack : undefined;
  void reportClientError({
    message: msg,
    stack,
    route: (context?.route as string) || "",
    meta: context,
  });
}

export async function reportClientError(payload: ReportPayload): Promise<void> {
  const session = getSession();
  const body = {
    message: payload.message.slice(0, 2000),
    stack: (payload.stack || "").slice(0, 8000),
    route: payload.route || "",
    level: payload.level || "error",
    platform: Platform.OS,
    app_version: Constants.expoConfig?.version || "",
    user_id: session?.user?.id || null,
    meta: payload.meta || {},
  };

  try {
    const base = API_V1.endsWith("/") ? API_V1 : `${API_V1}/`;
    await fetch(`${base}report-error`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    /* offline — Sentry ainda pode ter capturado */
  }
}

export function reportApiFailure(
  url: string | undefined,
  status: number | undefined,
  message: string
): void {
  if (status && status < 500) {
    return;
  }
  captureException(new Error(message), {
    route: url || "api",
    status,
    kind: "api",
  });
}
