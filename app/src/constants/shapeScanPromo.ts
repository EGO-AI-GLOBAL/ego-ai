import { Platform } from "react-native";
import * as Linking from "expo-linking";

/** Destino web + lojas ShapeScan (espelho cross-promo EGO ↔ ShapeScan). */
export const SHAPESCAN_WEB_URL = "https://shapescanapp.com.br";
export const SHAPESCAN_IOS_APP_ID = "6791775092";
export const SHAPESCAN_ANDROID_PACKAGE = "com.shapescan.app";

/** Links canónicos ShapeScan (espelho do free ShapeScan → EGO). */
export const SHAPESCAN_BAIXAR_ANDROID_URL = "https://shapescanapp.com.br/baixar-android";
export const SHAPESCAN_BAIXAR_IOS_URL = "https://shapescanapp.com.br/baixar-ios";

export const SHAPESCAN_IOS_STORE_URL = `https://apps.apple.com/app/id${SHAPESCAN_IOS_APP_ID}`;
export const SHAPESCAN_ANDROID_STORE_URL = `https://play.google.com/store/apps/details?id=${SHAPESCAN_ANDROID_PACKAGE}`;

/**
 * Copy PT · max ~80 chars · EGO (mente) → ShapeScan (corpo).
 * Só utilizador FREE (Essential); Premium nunca vê.
 */
export const SHAPESCAN_CROSS_PROMO_COPIES = [
  "🧠→💪 Ansiedade baixa com movimento. Treino + dieta por voz no ShapeScan. Grátis!",
  "Estresse no peito? O corpo ajuda a mente. Monta o treino no ShapeScan. Baixa já.",
  "😌 Ansiedade? Treinar ajuda. ShapeScan monta treino por voz. Grátis!",
] as const;

export const SHAPESCAN_BODY_NUDGE_TITLE = "Mente ok. E o corpo?";
export const SHAPESCAN_BODY_NUDGE_CTA = "Abrir ShapeScan";

export function shapeScanPromoCopy(): string {
  const day = Math.floor(Date.now() / 86_400_000);
  const i =
    ((day % SHAPESCAN_CROSS_PROMO_COPIES.length) + SHAPESCAN_CROSS_PROMO_COPIES.length) %
    SHAPESCAN_CROSS_PROMO_COPIES.length;
  return SHAPESCAN_CROSS_PROMO_COPIES[i];
}

/** URL de download por plataforma (card / CTA). */
export function shapeScanBaixarUrl(): string {
  if (Platform.OS === "ios") return SHAPESCAN_BAIXAR_IOS_URL;
  if (Platform.OS === "android") return SHAPESCAN_BAIXAR_ANDROID_URL;
  return SHAPESCAN_WEB_URL;
}

/** Abre baixar-android / baixar-ios; fallback site. */
export async function openShapeScan(): Promise<void> {
  const primary = shapeScanBaixarUrl();
  try {
    await Linking.openURL(primary);
  } catch {
    try {
      await Linking.openURL(SHAPESCAN_WEB_URL);
    } catch {
      /* ignore */
    }
  }
}
