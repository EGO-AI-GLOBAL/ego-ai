import { Audio } from "expo-av";
import { NativeModules } from "react-native";
import type { ChatHistoryPayload } from "@/api/types";
import { finishRealtimeVoiceTurn } from "@/api/realtimeVoice";
import {
  eventText,
  isTranscriptDelta,
  postSdpOffer,
  type PhoneCallCallbacks,
  type ServerEvent,
} from "@/utils/openaiRealtimeWebRTC.shared";

export type { PhoneCallCallbacks } from "@/utils/openaiRealtimeWebRTC.shared";

type WebRtcNative = {
  RTCPeerConnection: new (config: RTCConfiguration) => RTCPeerConnection;
  RTCSessionDescription: new (desc: RTCSessionDescriptionInit) => RTCSessionDescription;
  mediaDevices: {
    getUserMedia: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
  };
};

function nativeWebRtcModule(): WebRtcNative | null {
  if ((NativeModules as { WebRTCModule?: unknown }).WebRTCModule == null) {
    return null;
  }
  try {
    return require("react-native-webrtc") as WebRtcNative;
  } catch {
    return null;
  }
}

export function isNativeWebRtcAvailable(): boolean {
  return nativeWebRtcModule() != null;
}

async function prepareNativeCallAudio(): Promise<void> {
  await Audio.setAudioModeAsync({
    allowsRecordingIOS: true,
    playsInSilentModeIOS: true,
    staysActiveInBackground: false,
    shouldDuckAndroid: true,
    playThroughEarpieceAndroid: false,
  });
}

/** Chamada turbo por WebRTC nativo (Android / iPhone — requer dev build ou APK). */
export class RealtimePhoneCallWebRTC {
  private pc: RTCPeerConnection | null = null;
  private dc: RTCDataChannel | null = null;
  private stream: MediaStream | null = null;
  private callbacks: PhoneCallCallbacks = {};
  private userTranscript = "";
  private assistantReply = "";
  private active = false;
  private speaking = false;
  private thinking = false;
  private history: ChatHistoryPayload = [];

  static isSupported(): boolean {
    return isNativeWebRtcAvailable();
  }

  async start(history: ChatHistoryPayload, callbacks: PhoneCallCallbacks): Promise<void> {
    const webrtc = nativeWebRtcModule();
    if (!webrtc) {
      throw new Error(
        "Chamada ao vivo no celular exige o app instalado (APK ou TestFlight). No Expo Go use o microfone ou teste no PC."
      );
    }

    const { RTCPeerConnection, RTCSessionDescription, mediaDevices } = webrtc;

    await prepareNativeCallAudio();

    this.history = history;
    this.callbacks = callbacks;
    this.active = true;
    this.userTranscript = "";
    this.assistantReply = "";

    this.pc = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    });

    this.pc.ontrack = () => {
      this.setThinking(false);
      this.setSpeaking(true);
    };

    this.stream = await mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    });
    for (const track of this.stream.getTracks()) {
      this.pc.addTrack(track, this.stream);
    }

    this.dc = this.pc.createDataChannel("oai-events");
    this.dc.addEventListener("message", (e: MessageEvent) => {
      try {
        const ev = JSON.parse(String(e.data)) as ServerEvent;
        this.onEvent(ev);
      } catch {
        /* ignore */
      }
    });

    const offer = await this.pc.createOffer({});
    await this.pc.setLocalDescription(offer);
    if (!offer.sdp) {
      throw new Error("Falha ao criar oferta WebRTC.");
    }

    const answerSdp = await postSdpOffer(offer.sdp, history);
    await this.pc.setRemoteDescription(
      new RTCSessionDescription({ type: "answer", sdp: answerSdp })
    );
  }

  end(): void {
    this.active = false;
    this.setSpeaking(false);
    this.setThinking(false);
    this.dc?.close();
    this.dc = null;
    this.pc?.close();
    this.pc = null;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
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

  private onEvent(ev: ServerEvent): void {
    if (!this.active) return;
    const type = ev.type || "";

    if (type === "input_audio_buffer.speech_started") {
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
  }
}

export function warmupPhoneCallWebRTC(history: ChatHistoryPayload = []): void {
  if (!isNativeWebRtcAvailable()) return;
  void import("@/api/realtimeVoice")
    .then(({ isRealtimeVoiceAvailable }) => isRealtimeVoiceAvailable())
    .catch(() => false);
  void history;
}
