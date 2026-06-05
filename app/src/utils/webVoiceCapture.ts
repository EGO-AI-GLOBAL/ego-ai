/** Microfone no Safari iPhone — exige HTTPS (getUserMedia). */

import { getWebLocation } from "@/utils/webLocation";

export type WebMicMode = "recorder" | "needs-https" | "unsupported";

function isIosBrowser(): boolean {
  if (typeof navigator === "undefined") return false;
  return /iPad|iPhone|iPod/i.test(navigator.userAgent);
}

export function webMicMode(): WebMicMode {
  if (typeof window === "undefined") return "unsupported";

  const canRecord =
    typeof MediaRecorder !== "undefined" &&
    Boolean(window.isSecureContext) &&
    Boolean(navigator.mediaDevices?.getUserMedia);

  if (canRecord) return "recorder";

  if (isIosBrowser() && !window.isSecureContext) return "needs-https";

  if (typeof window !== "undefined" && !window.isSecureContext) {
    return "needs-https";
  }

  return "unsupported";
}

/** Instruções para mensagem de voz no iPhone Safari. */
export function iosSafariMicHelpMessage(): string {
  const lan =
    getWebLocation()?.hostname
      ? `http://${getWebLocation()!.hostname}:8081`
      : "http://192.168.x.x:8081";
  return [
    "Mensagem de voz no iPhone Safari exige HTTPS.",
    "",
    "Para chat em texto (link antigo na Wi‑Fi), use:",
    lan,
    "",
    "Inicie no PC: scripts\\start_expo_lan.ps1",
    "(ou: npx expo start --host lan --port 8081)",
    "",
    "Voz só com túnel: scripts\\start_expo_tunnel.ps1",
    "",
    "Por agora pode escrever a mensagem em texto.",
  ].join("\n");
}

export function webMicUnavailableMessage(): string {
  const mode = webMicMode();
  if (mode === "needs-https") {
    return iosSafariMicHelpMessage();
  }
  return "Microfone indisponível neste browser. Permita o microfone nas definições do Safari.";
}

export function mapGetUserMediaError(err: unknown): string {
  const name = err instanceof Error ? err.name : "";
  const msg = err instanceof Error ? err.message : String(err);
  if (name === "NotAllowedError" || /permission|denied|not allowed/i.test(msg)) {
    return "Permissão do microfone negada. Ajustes → Safari → Microfone → permitir para este site.";
  }
  if (name === "NotFoundError") {
    return "Nenhum microfone encontrado neste dispositivo.";
  }
  if (typeof window !== "undefined" && !window.isSecureContext) {
    return iosSafariMicHelpMessage();
  }
  return msg || webMicUnavailableMessage();
}
