import type { ChatHistoryPayload, SendChatResult } from "@/api/types";
import {
  fetchRealtimeClientSecret,
  finishRealtimeVoiceTurn,
  type RealtimeClientSecretPayload,
} from "@/api/realtimeVoice";
import { RealtimePcmPlayer, startPcmMicCapture, type PcmMicCapture } from "@/utils/openaiRealtimePcm";

type ServerEvent = {
  type?: string;
  delta?: string;
  transcript?: string;
  text?: string;
  error?: { message?: string };
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

/** Pré-carrega credenciais (chamar ao abrir o chat). */
export async function warmupRealtimeVoice(
  history: ChatHistoryPayload = []
): Promise<void> {
  await OpenAIRealtimePushToTalk.shared.warmup(history);
}

export class OpenAIRealtimePushToTalk {
  static readonly shared = new OpenAIRealtimePushToTalk();

  private ws: WebSocket | null = null;
  private mic: PcmMicCapture | null = null;
  private player: RealtimePcmPlayer | null = null;
  private pendingChunks: string[] = [];
  private chunkCount = 0;
  private userTranscript = "";
  private assistantReply = "";
  private responseDone = false;
  private turnReject: ((err: Error) => void) | null = null;
  private turnResolve: (() => void) | null = null;
  private sessionReady = false;
  private secretPayload: RealtimeClientSecretPayload | null = null;
  private connectPromise: Promise<void> | null = null;

  async warmup(history: ChatHistoryPayload): Promise<void> {
    try {
      this.secretPayload = await fetchRealtimeClientSecret(history);
    } catch {
      this.secretPayload = null;
    }
  }

  async startMic(history: ChatHistoryPayload = []): Promise<void> {
    this.pendingChunks = [];
    this.chunkCount = 0;
    this.userTranscript = "";
    this.assistantReply = "";
    this.responseDone = false;

    if (!this.secretPayload) {
      await this.warmup(history);
    }
    if (!this.secretPayload) {
      throw new Error("Voz em tempo real indisponível no servidor.");
    }

    await this.ensureConnected(this.secretPayload);

    this.send({ type: "input_audio_buffer.clear" });

    this.mic = await startPcmMicCapture((audio) => {
      this.chunkCount += 1;
      if (this.sessionReady) {
        this.send({ type: "input_audio_buffer.append", audio });
      } else {
        this.pendingChunks.push(audio);
      }
    });
  }

  stopMic(): void {
    this.mic?.stop();
    this.mic = null;
  }

  async completeTurn(
    speak: boolean,
    history: ChatHistoryPayload
  ): Promise<SendChatResult> {
    this.stopMic();
    if (this.chunkCount < 1) {
      throw new Error("Gravação demasiado curta. Fale pelo menos 1 segundo.");
    }

    if (!this.sessionReady) {
      await this.ensureConnected(this.secretPayload!);
    }

    for (const chunk of this.pendingChunks) {
      this.send({ type: "input_audio_buffer.append", audio: chunk });
    }
    this.pendingChunks = [];

    this.send({ type: "input_audio_buffer.commit" });
    this.send({ type: "response.create" });

    await new Promise<void>((resolve, reject) => {
      this.turnResolve = resolve;
      this.turnReject = reject;
      window.setTimeout(() => {
        if (!this.responseDone) {
          reject(new Error("A IA de voz demorou demais. Tente uma frase mais curta."));
        }
      }, 60_000);
    });

    const reply = this.assistantReply.trim();
    const userMsg = this.userTranscript.trim();
    if (!reply) {
      throw new Error("Sem resposta de voz da IA.");
    }

    const optimistic: SendChatResult = {
      reply,
      user_transcript: userMsg || undefined,
      voice_engine: "openai_realtime",
      warnings: [],
    };

    void finishRealtimeVoiceTurn({
      userMessage: userMsg,
      assistantReply: reply,
      speak,
      history,
    }).catch(() => undefined);

    void this.warmup(history);

    return optimistic;
  }

  dispose(): void {
    this.stopMic();
    this.pendingChunks = [];
    this.chunkCount = 0;
    this.player?.close();
    this.player = null;
    this.sessionReady = false;
    this.connectPromise = null;
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        /* ignore */
      }
      this.ws = null;
    }
  }

  private async ensureConnected(secret: RealtimeClientSecretPayload): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN && this.sessionReady) {
      return;
    }
    if (this.connectPromise) {
      await this.connectPromise;
      return;
    }

    this.connectPromise = this.openSocket(secret);
    try {
      await this.connectPromise;
    } finally {
      this.connectPromise = null;
    }
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

      const connectTimeout = window.setTimeout(() => {
        reject(new Error("OpenAI Realtime: ligação demorou demais."));
      }, 18_000);

      const markReady = () => {
        if (this.sessionReady) return;
        window.clearTimeout(connectTimeout);
        this.sessionReady = true;
        if (!this.player) {
          this.player = new RealtimePcmPlayer();
        }
        void this.player.resume();
        for (const chunk of this.pendingChunks) {
          this.send({ type: "input_audio_buffer.append", audio: chunk });
        }
        this.pendingChunks = [];
        resolve();
      };

      ws.onerror = () => {
        window.clearTimeout(connectTimeout);
        reject(new Error("Falha na ligação de voz em tempo real."));
      };
      ws.onclose = () => {
        this.sessionReady = false;
        if (!this.responseDone && this.turnReject) {
          this.turnReject(new Error("Ligação de voz fechada antes da resposta."));
        }
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
          window.clearTimeout(connectTimeout);
          reject(new Error(ev.error?.message || "Erro na sessão de voz."));
          return;
        }
        if (type === "session.created" || type === "session.updated") {
          markReady();
          return;
        }
        if (this.sessionReady) {
          this.onMessage(msg);
        }
      };

      ws.onopen = () => {
        window.setTimeout(() => {
          if (!this.sessionReady && ws.readyState === WebSocket.OPEN) {
            markReady();
          }
        }, 1200);
      };
    });
  }

  private send(payload: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(payload));
  }

  private onMessage(msg: MessageEvent): void {
    let ev: ServerEvent;
    try {
      ev = JSON.parse(String(msg.data)) as ServerEvent;
    } catch {
      return;
    }

    const type = ev.type || "";

    if (type === "error") {
      this.turnReject?.(new Error(ev.error?.message || "Erro na sessão de voz."));
      return;
    }

    if (type === "conversation.item.input_audio_transcription.completed") {
      const t = eventText(ev);
      if (t) this.userTranscript = t;
    }

    if (isTranscriptDelta(type)) {
      this.assistantReply += eventText(ev);
    }

    if (isAudioDelta(type) && ev.delta) {
      void this.player?.resume();
      this.player?.playDelta(ev.delta);
    }

    if (type === "response.done" || type === "response.completed") {
      this.responseDone = true;
      void this.finishTurn();
    }
  }

  private async finishTurn(): Promise<void> {
    await this.player?.drain(80);
    const reply = this.assistantReply.trim();
    if (!reply) {
      this.turnReject?.(new Error("Sem resposta de voz da IA. Fale mais alto e tente outra vez."));
      return;
    }
    this.turnResolve?.();
    this.turnResolve = null;
    this.turnReject = null;
  }
}
