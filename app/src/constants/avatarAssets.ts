/**
 * Registo de ficheiros de avatar no bundle.
 * Quando adicionar PNG/MP4 em app/assets/, descomente a linha correspondente.
 */
export const AVATAR_IMAGE_FILES: Record<string, number | undefined> = {
  f1: require("../../assets/avatar-f1.png"),
  m1: require("../../assets/avatar-m1.png"),
  f2: require("../../assets/avatar-f2.png"),
  f3: require("../../assets/avatar-f3.png"),
  f4: require("../../assets/avatar-f4.png"),
  f5: require("../../assets/avatar-f5.png"),
  m2: require("../../assets/avatar-m2.png"),
  m3: require("../../assets/avatar-m3.png"),
  m4: require("../../assets/avatar-m4.png"),
  m5: require("../../assets/avatar-m5.png"),
  g1: require("../../assets/avatar-g1.png"),
  g2: require("../../assets/avatar-g2.png"),
};

export const AVATAR_VIDEO_FILES: Record<string, number | undefined> = {
  f1: require("../../assets/avatar-f1-speaking.mp4"),
  m1: require("../../assets/avatar-m1-speaking.mp4"),
  f2: require("../../assets/avatar-f2-speaking.mp4"),
  f3: require("../../assets/avatar-f3-speaking.mp4"),
  m2: require("../../assets/avatar-m2-speaking.mp4"),
  m3: require("../../assets/avatar-m3-speaking.mp4"),
  f4: require("../../assets/avatar-f4-speaking.mp4"),
  m4: require("../../assets/avatar-m4-speaking.mp4"),
  g1: require("../../assets/avatar-g1-speaking.mp4"),
  f5: require("../../assets/avatar-f5-speaking.mp4"),
  m5: require("../../assets/avatar-m5-speaking.mp4"),
  g2: require("../../assets/avatar-g2-speaking.mp4"),
};

export function hasAvatarImage(avatarId: string): boolean {
  return Boolean(AVATAR_IMAGE_FILES[avatarId.toLowerCase()]);
}

export function hasAvatarVideo(avatarId: string): boolean {
  return Boolean(AVATAR_VIDEO_FILES[avatarId.toLowerCase()]);
}
