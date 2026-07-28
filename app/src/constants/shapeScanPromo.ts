import { Platform } from "react-native";
import * as Linking from "expo-linking";

/** Destino web + lojas ShapeScan (espelho do cross-promo EGO ↔ ShapeScan). */
export const SHAPESCAN_WEB_URL = "https://shapescanapp.com.br";
export const SHAPESCAN_IOS_APP_ID = "6791775092";
export const SHAPESCAN_ANDROID_PACKAGE = "com.shapescan.app";

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

export function shapeScanPromoCopy(): string {
  const day = Math.floor(Date.now() / 86_400_000);
  const i = ((day % SHAPESCAN_CROSS_PROMO_COPIES.length) + SHAPESCAN_CROSS_PROMO_COPIES.length) %
    SHAPESCAN_CROSS_PROMO_COPIES.length;
  return SHAPESCAN_CROSS_PROMO_COPIES[i];
}

/** Abre loja nativa; se falhar, site shapescanapp.com.br. */
export async function openShapeScan(): Promise<void> {
  const primary =
    Platform.OS === "ios"
      ? SHAPESCAN_IOS_STORE_URL
      : Platform.OS === "android"
        ? SHAPESCAN_ANDROID_STORE_URL
        : SHAPESCAN_WEB_URL;
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
