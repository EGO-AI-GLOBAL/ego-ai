export type ChatQuickAction = {
  id: string;
  label: string;
  prompt: string;
};

export const CHAT_QUICK_ACTIONS: ChatQuickAction[] = [
  {
    id: "marcar",
    label: "Marcar",
    prompt: "Quero marcar um compromisso. Pergunta agenda, título, data e hora.",
  },
  {
    id: "lembrar",
    label: "Lembrar",
    prompt: "Quero um lembrete. Pergunta o quê e quando.",
  },
  {
    id: "convidar",
    label: "Convidar",
    prompt: "Quero convidar alguém na agenda. Pergunta qual agenda e o telefone ou e-mail.",
  },
  {
    id: "resumo",
    label: "Resumo",
    prompt: "Resumo da minha semana em tópicos curtos.",
  },
];
