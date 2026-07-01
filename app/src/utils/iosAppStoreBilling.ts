import { Platform } from "react-native";

/**
 * App Store 3.1.3(b): no iOS não vendemos subscrição digital nem abrimos checkout
 * externo (Stripe). Android mantém compra via browser.
 */
export function allowsInAppPlanPurchase(): boolean {
  return Platform.OS !== "ios";
}

/** Menu / CTAs que levam ao ecrã de planos pagos. */
export function showsPlansNavigation(): boolean {
  return Platform.OS !== "ios";
}

export const IOS_PLANS_SCREEN_NOTE =
  "Este app iOS é gratuito com período de teste. Planos pagos não são vendidos aqui. " +
  "Se já tem acesso na sua conta EGO-AI, entre com o mesmo e-mail.";

export const IOS_PLAN_CARD_NOTE = "Indisponível neste app iOS";

export const IOS_TRIAL_END_ALERT =
  "Seu teste grátis terminou. Entre com o mesmo e-mail se já tiver acesso ativo na sua conta.";

export const IOS_DAILY_LIMIT_ALERT =
  "O desabafo usa a mesma cota do chat. Espere até 00:00 para usar de novo.";

export const IOS_CHAT_BLOCKED_PLACEHOLDER =
  "Teste encerrado — entre com uma conta com acesso ativo.";
