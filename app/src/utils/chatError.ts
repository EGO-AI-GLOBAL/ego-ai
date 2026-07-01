import type { AccessInfo } from "@/api/types";
import { allowsInAppPlanPurchase } from "@/utils/iosAppStoreBilling";

/** Deixa claro quando o bloqueio é Google Gemini vs limite do plano EGO. */
export function enrichChatError(
  message: string,
  access: AccessInfo | null | undefined
): string {
  const msg = message.trim();
  if (!msg) return msg;
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
