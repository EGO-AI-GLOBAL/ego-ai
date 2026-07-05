import type { AccessInfo } from "@/api/types";
import { allowsInAppPlanPurchase } from "@/utils/iosAppStoreBilling";

/** Deixa claro quando o bloqueio é Google Gemini vs limite do plano EGO. */
const PLAY_INTERNAL_TEST_URL =
  "https://play.google.com/apps/testing/com.egoai.app";

export function enrichChatError(
  message: string,
  access: AccessInfo | null | undefined
): string {
  const msg = message.trim();
  if (!msg) return msg;
  if (/app não verificado|play store|integridade do app|integrity/i.test(msg)) {
    return (
      `${msg}\n\n` +
      `Testadores Android: instale só pelo link oficial da Play (teste interno):\n` +
      `${PLAY_INTERNAL_TEST_URL}\n\n` +
      `Se já instalou por aí, feche o app, abra de novo e tente «Oi» por texto.`
    );
  }
  if (!/gemini|cota da api google/i.test(msg)) return msg;

  const plan = access?.plan_label || access?.plan_tier || "Essencial";
  if (access?.is_test_total) {
    return (
      `${msg}\n\n` +
      `Plano EGO ${plan} está ativo no app. O bloqueio é a chave Google no servidor ` +
      `(Railway → GOOGLE_API_KEY), não o plano Total. Se você já paga o Google, cole a chave ` +
      `paga no Railway e faça Redeploy.`
    );
  }
  return (
    `${msg}\n\n` +
    `Plano atual no app: ${plan}.` +
    (allowsInAppPlanPurchase()
      ? " Se aparecer «limite mensal de tokens» ou 100% na barra de uso, faça upgrade em Planos."
      : " Se aparecer limite mensal de tokens, aguarde o próximo mês ou entre com uma conta com acesso ativo.")
  );
}
