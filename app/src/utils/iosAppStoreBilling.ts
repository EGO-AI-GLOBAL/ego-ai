import { Platform } from "react-native";

/** Compra via In-App Purchase Apple (iOS). */
export function usesAppleIap(): boolean {
  return Platform.OS === "ios";
}

/** Compra via Google Play Billing (Android). */
export function usesGooglePlayIap(): boolean {
  return Platform.OS === "android";
}

/** Compra dentro do app pela loja (iOS App Store ou Google Play). */
export function usesStoreIap(): boolean {
  return usesAppleIap() || usesGooglePlayIap();
}

/** Compra via Stripe no browser — só web (Android/iOS usam a loja). */
export function usesStripeCheckout(): boolean {
  return Platform.OS !== "ios" && Platform.OS !== "android";
}

/** O utilizador pode subscrever dentro do app (loja) ou via Stripe (web). */
export function allowsInAppPlanPurchase(): boolean {
  return true;
}

/** Menu / CTAs que levam ao ecrã de planos pagos. */
export function showsPlansNavigation(): boolean {
  return true;
}

/** Onde o utilizador cancela a assinatura, conforme a loja. */
export function storeCancelHint(): string {
  if (usesAppleIap()) {
    return "Cancele em Ajustes → Apple ID → Assinaturas até 24h antes do fim do período.";
  }
  if (usesGooglePlayIap()) {
    return "Cancele na Google Play → Assinaturas até 24h antes do fim do período.";
  }
  return "Cancele no portal Stripe para voltar ao grátis.";
}

export const IOS_SUBSCRIPTION_LEGAL =
  "Assinatura renova automaticamente. Cancele em Ajustes → Apple ID → Assinaturas até 24h antes do fim do período. Termos de Uso (EULA) e Privacidade: links abaixo.";

const ANDROID_SUBSCRIPTION_LEGAL =
  "Assinatura renova automaticamente. Cancele na Google Play → Assinaturas até 24h antes do fim do período. Termos de Uso (EULA) e Privacidade: links abaixo.";

/** Texto legal do fluxo de assinatura conforme a loja. */
export function storeSubscriptionLegal(): string {
  return usesGooglePlayIap() ? ANDROID_SUBSCRIPTION_LEGAL : IOS_SUBSCRIPTION_LEGAL;
}

/** Links públicos exigidos pela Guideline 3.1.2(c) no fluxo de assinatura. */
export const IOS_TERMS_OF_USE_URL = "https://egoai.com.br/termos/";
export const IOS_PRIVACY_POLICY_URL = "https://egoai.com.br/privacidade/";

export const IOS_TRIAL_END_ALERT =
  "Seu teste grátis terminou. Assine um plano para continuar.";

export const IOS_DAILY_LIMIT_ALERT =
  "O desabafo usa a mesma cota do chat. Espere até 00:00 ou assine um plano para continuar.";

export const IOS_CHAT_BLOCKED_PLACEHOLDER =
  "Teste encerrado — assine um plano para continuar o chat.";
