import { findAvatarInCatalog } from "@/constants/avatarCatalog";
import { AVATAR_IMAGE_FILES, AVATAR_VIDEO_FILES } from "@/constants/avatarAssets";

/** Presets grátis: Luna (f1+vf1) e Leo (m1+vm1). */

export const DEFAULT_PERSONA = { avatar_id: "f1", voice_id: "vf1" } as const;

export type PersonaChoice = { avatar_id: string; voice_id: string };

export type PersonaPresetId = "female" | "male";

export const AVATAR_IMAGES: Record<string, number> = Object.fromEntries(
  Object.entries(AVATAR_IMAGE_FILES).filter(([, v]) => v != null)
) as Record<string, number>;

export const AVATAR_SPEAKING_VIDEOS: Record<string, number> = Object.fromEntries(
  Object.entries(AVATAR_VIDEO_FILES).filter(([, v]) => v != null)
) as Record<string, number>;



export const PERSONA_PRESETS: {

  id: PersonaPresetId;

  /** Nome exibido no chat (troca rápida) */
  shortName: string;

  label: string;

  description: string;

  avatar_id: string;

  voice_id: string;

}[] = [

  {

    id: "female",

    shortName: "Luna",

    label: "Feminina",

    description: "Luna · voz Francisca",

    avatar_id: "f1",

    voice_id: "vf1",

  },

  {

    id: "male",

    shortName: "Leo",

    label: "Masculino",

    description: "Leo · voz António",

    avatar_id: "m1",

    voice_id: "vm1",

  },

];



export function isMaleAvatar(avatarId?: string): boolean {

  const id = (avatarId || "f1").toLowerCase();

  return id.startsWith("m") || id.startsWith("pm");

}



export function avatarImageSource(avatarId?: string): number {
  const id = (avatarId || "f1").toLowerCase();
  if (AVATAR_IMAGES[id]) return AVATAR_IMAGES[id];
  if (id.startsWith("g") || id.startsWith("f")) return AVATAR_IMAGES.f1;
  return AVATAR_IMAGES.m1;
}



export function avatarSpeakingVideoSource(avatarId?: string): number {
  const id = (avatarId || "f1").toLowerCase();
  if (AVATAR_SPEAKING_VIDEOS[id]) return AVATAR_SPEAKING_VIDEOS[id];
  return isMaleAvatar(id) ? AVATAR_SPEAKING_VIDEOS.m1 : AVATAR_SPEAKING_VIDEOS.f1;
}



export function presetFromPersona(avatarId: string, voiceId: string): PersonaPresetId {

  if (isMaleAvatar(avatarId)) return "male";

  const vid = (voiceId || "vf1").toLowerCase();

  if (vid.startsWith("vm") || vid.startsWith("pvm")) return "male";

  return "female";

}



/** Voz TTS coerente com o avatar (Leo → vm1 mesmo se o perfil tiver vf1). */
export function resolveSpeechVoiceId(
  voiceId?: string,
  avatarId?: string
): string {
  return accountPersona({
    avatar_id: avatarId,
    voice_id: voiceId,
  }).voice_id;
}

export function accountPersona(
  persona?: { avatar_id?: string; voice_id?: string } | null
): PersonaChoice {
  const avatar_id = (persona?.avatar_id || DEFAULT_PERSONA.avatar_id).toLowerCase();
  const voice_id = (persona?.voice_id || DEFAULT_PERSONA.voice_id).toLowerCase();
  const entry = findAvatarInCatalog(avatar_id);

  if (entry) {
    const voiceOk =
      (entry.category === "male" && voice_id.startsWith("vm")) ||
      (entry.category === "female" && voice_id.startsWith("vf")) ||
      (entry.category === "neutral" && voice_id.startsWith("vg"));
    return {
      avatar_id: entry.avatar_id,
      voice_id: voiceOk ? voice_id : entry.voice_id,
    };
  }

  if (isMaleAvatar(avatar_id)) {
    return { avatar_id: "m1", voice_id: voice_id.startsWith("vm") ? voice_id : "vm1" };
  }
  return { avatar_id: "f1", voice_id: voice_id.startsWith("vf") ? voice_id : "vf1" };
}


