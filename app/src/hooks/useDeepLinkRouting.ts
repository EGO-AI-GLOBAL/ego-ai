import * as Linking from "expo-linking";
import { router, type Href } from "expo-router";
import { useEffect } from "react";
import { savePostLoginRoute } from "@/storage/postLoginRoute";

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

function routeFromDeepLink(url: string): Href | null {
  const parsed = Linking.parse(url);
  const path = (parsed.path || "").replace(/^\/+/, "").toLowerCase();
  const q = queryFromUrl(url);
  const ref = q.ref || "";
  const next = (q.next || "").toLowerCase();

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
  if (!url || !url.includes("egoai")) return;
  const href = routeFromDeepLink(url);
  if (href) {
    router.replace(href);
  }
}

/** egoai://signup, egoai://cadastro?next=agenda — abre cadastro ou agenda após login. */
export function useDeepLinkRouting() {
  useEffect(() => {
    void Linking.getInitialURL().then((url) => handleUrl(url));
    const sub = Linking.addEventListener("url", (ev) => {
      void handleUrl(ev.url);
    });
    return () => sub.remove();
  }, []);
}
