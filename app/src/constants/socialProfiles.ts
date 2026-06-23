import { Linking, Platform } from "react-native";
import Constants from "expo-constants";

/** Handles oficiais — alinhar com marketing/brand/config.json */
const DEFAULT_INSTAGRAM = "egoai__seu_amigo_no_bolso";
const DEFAULT_TIKTOK = "egoai.seuamigonobolso";

export type SocialProfiles = {
  instagramHandle: string;
  instagramUrl: string;
  instagramMention: string;
  tiktokHandle: string;
  tiktokUrl: string;
  tiktokMention: string;
};

function cleanHandle(raw: string): string {
  return raw.replace(/^@+/, "").trim();
}

export function getSocialProfiles(): SocialProfiles {
  const extra = Constants.expoConfig?.extra ?? {};
  const ig = cleanHandle(
    (process.env.EXPO_PUBLIC_INSTAGRAM_HANDLE as string) ||
      (extra.instagramHandle as string) ||
      DEFAULT_INSTAGRAM
  );
  const tt = cleanHandle(
    (process.env.EXPO_PUBLIC_TIKTOK_HANDLE as string) ||
      (extra.tiktokHandle as string) ||
      DEFAULT_TIKTOK
  );
  return {
    instagramHandle: ig,
    instagramUrl: `https://www.instagram.com/${ig}/`,
    instagramMention: `@${ig}`,
    tiktokHandle: tt,
    tiktokUrl: `https://www.tiktok.com/@${tt}`,
    tiktokMention: `@${tt}`,
  };
}

/** Bloco para legenda — links clicáveis para os perfis oficiais. */
export function buildSocialFollowBlock(): string {
  const s = getSocialProfiles();
  return (
    `Siga a gente:\n` +
    `📸 Instagram: ${s.instagramMention}\n` +
    `${s.instagramUrl}\n` +
    `🎵 TikTok: ${s.tiktokMention}\n` +
    `${s.tiktokUrl}`
  );
}

/** Uma linha curta para cartões de partilha. */
export function socialCardFooter(): string {
  const s = getSocialProfiles();
  return `${s.instagramMention} · ${s.tiktokMention}`;
}

export async function openInstagramProfile(): Promise<void> {
  const s = getSocialProfiles();
  const appUrl = `instagram://user?username=${encodeURIComponent(s.instagramHandle)}`;
  try {
    if (Platform.OS !== "web") {
      const can = await Linking.canOpenURL(appUrl);
      if (can) {
        await Linking.openURL(appUrl);
        return;
      }
    }
  } catch {
    /* fallback web */
  }
  await Linking.openURL(s.instagramUrl);
}

export async function openTikTokProfile(): Promise<void> {
  const s = getSocialProfiles();
  try {
    await Linking.openURL(s.tiktokUrl);
  } catch {
    /* ignore */
  }
}

/** Dica após partilhar — adesivo @ no Story não vem automático do app. */
export const STORIES_POST_TIP =
  "No Instagram: depois de publicar, edite o Story e adicione o adesivo «Menção» com @egoai__seu_amigo_no_bolso — assim quem tocar vai ao nosso perfil.";
