/** Captura microfone → PCM16 24 kHz (OpenAI Realtime) e reprodução de deltas. */

const TARGET_RATE = 24000;

function floatTo16BitPCM(float32: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(float32.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buffer;
}

function resampleTo24k(input: Float32Array, inputRate: number): Float32Array {
  if (inputRate === TARGET_RATE) return input;
  const ratio = inputRate / TARGET_RATE;
  const outLen = Math.max(1, Math.round(input.length / ratio));
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const src = i * ratio;
    const i0 = Math.floor(src);
    const i1 = Math.min(i0 + 1, input.length - 1);
    const t = src - i0;
    out[i] = input[i0] * (1 - t) + input[i1] * t;
  }
  return out;
}

export function encodePcm16Base64(float32: Float32Array, inputRate: number): string {
  const resampled = resampleTo24k(float32, inputRate);
  const pcm = floatTo16BitPCM(resampled);
  const bytes = new Uint8Array(pcm);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function decodePcm16Base64(b64: string): Float32Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const samples = bytes.length / 2;
  const out = new Float32Array(samples);
  const view = new DataView(bytes.buffer);
  for (let i = 0; i < samples; i++) {
    out[i] = view.getInt16(i * 2, true) / 0x8000;
  }
  return out;
}

export type PcmMicCapture = {
  stop: () => void;
};

export function startPcmMicCapture(
  onChunk: (base64Pcm: string) => void
): Promise<PcmMicCapture> {
  return navigator.mediaDevices
    .getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    })
    .then((stream) => {
    const Ctx = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) throw new Error("AudioContext indisponível neste browser.");
    const ctx = new Ctx({ sampleRate: TARGET_RATE });
    const source = ctx.createMediaStreamSource(stream);
    const processor = ctx.createScriptProcessor(1024, 1, 1);
    const inputRate = ctx.sampleRate;

    processor.onaudioprocess = (ev) => {
      const ch = ev.inputBuffer.getChannelData(0);
      if (!ch.length) return;
      const copy = new Float32Array(ch.length);
      copy.set(ch);
      onChunk(encodePcm16Base64(copy, inputRate));
    };

    source.connect(processor);
    processor.connect(ctx.destination);

    return {
      stop: () => {
        processor.disconnect();
        source.disconnect();
        stream.getTracks().forEach((t) => t.stop());
        void ctx.close();
      },
    };
  });
}

export class RealtimePcmPlayer {
  private ctx: AudioContext;
  private nextTime = 0;

  constructor() {
    const Ctx = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) throw new Error("AudioContext indisponível.");
    this.ctx = new Ctx({ sampleRate: TARGET_RATE });
  }

  async resume(): Promise<void> {
    if (this.ctx.state === "suspended") await this.ctx.resume();
  }

  playDelta(base64: string): void {
    const floats = decodePcm16Base64(base64);
    if (!floats.length) return;
    const buffer = this.ctx.createBuffer(1, floats.length, TARGET_RATE);
    buffer.copyToChannel(floats, 0);
    const src = this.ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(this.ctx.destination);
    const start = Math.max(this.ctx.currentTime, this.nextTime);
    src.start(start);
    this.nextTime = start + buffer.duration;
  }

  async drain(msPadding = 0): Promise<void> {
    const wait = Math.max(0, (this.nextTime - this.ctx.currentTime) * 1000 + msPadding);
    if (wait > 0) {
      await new Promise((r) => setTimeout(r, wait));
    }
  }

  /** Corta áudio da IA quando o utilizador interrompe. */
  flushPlayback(): void {
    this.nextTime = this.ctx.currentTime;
  }

  close(): void {
    void this.ctx.close();
  }
}
