export type AudioPlaybackSpeed = 1 | 1.5 | 2;

/** Velocidades aceleradas nos planos pagos (1x é o padrão, sem botão). */
export const AUDIO_SPEED_OPTIONS_PAID: AudioPlaybackSpeed[] = [1.5, 2];

/** Legado / testes locais. */
export const AUDIO_SPEED_OPTIONS: AudioPlaybackSpeed[] = [1, 1.5];

export const AUDIO_SPEED_OPTIONS_ALL: AudioPlaybackSpeed[] = [1, 1.5, 2];

export function formatAudioSpeed(speed: AudioPlaybackSpeed): string {
  return speed === 1 ? "1x" : `${speed}x`;
}
