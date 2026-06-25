import type { WellnessJourneyStep } from "@/api/types";

/** Texto «Falta: …» — label da API já traz (como fazer); fallback curto no app. */
const STEP_HINT: Record<string, string> = {
  checkin: "Monstrinhos → toque no emoji de humor",
  chat: "Chat → escreva 1 mensagem",
  voice: "Chat → botão do microfone",
  habit: "Agenda → marque 1 hábito",
  reminder: "Agenda → + Novo compromisso",
  night_dump: "Chat → Desabafo agora",
  draft_confirm: "Agenda → confirme item do desabafo",
  invite: "Agenda → Entre Nós → Convidar pessoa",
};

export function formatWellnessStepPendingLabel(step: WellnessJourneyStep): string {
  const label = (step.label || "").trim();
  if (!label || label.includes("(")) return label;
  const key = (step.key || "").toLowerCase();
  const hint = STEP_HINT[key];
  if (!hint) return label;
  return `${label} (${hint})`;
}

export function formatWellnessPendingLine(steps: WellnessJourneyStep[]): string {
  return steps
    .filter((s) => !s.done)
    .map(formatWellnessStepPendingLabel)
    .join(" · ");
}
