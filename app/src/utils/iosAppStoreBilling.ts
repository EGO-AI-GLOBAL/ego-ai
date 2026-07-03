import { Platform } from "react-native";

/** Compra via Stripe no browser (Android / web). */
export function usesStripeCheckout(): boolean {
  return Platform.OS !== "ios";
}

/** Compra via In-App Purchase (iOS). */
export function usesAppleIap(): boolean {
  return Platform.OS === "ios";
}

/** O utilizador pode subscrever dentro do app (IAP iOS ou Stripe Android). */
export function allowsInAppPlanPurchase(): boolean {
  return true;
}

/** Menu / CTAs que levam ao ecrã de planos pagos. */
export function showsPlansNavigation(): boolean {
  return true;
}

export const IOS_SUBSCRIPTION_LEGAL =
  "Assinatura renova automaticamente. Cancele em Ajustes → Apple ID → Assinaturas até 24h antes do fim do período.";

export const IOS_TRIAL_END_ALERT =
  "Seu teste grátis terminou. Assine um plano para continuar.";

export const IOS_DAILY_LIMIT_ALERT =
  "O desabafo usa a mesma cota do chat. Espere até 00:00 ou assine um plano para continuar.";

export const IOS_CHAT_BLOCKED_PLACEHOLDER =
  "Teste encerrado — assine um plano para continuar o chat.";
