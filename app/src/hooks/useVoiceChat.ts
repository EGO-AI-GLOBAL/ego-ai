import * as FileSystem from "expo-file-system";
import * as Speech from "expo-speech";
import { useCallback, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import {
  fetchTtsAudio,
  sendChatVoiceBlob,
  sendChatVoiceFromUri,
  sendChatVoiceMessage,
} from "@/api/client";
import type { ChatHistoryPayload, SendChatResult } from "@/api/types";
import type { AudioPlaybackSpeed } from "@/constants/audioSpeed";
import { resolveSpeechVoiceId } from "@/constants/personas";
import { getExpoAudio } from "@/utils/expoAvSafe";
import { plainTextForSpeech } from "@/utils/speechText";
import {
  mapGetUserMediaError,
  webMicMode,
  webMicUnavailableMessage,
  iosSafariMicHelpMessage,
} from "@/utils/webVoiceCapture";

const isWeb = Platform.OS === ("web" as typeof Platform.OS);

type WebRecorderState = {
  recorder: MediaRecorder;
  stream: MediaStream;
  chunks: Blob[];
};

/** Liberta gravação nativa (prepared ou a gravar) — evita "Only one Recording object…". */
async function safeStopNativeRecording(
  rec: import("expo-av").Audio.Recording | null
): Promise<void> {
  if (!rec) return;
  try {
    await rec.stopAndUnloadAsync();
  } catch {
    /* gravação já inexistente ou nunca iniciou — ignorar */
  }
}

function normalizeBase64Payload(b64: string): string {
  let s = (b64 || "").trim();
  if (s.startsWith("data:") && s.includes(",")) {
    const comma = s.indexOf(",");
    s = comma >= 0 ? s.slice(comma + 1) : s;
  }
  return s.replace(/\s/g, "");
}

function normalizeRecordingMime(mime: string): string {
  const m = (mime || "").toLowerCase();
  if (m.includes("mp4") || m.includes("m4a") || m.includes("aac")) return "audio/mp4";
  if (m.includes("webm")) return "audio/webm";
  if (m.includes("wav")) return "audio/wav";
  return mime || "audio/mp4";
}

function isIosWebBrowser(): boolean {
  return typeof navigator !== "undefined" && /iPad|iPhone|iPod/i.test(navigator.userAgent);
}

function blobToBase64(blob: Blob): Promise<{ base64: string; mime: string }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const dataUrl = reader.result;
      if (typeof dataUrl !== "string") {
        reject(new Error("Falha ao ler gravação de voz."));
        return;
      }
      const base64 = dataUrl.split(",")[1] || "";
      if (!base64) {
        reject(new Error("Gravação vazia."));
        return;
      }
      resolve({
        base64: normalizeBase64Payload(base64),
        mime: normalizeRecordingMime(blob.type || "audio/mp4"),
      });
    };
    reader.onerror = () => reject(new Error("Falha ao ler gravação de voz."));
    reader.readAsDataURL(blob);
  });
}

function pickWebRecorderMime(): string {
  if (typeof MediaRecorder === "undefined") return "";
  // Safari iPhone (HTTPS)
  if (MediaRecorder.isTypeSupported("audio/mp4")) return "audio/mp4";
  if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
    return "audio/webm;codecs=opus";
  }
  if (MediaRecorder.isTypeSupported("audio/webm")) return "audio/webm";
  return "";
}

function mimeFromUri(uri: string): string {
  const u = uri.toLowerCase();
  if (u.endsWith(".wav")) return "audio/wav";
  if (u.endsWith(".mp3")) return "audio/mpeg";
  if (u.endsWith(".m4a") || u.endsWith(".mp4")) return "audio/mp4";
  if (u.endsWith(".webm")) return "audio/webm";
  return "audio/m4a";
}

function deviceSpeechRate(speed: AudioPlaybackSpeed): number {
  if (Platform.OS === "ios") {
    return speed === 1 ? 0.5 : speed === 1.5 ? 0.55 : 0.62;
  }
  return speed;
}

function isMaleVoiceName(name: string): boolean {
  return /male|mascul|homem|man\b|#male|male_|daniel|joão|joao|pedro|antonio|bruno|guy|davis|christopher|eric|roger/i.test(
    name
  );
}

function isFemaleVoiceName(name: string): boolean {
  return /female|femin|mulher|woman|#female|female_|francisca|luciana|joana|vitória|vitoria|ana|maria|brenda|thalita|yara|leila|giovanna|jenny|aria|emma|michelle|amber|nova/i.test(
    name
  );
}

function wantsMaleSpeech(voiceId?: string, avatarId?: string): boolean {
  return resolveSpeechVoiceId(voiceId, avatarId).startsWith("vm");
}

function unlockWebAudioPlayback(): void {
  if (!isWeb || typeof window === "undefined") return;
  try {
    const w = window as Window & { webkitAudioContext?: typeof AudioContext };
    const Ctx = w.AudioContext || w.webkitAudioContext;
    if (Ctx) {
      const ctx = new Ctx();
      void ctx.resume();
    }
    const prime = new window.Audio();
    prime.preload = "auto";
    prime.volume = 0.001;
    void prime.play().catch(() => undefined);
  } catch {
    /* ignore */
  }
}

function speakWithWebSpeech(
  text: string,
  voiceId?: string,
  avatarId?: string,
  rate: AudioPlaybackSpeed = 1
): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      reject(new Error("Browser sem síntese de voz."));
      return;
    }
    const trimmed = plainTextForSpeech(text);
    if (!trimmed) {
      resolve();
      return;
    }
    const resolved = resolveSpeechVoiceId(voiceId, avatarId);
    const wantMale = resolved.startsWith("vm") || resolved.startsWith("pvm");
    const utter = new SpeechSynthesisUtterance(trimmed);
    utter.lang = "pt-BR";
    utter.rate = rate === 1 ? 1 : rate === 1.5 ? 1.12 : 1.25;

    const assignVoice = () => {
      const voices = window.speechSynthesis.getVoices();
      const pt = voices.filter((v) => v.lang.toLowerCase().startsWith("pt"));
      const pool = pt.length ? pt : voices;
      if (wantMale) {
        const male = pool.find((v) =>
          /antonio|felipe|joão|joao|male|mascul|daniel|tiago|bruno|humberto|nicolau|donato/i.test(
            v.name
          )
        );
        if (male) {
          utter.voice = male;
        } else {
          reject(
            new Error(
              "Voz masculina indisponível no Safari. Toque em «Ouvir resposta» para usar o áudio do servidor."
            )
          );
          return;
        }
      } else {
        const femaleHints =
          /francisca|luciana|female|femin|ana|maria|brenda|thalita|yara|leila|giovanna|michelle|emma|aria|jenny|amber/i;
        const female = pool.find((v) => femaleHints.test(v.name));
        if (female) utter.voice = female;
      }
    };

    assignVoice();
    window.speechSynthesis.onvoiceschanged = assignVoice;
    utter.onend = () => resolve();
    utter.onerror = () => reject(new Error("Voz do Safari bloqueada. Toque Enviar de novo."));
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
  });
}

/** iPhone: vozes pt-BR nativas (Felipe = masculino, Luciana = feminino). */
const IOS_PT_VOICE_HINTS: { male: string[]; female: string[] } = {
  male: ["felipe", "tiago", "joão", "joao", "daniel", "male"],
  female: ["luciana", "francisca", "brenda", "thalita", "yara", "leila", "female"],
};

function findVoiceByHints(
  voices: Speech.Voice[],
  hints: string[],
  exclude?: RegExp
): string | undefined {
  for (const hint of hints) {
    const found = voices.find((v) => {
      const blob = `${v.name || ""} ${v.identifier || ""}`.toLowerCase();
      if (exclude?.test(blob)) return false;
      return blob.includes(hint);
    });
    if (found?.identifier) return found.identifier;
  }
  return undefined;
}

async function pickDevicePtVoice(
  voiceId?: string,
  avatarId?: string
): Promise<string | undefined> {
  const wantMale = wantsMaleSpeech(voiceId, avatarId);
  const femaleExclude =
    /luciana|francisca|brenda|thalita|yara|leila|giovanna|joana|vitória|vitoria|femin|female|mulher|woman/i;
  try {
    const voices = await Speech.getAvailableVoicesAsync();
    const pt = voices.filter((v) =>
      (v.language || "").toLowerCase().startsWith("pt")
    );
    const ptBr = voices.filter((v) => {
      const lang = (v.language || "").toLowerCase();
      return lang === "pt-br" || lang.startsWith("pt");
    });
    const pool = ptBr.length ? ptBr : pt;
    const all = voices;
    const byHint = (v: { name?: string; identifier?: string }) =>
      `${v.name || ""} ${v.identifier || ""}`.toLowerCase();

    if (Platform.OS === "ios") {
      if (wantMale) {
        const iosMale = findVoiceByHints(pool, IOS_PT_VOICE_HINTS.male, femaleExclude);
        if (iosMale) return iosMale;
      } else {
        const iosFemale = findVoiceByHints(pool, IOS_PT_VOICE_HINTS.female);
        if (iosFemale) return iosFemale;
      }
    }

    if (wantMale) {
      const male = pool.find(
        (v) =>
          isMaleVoiceName(`${v.name || ""} ${v.identifier || ""}`) &&
          !isFemaleVoiceName(`${v.name || ""} ${v.identifier || ""}`) &&
          !femaleExclude.test(byHint(v))
      );
      if (male?.identifier) return male.identifier;

      const maleById = pool.find(
        (v) =>
          /male|masc|homem|#male|male_/.test(byHint(v)) && !femaleExclude.test(byHint(v))
      );
      if (maleById?.identifier) return maleById.identifier;

      const notFemalePt = pool.find(
        (v) =>
          !isFemaleVoiceName(`${v.name || ""} ${v.identifier || ""}`) &&
          !femaleExclude.test(byHint(v))
      );
      if (notFemalePt?.identifier) return notFemalePt.identifier;

      // 4) Last fallback across all locales still preferring male hints.
      const maleAny = all.find(
        (v) =>
          isMaleVoiceName(`${v.name || ""} ${v.identifier || ""}`) &&
          !isFemaleVoiceName(`${v.name || ""} ${v.identifier || ""}`)
      );
      if (maleAny?.identifier) return maleAny.identifier;

      return pool[0]?.identifier || all[0]?.identifier;
    }
    const female = pool.find(
      (v) =>
        isFemaleVoiceName(`${v.name || ""} ${v.identifier || ""}`) &&
        !isMaleVoiceName(`${v.name || ""} ${v.identifier || ""}`)
    );
    if (female?.identifier) return female.identifier;
    const notMale = pool.find(
      (v) => !isMaleVoiceName(`${v.name || ""} ${v.identifier || ""}`)
    );
    return notMale?.identifier || pool[0]?.identifier;
  } catch {
    return undefined;
  }
}

function speakWithDeviceTts(
  text: string,
  voiceId: string | undefined,
  avatarId: string | undefined,
  speed: AudioPlaybackSpeed
): Promise<void> {
  if (isWeb) {
    return speakWithWebSpeech(text, voiceId, avatarId, speed);
  }
  return new Promise((resolve, reject) => {
    const trimmed = plainTextForSpeech(text);
    if (!trimmed) {
      resolve();
      return;
    }
    void (async () => {
      const voice = await pickDevicePtVoice(voiceId, avatarId);
      Speech.speak(trimmed, {
        language: "pt-BR",
        voice,
        rate: deviceSpeechRate(speed),
        onDone: () => resolve(),
        onStopped: () => resolve(),
        onError: () => reject(new Error("Síntese de voz do dispositivo falhou.")),
      });
    })();
  });
}

async function withSpeaking(
  setSpeaking: (v: boolean) => void,
  fn: () => Promise<void>
): Promise<void> {
  setSpeaking(true);
  try {
    await fn();
  } finally {
    setSpeaking(false);
  }
}

function base64ToBlob(b64: string, mime: string): Blob {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type: mime || "audio/mpeg" });
}

function playWebBase64(
  b64: string,
  mime: string,
  rate: AudioPlaybackSpeed,
  audioRef: { current: HTMLAudioElement | null }
): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined") {
      reject(new Error("Browser sem suporte a áudio."));
      return;
    }
    let objectUrl: string | null = null;
    const cleanup = () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
        objectUrl = null;
      }
    };
    try {
      objectUrl = URL.createObjectURL(base64ToBlob(b64, mime));
    } catch {
      cleanup();
      reject(new Error("Não foi possível preparar o áudio."));
      return;
    }
    const el = new window.Audio(objectUrl);
    el.playbackRate = rate;
    el.preload = "auto";
    el.setAttribute("playsinline", "true");
    el.setAttribute("webkit-playsinline", "true");
    (el as HTMLAudioElement & { playsInline?: boolean }).playsInline = true;
    audioRef.current = el;
    el.onended = () => {
      audioRef.current = null;
      cleanup();
      resolve();
    };
    el.onerror = () => {
      audioRef.current = null;
      cleanup();
      reject(new Error("O browser bloqueou a reprodução. Clique na página e tente de novo."));
    };
    void el.play().catch(() => {
      audioRef.current = null;
      cleanup();
      reject(
        new Error("Autoplay bloqueado: clique na página e envie a mensagem outra vez.")
      );
    });
  });
}

export function useVoiceChat() {
  const [isRecording, setIsRecording] = useState(false);
  const [micSessionActive, setMicSessionActive] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [audioSpeed, setAudioSpeedState] = useState<AudioPlaybackSpeed>(1);
  const recordingRef = useRef<import("expo-av").Audio.Recording | null>(null);
  const webRecorderRef = useRef<WebRecorderState | null>(null);
  const recordingStartedAtRef = useRef<number>(0);
  const isRecordingRef = useRef(false);
  const soundRef = useRef<import("expo-av").Audio.Sound | null>(null);
  const webAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioSpeedRef = useRef<AudioPlaybackSpeed>(1);

  useEffect(() => {
    audioSpeedRef.current = audioSpeed;
  }, [audioSpeed]);

  useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);

  const waitForRecording = useCallback(async (timeoutMs = 2500): Promise<boolean> => {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (isRecordingRef.current) return true;
      await new Promise((r) => setTimeout(r, 100));
    }
    return isRecordingRef.current;
  }, []);

  useEffect(() => {
    return () => {
      Speech.stop();
      void safeStopNativeRecording(recordingRef.current);
      recordingRef.current = null;
      if (webRecorderRef.current) {
        try {
          webRecorderRef.current.recorder.stop();
        } catch {
          /* ignore */
        }
        webRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
        webRecorderRef.current = null;
      }
      void soundRef.current?.stopAsync().catch(() => undefined);
    };
  }, []);

  const applyPlaybackRate = useCallback(async (rate: AudioPlaybackSpeed) => {
    if (isWeb && webAudioRef.current) {
      webAudioRef.current.playbackRate = rate;
    }
    if (soundRef.current) {
      try {
        await soundRef.current.setRateAsync(rate, true);
      } catch {
        /* ignore */
      }
    }
  }, []);

  const setAudioSpeed = useCallback(
    (speed: AudioPlaybackSpeed) => {
      setAudioSpeedState(speed);
      void applyPlaybackRate(speed);
    },
    [applyPlaybackRate]
  );

  const stopPlayback = useCallback(async (opts?: { keepSpeaking?: boolean }) => {
    Speech.stop();
    if (soundRef.current) {
      try {
        await soundRef.current.stopAsync();
        await soundRef.current.unloadAsync();
      } catch {
        /* ignore */
      }
      soundRef.current = null;
    }
    if (isWeb && webAudioRef.current) {
      try {
        webAudioRef.current.pause();
      } catch {
        /* ignore */
      }
      webAudioRef.current = null;
    }
    if (!opts?.keepSpeaking) {
      setIsSpeaking(false);
    }
  }, []);

  const playBase64Audio = useCallback(
    async (b64: string, mime = "audio/mpeg"): Promise<void> => {
      if (!b64?.trim()) {
        throw new Error("Áudio vazio.");
      }
      const rate = audioSpeedRef.current;
      setIsSpeaking(true);
      await stopPlayback({ keepSpeaking: true });
      try {
        if (isWeb) {
          unlockWebAudioPlayback();
          try {
            await playWebBase64(b64, mime, rate, webAudioRef);
          } finally {
            setIsSpeaking(false);
          }
          return;
        }
        const dir = FileSystem.cacheDirectory;
        if (!dir) {
          throw new Error("Cache de áudio indisponível.");
        }
        const Audio = getExpoAudio();
        if (!Audio) {
          throw new Error("Áudio indisponível neste dispositivo.");
        }
        const ext = mime.includes("wav") ? "wav" : "mp3";
        const path = `${dir}ego_tts_${Date.now()}.${ext}`;
        await FileSystem.writeAsStringAsync(path, b64, {
          encoding: FileSystem.EncodingType.Base64,
        });
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: false,
          playsInSilentModeIOS: true,
          shouldDuckAndroid: true,
          playThroughEarpieceAndroid: false,
        });
        const { sound } = await Audio.Sound.createAsync({ uri: path });
        soundRef.current = sound;
        sound.setOnPlaybackStatusUpdate((status) => {
          if (status.isLoaded && status.didJustFinish) {
            void stopPlayback();
          }
        });
        await sound.setRateAsync(rate, true);
        await sound.playAsync();
      } catch (e) {
        setIsSpeaking(false);
        throw e;
      }
    },
    [stopPlayback]
  );

  const playReplyAudio = useCallback(
    async (
      result: SendChatResult,
      voiceId?: string,
      avatarId?: string
    ): Promise<string | null> => {
      const resolvedVoice = resolveSpeechVoiceId(voiceId, avatarId);
      const reply = plainTextForSpeech(result.reply || "");
      if (!reply) {
        return "Resposta vazia.";
      }

      const speed = audioSpeedRef.current;
      const wantMale =
        resolvedVoice.startsWith("vm") || resolvedVoice.startsWith("pvm");

      const tryEmbeddedTts = async (): Promise<boolean> => {
        if (!result.tts_audio_base64?.trim()) return false;
        const embeddedVoice = (result.tts_voice_id || "").toLowerCase();
        if (embeddedVoice && embeddedVoice !== resolvedVoice) {
          return false;
        }
        await playBase64Audio(
          result.tts_audio_base64,
          result.tts_mime || "audio/mpeg"
        );
        return true;
      };

      try {
        const { audio_base64, mime } = await fetchTtsAudio(
          reply,
          resolvedVoice,
          avatarId
        );
        await playBase64Audio(audio_base64, mime || "audio/mpeg");
        return null;
      } catch (fetchErr) {
        const fetchMsg =
          fetchErr instanceof Error ? fetchErr.message : "Erro ao gerar áudio.";
        try {
          if (await tryEmbeddedTts()) {
            return null;
          }
        } catch {
          /* segue para fallback */
        }

        if (isWeb && wantMale) {
          setIsSpeaking(false);
          return `${fetchMsg} Toque em «Ouvir resposta» (áudio masculino do servidor).`;
        }

        try {
          await withSpeaking(setIsSpeaking, () =>
            isWeb
              ? speakWithWebSpeech(reply, resolvedVoice, avatarId, speed)
              : speakWithDeviceTts(reply, resolvedVoice, avatarId, speed)
          );
          if (isWeb) {
            return "Toque em «Ouvir resposta» se não ouvir o som.";
          }
          return result.tts_error
            ? `${result.tts_error} — voz do dispositivo.`
            : null;
        } catch (e2) {
          setIsSpeaking(false);
          const tail = e2 instanceof Error ? e2.message : "";
          return [fetchMsg, result.tts_error, tail]
            .filter(Boolean)
            .join(" ");
        }
      }
    },
    [playBase64Audio]
  );

  const startRecording = useCallback(async (_history?: ChatHistoryPayload) => {
    unlockWebAudioPlayback();
    await stopPlayback();
    if (isWeb) {
      if (webMicMode() === "needs-https") {
        throw new Error(iosSafariMicHelpMessage());
      }
      if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
        throw new Error(webMicUnavailableMessage());
      }
      if (typeof MediaRecorder === "undefined") {
        throw new Error("Gravação de voz não suportada neste browser.");
      }
      try {
        setMicSessionActive(true);
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeType = pickWebRecorderMime();
        const recorder = mimeType
          ? new MediaRecorder(stream, { mimeType })
          : new MediaRecorder(stream);
        const chunks: Blob[] = [];
        recorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            chunks.push(event.data);
          }
        };
        if (isIosWebBrowser()) {
          recorder.start();
        } else {
          recorder.start(250);
        }
        webRecorderRef.current = { recorder, stream, chunks };
        recordingStartedAtRef.current = Date.now();
        setIsRecording(true);
      } catch (err) {
        setMicSessionActive(false);
        setIsRecording(false);
        throw new Error(mapGetUserMediaError(err));
      }
      return;
    }
    if (recordingRef.current) {
      await safeStopNativeRecording(recordingRef.current);
      recordingRef.current = null;
    }
    const Audio = getExpoAudio();
    if (!Audio) {
      throw new Error("Áudio indisponível neste dispositivo.");
    }
    const perm = await Audio.requestPermissionsAsync();
    if (!perm.granted) {
      throw new Error("Permissão do microfone negada.");
    }
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
      shouldDuckAndroid: true,
      playThroughEarpieceAndroid: false,
    });
    const recordingOptions: Audio.RecordingOptions = {
      ...Audio.RecordingOptionsPresets.HIGH_QUALITY,
      android: {
        extension: ".m4a",
        outputFormat: Audio.AndroidOutputFormat.MPEG_4,
        audioEncoder: Audio.AndroidAudioEncoder.AAC,
        sampleRate: 44100,
        numberOfChannels: 1,
        bitRate: 128000,
      },
      ios: Audio.RecordingOptionsPresets.HIGH_QUALITY.ios,
    };
    const { recording } = await Audio.Recording.createAsync(recordingOptions);
    recordingRef.current = recording;
    recordingStartedAtRef.current = Date.now();
    setMicSessionActive(true);
    setIsRecording(true);
  }, [stopPlayback]);

  const finishWebRecording = useCallback((): Promise<{ blob: Blob; mime: string }> => {
    return new Promise((resolve, reject) => {
      const state = webRecorderRef.current;
      if (!state) {
        reject(new Error("Nenhuma gravação ativa."));
        return;
      }

      const finalize = () => {
        const mime = normalizeRecordingMime(
          state.recorder.mimeType || pickWebRecorderMime() || "audio/mp4"
        );
        const blob = new Blob(state.chunks, { type: mime });
        if (blob.size < 512) {
          reject(new Error("Gravação demasiado curta. Fale pelo menos 2 segundos."));
          return;
        }
        resolve({ blob, mime });
      };

      state.recorder.onstop = () => {
        state.stream.getTracks().forEach((track) => track.stop());
        webRecorderRef.current = null;
        const delay = isIosWebBrowser() ? 450 : 50;
        window.setTimeout(finalize, delay);
      };

      state.recorder.onerror = () => {
        state.stream.getTracks().forEach((track) => track.stop());
        webRecorderRef.current = null;
        reject(new Error("Erro na gravação de voz."));
      };

      try {
        if (typeof state.recorder.requestData === "function") {
          state.recorder.requestData();
        }
        state.recorder.stop();
      } catch {
        state.stream.getTracks().forEach((track) => track.stop());
        webRecorderRef.current = null;
        reject(new Error("Não foi possível parar a gravação."));
      }
    });
  }, []);

  const stopRecordingAndSend = useCallback(
    async (
      speak = true,
      history?: ChatHistoryPayload,
      _opts?: { onDelta?: (chunk: string, full: string) => void }
    ): Promise<SendChatResult> => {
      const hist = history ?? [];
      if (isWeb) {
        if (!webRecorderRef.current) {
          throw new Error("Nenhuma gravação ativa. Toque no microfone para gravar.");
        }
        const elapsed = Date.now() - recordingStartedAtRef.current;
        if (elapsed < 900) {
          throw new Error("Fale pelo menos 2 segundos antes de tocar em Enviar.");
        }
        const { blob, mime } = await finishWebRecording();
        setMicSessionActive(false);
        setIsRecording(false);
        recordingStartedAtRef.current = 0;
        // Multipart é mais fiável no browser (evita base64 corrompido no proxy Metro).
        try {
          return await sendChatVoiceBlob({ blob, speak, history: hist });
        } catch (multipartErr) {
          const { base64 } = await blobToBase64(blob);
          try {
            return await sendChatVoiceMessage({
              audioBase64: base64,
              audioMime: mime,
              speak,
              history: hist,
            });
          } catch {
            throw multipartErr;
          }
        }
      }

      const rec = recordingRef.current;
      if (!rec) {
        throw new Error("Nenhuma gravação ativa.");
      }
      const elapsed = Date.now() - recordingStartedAtRef.current;
      if (elapsed < 900) {
        throw new Error("Fale pelo menos 2 segundos antes de tocar em Enviar.");
      }
      setIsRecording(false);
      recordingRef.current = null;
      setMicSessionActive(false);
      const uri = rec.getURI();
      await safeStopNativeRecording(rec);
      const Audio = getExpoAudio();
      if (Audio) {
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: false,
          playsInSilentModeIOS: true,
          shouldDuckAndroid: true,
          playThroughEarpieceAndroid: false,
        });
      }
      if (!uri) {
        throw new Error("Gravação vazia.");
      }
      const audioMime = mimeFromUri(uri);
      try {
        return await sendChatVoiceFromUri({
          uri,
          audioMime,
          speak,
          history: hist,
        });
      } catch (multipartErr) {
        const audioBase64 = await FileSystem.readAsStringAsync(uri, {
          encoding: FileSystem.EncodingType.Base64,
        });
        try {
          return await sendChatVoiceMessage({
            audioBase64,
            audioMime,
            speak,
            history: hist,
          });
        } catch {
          throw multipartErr;
        }
      }
    },
    [finishWebRecording]
  );

  const stopRecordingRaw = useCallback(async (): Promise<{
    blob?: Blob;
    uri?: string;
    mime: string;
  }> => {
    if (isWeb) {
      if (!webRecorderRef.current) {
        throw new Error("Nenhuma gravação ativa. Toque no microfone para gravar.");
      }
      const elapsed = Date.now() - recordingStartedAtRef.current;
      if (elapsed < 900) {
        throw new Error("Fale pelo menos 2 segundos antes de enviar.");
      }
      const { blob, mime } = await finishWebRecording();
      setMicSessionActive(false);
      setIsRecording(false);
      recordingStartedAtRef.current = 0;
      return { blob, mime };
    }

    const rec = recordingRef.current;
    if (!rec) {
      throw new Error("Nenhuma gravação ativa.");
    }
    const elapsed = Date.now() - recordingStartedAtRef.current;
    if (elapsed < 900) {
      throw new Error("Fale pelo menos 2 segundos antes de enviar.");
    }
    setIsRecording(false);
    recordingRef.current = null;
    setMicSessionActive(false);
    const uri = rec.getURI();
    await safeStopNativeRecording(rec);
    const Audio = getExpoAudio();
    if (Audio) {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });
    }
    if (!uri) {
      throw new Error("Gravação vazia.");
    }
    recordingStartedAtRef.current = 0;
    return { uri, mime: mimeFromUri(uri) };
  }, [finishWebRecording]);

  const cancelRecording = useCallback(async () => {
    setMicSessionActive(false);
    setIsRecording(false);
    recordingStartedAtRef.current = 0;
    if (isWeb) {
      const state = webRecorderRef.current;
      if (!state) return;
      webRecorderRef.current = null;
      try {
        state.recorder.stop();
      } catch {
        /* ignore */
      }
      state.stream.getTracks().forEach((track) => track.stop());
      return;
    }

    const rec = recordingRef.current;
    if (!rec) return;
    recordingRef.current = null;
    setMicSessionActive(false);
    setIsRecording(false);
    await safeStopNativeRecording(rec);
  }, []);

  const replayLastText = useCallback(
    async (text: string, voiceId?: string, avatarId?: string) =>
      playReplyAudio({ reply: text }, voiceId, avatarId),
    [playReplyAudio]
  );

  return {
    isRecording,
    micSessionActive,
    isSpeaking,
    audioSpeed,
    setAudioSpeed,
    webMicMode: isWeb ? webMicMode() : ("native" as const),
    isPhoneCall: false,
    isPreparingAudio: false,
    isAssistantThinking: false,
    isUserSpeaking: false,
    activeVoiceMode: "recorder" as const,
    webUsesSpeechToText: false,
    startRecording,
    waitForRecording,
    stopRecordingAndSend,
    stopRecordingRaw,
    cancelRecording,
    playReplyAudio,
    replayLastText,
    stopPlayback,
    unlockWebPlayback: unlockWebAudioPlayback,
  };
}
