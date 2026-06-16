export type ChatQuickAction = {
  id: string;
  label: string;
  prompt: string;
};

/** Reservado — barra de atalhos removida do chat; prompts usados só se reativar no futuro. */
export const CHAT_QUICK_ACTIONS: ChatQuickAction[] = [
  {
    id: "agenda",
    label: "Agenda",
    prompt: "Como uso a agenda pessoal e a compartilhada no app?",
  },
  {
    id: "convidar",
    label: "Convidar",
    prompt: "Como adiciono alguém numa agenda compartilhada?",
  },
];

type DayPeriod = "morning" | "afternoon" | "evening" | "night";

export function getContextualQuickActions(
  _period: DayPeriod,
  _lastIntent?: string | null
): ChatQuickAction[] {
  return CHAT_QUICK_ACTIONS;
}

export function getComposerPlaceholder(_period: DayPeriod): string {
  return "Mensagem…";
}
