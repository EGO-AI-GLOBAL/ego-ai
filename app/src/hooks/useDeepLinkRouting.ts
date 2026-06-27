import * as Linking from "expo-linking";
import { router, type Href } from "expo-router";
import { useEffect } from "react";
import { savePostLoginRoute } from "@/storage/postLoginRoute";
import { savePasswordRecoveryTokens } from "@/storage/passwordRecovery";
import { authTokensFromUrl } from "@/utils/authLinkParams";

function queryFromUrl(url: string): Record<string, string> {
  try {
    const parsed = Linking.parse(url);
    const q = parsed.queryParams ?? {};
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(q)) {
      if (typeof v === "string" && v.trim()) out[k] = v.trim();
      else if (Array.isArray(v) && typeof v[0] === "string") out[k] = v[0].trim();
    }
    return out;
  } catch {
    return {};
  }
}

async function maybeStoreRecoveryTokens(url: string): Promise<boolean> {
  const tokens = authTokensFromUrl(url);
  if (!tokens.access_token || !tokens.refresh_token) return false;
  if (tokens.type && tokens.type !== "recovery") return false;
  await savePasswordRecoveryTokens({
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
  });
  return true;
}

function routeFromDeepLink(url: string): Href | null {
  const parsed = Linking.parse(url);
  const path = (parsed.path || "").replace(/^\/+/, "").toLowerCase();
  const q = queryFromUrl(url);
  const ref = q.ref || "";
  const next = (q.next || "").toLowerCase();

  if (path === "reset-password" || path === "auth/reset-password") {
    return "/reset-password" as Href;
  }
  if (path === "signup" || path === "cadastro" || path === "register") {
    if (next === "agenda") void savePostLoginRoute("/(main)/agenda");
    const qs = ref ? `?ref=${encodeURIComponent(ref)}` : "";
    return (`/signup${qs}` as Href);
  }
  if (path === "agenda" || path === "convite" || path === "invite") {
    void savePostLoginRoute("/(main)/agenda");
    return "/signup" as Href;
  }
  if (path === "login") {
    return "/login" as Href;
  }
  return null;
}

async function handleUrl(url: string | null) {
  if (!url) return;
  const lower = url.toLowerCase();
  const isEgo =
    lower.includes("egoai://") ||
    lower.includes("egoai/") ||
    lower.includes("/auth/reset-password");
  if (!isEgo && !lower.includes("access_token=")) return;

  const recovered = await maybeStoreRecoveryTokens(url);
  if (recovered) {
    router.replace("/reset-password" as Href);
    return;
  }

  if (!lower.includes("egoai")) return;
  const href = routeFromDeepLink(url);
  if (href) {
    router.replace(href);
  }
}

/** egoai://signup, egoai://reset-password — cadastro, recuperação de senha. */
export function useDeepLinkRouting() {
  useEffect(() => {
    void Linking.getInitialURL().then((url) => handleUrl(url));
    const sub = Linking.addEventListener("url", (ev) => {
      void handleUrl(ev.url);
    });
    return () => sub.remove();
  }, []);
}
