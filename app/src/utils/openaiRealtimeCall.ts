import type { ChatHistoryPayload } from "@/api/types";
import {
  fetchRealtimeClientSecret,
  finishRealtimeVoiceTurn,
  type RealtimeClientSecretPayload,
} from "@/api/realtimeVoice";
import { RealtimePcmPlayer, startPcmMicCapture, type PcmMicCapture } from "@/utils/openaiRealtimePcm";
import { RealtimePhoneCallWebRTC } from "@/utils/openaiRealtimeWebRTC";

type ServerEvent = {
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

function eventText(ev: ServerEvent): string {
  return (ev.delta || ev.transcript || ev.text || "").trim();
}

function isAudioDelta(type: string): boolean {
  return (
    type === "response.output_audio.delta" ||
    type === "response.audio.delta" ||
    type === "output_audio.delta"
  );
}

function isTranscriptDelta(type: string): boolean {
  return (
    type === "response.output_audio_transcript.delta" ||
    type === "response.audio_transcript.delta" ||
    type === "response.output_text.delta"
  );
}

/** Ligação WebSocket partilhada — evita 2–4 s de espera em cada «Chamada ao vivo». */
class CallWsPool {
  private ws: WebSocket | null = null;
  private sessionReady = false;
  private secret: RealtimeClientSecretPayload | null = null;
  private player: RealtimePcmPlayer | null = null;
  private pendingAudio: string[] = [];
  private connectPromise: Promise<void> | null = null;
  private onEvent: ((ev: ServerEvent) => void) | null = null;

  setEventHandler(handler: ((ev: ServerEvent) => void) | null): void {
    this.onEvent = handler;
  }

  appendAudio(base64: string): void {
    if (this.sessionReady && this.ws?.readyState === WebSocket.OPEN) {
      this.send({ type: "input_audio_buffer.append", audio: base64 });
    } else {
      this.pendingAudio.push(base64);
    }
  }

  async warm(history: ChatHistoryPayload): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN && this.sessionReady) {
      return;
    }
    this.secret = await fetchRealtimeClientSecret(history, "call");
    await this.ensureConnected();
  }

  async ensureConnected(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN && this.sessionReady) {
      return;
    }
    if (!this.secret) {
      throw new Error("Chamada: credenciais em falta.");
    }
    if (this.connectPromise) {
      await this.connectPromise;
      return;
    }
    this.connectPromise = this.openSocket(this.secret);
    try {
      await this.connectPromise;
    } finally {
      this.connectPromise = null;
    }
  }

  keepWarm(history: ChatHistoryPayload): void {
    void this.warm(history).catch(() => undefined);
  }

  release(fullyClose: boolean): void {
    if (fullyClose) {
      try {
        this.ws?.close();
      } catch {
        /* ignore */
      }
      this.ws = null;
      this.sessionReady = false;
      this.secret = null;
      this.player?.close();
      this.player = null;
      this.pendingAudio = [];
    }
    this.onEvent = null;
  }

  getPlayer(): RealtimePcmPlayer | null {
    return this.player;
  }

  clearAssistantAudio(): void {
    this.player?.flushPlayback();
    this.send({ type: "output_audio_buffer.clear" });
  }

  private send(payload: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(payload));
  }

  private flushPendingAudio(): void {
    if (!this.sessionReady) return;
    for (const chunk of this.pendingAudio) {
      this.send({ type: "input_audio_buffer.append", audio: chunk });
    }
    this.pendingAudio = [];
  }

  private openSocket(secret: RealtimeClientSecretPayload): Promise<void> {
    const { client_secret, ws_url } = secret;

    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        /* ignore */
      }
      this.ws = null;
    }
    this.sessionReady = false;

    return new Promise<void>((resolve, reject) => {
      const ws = new WebSocket(ws_url, [
        "realtime",
        `openai-insecure-api-key.${client_secret}`,
      ]);
      this.ws = ws;

      const timeout = window.setTimeout(() => {
        reject(new Error("Chamada: ligação demorou demais."));
      }, 15_000);

      const markReady = () => {
        if (this.sessionReady) return;
        window.clearTimeout(timeout);
        this.sessionReady = true;
        if (!this.player) {
          this.player = new RealtimePcmPlayer();
        }
        void this.player.resume();
        this.flushPendingAudio();
        resolve();
      };

      ws.onerror = () => {
        window.clearTimeout(timeout);
        reject(new Error("Falha na chamada de voz."));
      };
      ws.onclose = () => {
        this.sessionReady = false;
      };
      ws.onmessage = (msg) => {
        let ev: ServerEvent;
        try {
          ev = JSON.parse(String(msg.data)) as ServerEvent;
        } catch {
          return;
        }
        const type = ev.type || "";
        if (type === "error") {
          window.clearTimeout(timeout);
          reject(new Error(ev.error?.message || "Erro na chamada."));
          return;
        }
        if (type === "session.created" || type === "session.updated") {
          markReady();
          return;
        }
        if (this.sessionReady) {
          this.onEvent?.(ev);
        }
      };
      ws.onopen = () => {
        window.setTimeout(() => {
          if (!this.sessionReady && ws.readyState === WebSocket.OPEN) {
            markReady();
          }
        }, 500);
      };
    });
  }
}

const callPool = new CallWsPool();

/** Chamada WebSocket (fallback se WebRTC falhar). */
class RealtimePhoneCallWs {
  private mic: PcmMicCapture | null = null;
  private callbacks: PhoneCallCallbacks = {};
  private userTranscript = "";
  private assistantReply = "";
  private active = false;
  private speaking = false;
  private thinking = false;
  private history: ChatHistoryPayload = [];

  async start(history: ChatHistoryPayload, callbacks: PhoneCallCallbacks): Promise<void> {
    this.history = history;
    if (this.active) return;
    this.callbacks = callbacks;
    this.active = true;
    this.userTranscript = "";
    this.assistantReply = "";

    callPool.setEventHandler((ev) => this.handleEvent(ev));
    await callPool.warm(history);

    this.mic = await startPcmMicCapture((audio) => {
      callPool.appendAudio(audio);
    });
  }

  end(): void {
    this.active = false;
    this.mic?.stop();
    this.mic = null;
    this.setSpeaking(false);
    this.setThinking(false);
    callPool.setEventHandler(null);
    callPool.release(false);
    this.callbacks = {};
  }

  private setSpeaking(on: boolean): void {
    if (this.speaking === on) return;
    this.speaking = on;
    if (on) this.setThinking(false);
    this.callbacks.onSpeakingChange?.(on);
  }

  private setThinking(on: boolean): void {
    if (this.thinking === on) return;
    this.thinking = on;
    this.callbacks.onThinkingChange?.(on);
  }

  private handleEvent(ev: ServerEvent): void {
    if (!this.active) return;
    const type = ev.type || "";

    if (type === "input_audio_buffer.speech_started") {
      callPool.clearAssistantAudio();
      this.setSpeaking(false);
      this.setThinking(false);
      this.callbacks.onUserSpeechStart?.();
      return;
    }
    if (type === "input_audio_buffer.speech_stopped") {
      this.callbacks.onUserSpeechStop?.();
      this.setThinking(true);
      return;
    }

    if (type === "response.created" || type === "response.started") {
      this.setThinking(false);
    }

    if (type === "conversation.item.input_audio_transcription.completed") {
      const t = eventText(ev);
      if (t) this.userTranscript = t;
    }

    if (isTranscriptDelta(type)) {
      this.setThinking(false);
      const chunk = eventText(ev);
      if (chunk) {
        this.assistantReply += chunk;
        this.callbacks.onAssistantText?.(chunk, this.assistantReply);
      }
    }

    if (isAudioDelta(type) && ev.delta) {
      this.setThinking(false);
      this.setSpeaking(true);
      const player = callPool.getPlayer();
      void player?.resume();
      player?.playDelta(ev.delta);
    }

    if (type === "response.done" || type === "response.completed") {
      void this.onResponseDone();
    }
  }

  private async onResponseDone(): Promise<void> {
    this.setSpeaking(false);
    this.setThinking(false);
    const reply = this.assistantReply.trim();
    const user = this.userTranscript.trim();
    if (reply) {
      this.callbacks.onTurnComplete?.(user, reply);
      void finishRealtimeVoiceTurn({
        userMessage: user,
        assistantReply: reply,
        speak: false,
        history: this.history,
      }).catch(() => undefined);
    }
    this.assistantReply = "";
    this.userTranscript = "";
    callPool.keepWarm(this.history);
  }
}

/** Chamada contínua — WebRTC primeiro (mais rápido), senão WebSocket. */
export class RealtimePhoneCall {
  private impl: RealtimePhoneCallWebRTC | RealtimePhoneCallWs | null = null;

  async start(history: ChatHistoryPayload, callbacks: PhoneCallCallbacks): Promise<void> {
    if (RealtimePhoneCallWebRTC.isSupported()) {
      try {
        const webrtc = new RealtimePhoneCallWebRTC();
        this.impl = webrtc;
        await webrtc.start(history, callbacks);
        return;
      } catch {
        this.impl = null;
      }
    }
    const ws = new RealtimePhoneCallWs();
    this.impl = ws;
    await ws.start(history, callbacks);
  }

  end(): void {
    this.impl?.end();
    this.impl = null;
  }
}

export async function warmupPhoneCall(history: ChatHistoryPayload = []): Promise<void> {
  if (RealtimePhoneCallWebRTC.isSupported()) {
    void history;
    return;
  }
  callPool.keepWarm(history);
}
