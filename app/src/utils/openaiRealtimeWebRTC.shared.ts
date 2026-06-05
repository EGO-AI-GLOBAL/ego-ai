import type { ChatHistoryPayload } from "@/api/types";
import { api } from "@/api/client";

export type ServerEvent = {
  type?: string;
  delta?: string;
  transcript?: string;
  text?: string;
  error?: { message?: string };
};

export type PhoneCallCallbacks = {
  onUserSpeechStart?: () => void;
  onUserSpeechStop?: () => void;
  onAssistantText?: (chunk: string, full: string) => void;
  onThinkingChange?: (thinking: boolean) => void;
  onSpeakingChange?: (speaking: boolean) => void;
  onTurnComplete?: (user: string, assistant: string) => void;
  onError?: (message: string) => void;
};

export function eventText(ev: ServerEvent): string {
  return (ev.delta || ev.transcript || ev.text || "").trim();
}

export function isTranscriptDelta(type: string): boolean {
  return (
    type === "response.output_audio_transcript.delta" ||
    type === "response.audio_transcript.delta" ||
    type === "response.output_text.delta"
  );
}

export async function postSdpOffer(
  sdp: string,
  history: ChatHistoryPayload
): Promise<string> {
  const form = new FormData();
  form.append("sdp", sdp);
  form.append("history", JSON.stringify(history ?? []));

  const { data } = await api.post("voice/realtime/webrtc", form, {
    timeout: 45_000,
    responseType: "text",
    transformResponse: [(d) => d],
    headers: { "Content-Type": "multipart/form-data" },
  });

  const answer = typeof data === "string" ? data : String(data ?? "");
  if (!answer.trim().startsWith("v=")) {
    throw new Error("Resposta WebRTC inválida do servidor.");
  }
  return answer;
}
