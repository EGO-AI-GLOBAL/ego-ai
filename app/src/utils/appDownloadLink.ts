import { API_BASE_URL } from "@/constants/config";

const FALLBACK_GO = "https://ego-ai-production-a2c2.up.railway.app/go";

/** Link único: abre o app se instalado, senão Play ou TestFlight + cadastro. */
export function smartDownloadUrl(opts?: {
  ref?: string;
  next?: "agenda" | "signup" | "chat";
  campaign?: string;
}): string {
  const env = (process.env.EXPO_PUBLIC_DOWNLOAD_URL || "").trim().replace(/\/$/, "");
  const base = env || (API_BASE_URL ? API_BASE_URL.replace(/\/$/, "") : FALLBACK_GO.replace(/\/go$/, ""));
  const params = new URLSearchParams();
  params.set("utm_source", "egoai");
  params.set("utm_medium", "app");
  params.set("utm_campaign", opts?.campaign || "share");
  const ref = (opts?.ref || "").trim();
  if (ref) params.set("ref", ref);
  if (opts?.next) params.set("next", opts.next);
  const qs = params.toString();
  return `${base}/go${qs ? `?${qs}` : ""}`;
}

/** Convite de agenda — após cadastro cai na aba compartilhada (convites pendentes). */
export function inviteDownloadUrl(): string {
  return smartDownloadUrl({ next: "agenda", campaign: "invite" });
}
