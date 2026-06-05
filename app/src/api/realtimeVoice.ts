import type { ChatHistoryPayload, SendChatResult } from "@/api/types";
import { api } from "@/api/client";

export type RealtimeClientSecretPayload = {
  client_secret: string;
  ws_url: string;
  model: string;
  voice: string;
  expires_at?: number;
};

let statusCache: boolean | null = null;

function unwrap<T>(data: unknown): T {
  const d = data as { ok?: boolean; error?: string };
  if (d && d.ok === false) {
    throw new Error(d.error || "Erro na API");
  }
  return data as T;
}

export function resetRealtimeVoiceCache(): void {
  statusCache = null;
}

export async function isRealtimeVoiceAvailable(): Promise<boolean> {
  if (statusCache !== null) return statusCache;
  try {
    const { data } = await api.get("voice/realtime/status", { timeout: 12_000 });
    const body = data as { ok?: boolean; available?: boolean; error?: string };
    if (body?.ok === false) {
      statusCache = false;
    } else {
      statusCache = Boolean(body?.available);
    }
  } catch {
    statusCache = false;
  }
  return statusCache;
}

export type RealtimeVoiceMode = "push" | "call";

export async function fetchRealtimeClientSecret(
  history: ChatHistoryPayload,
  mode: RealtimeVoiceMode = "push"
): Promise<RealtimeClientSecretPayload> {
  const { data } = await api.post(
    "voice/realtime/client-secret",
    { history, mode },
    { timeout: 30_000 }
  );
  const body = unwrap<RealtimeClientSecretPayload>(data);
  if (!body.client_secret || !body.ws_url) {
    throw new Error("Servidor não devolveu credenciais de voz em tempo real.");
  }
  return body;
}

export async function finishRealtimeVoiceTurn(opts: {
  userMessage: string;
  assistantReply: string;
  speak: boolean;
  history: ChatHistoryPayload;
}): Promise<SendChatResult> {
  const { data } = await api.post(
    "voice/realtime/finish",
    {
      user_message: opts.userMessage,
      assistant_reply: opts.assistantReply,
      speak: opts.speak,
      history: opts.history,
    },
    { timeout: 60_000 }
  );
  return unwrap<SendChatResult>(data);
}
