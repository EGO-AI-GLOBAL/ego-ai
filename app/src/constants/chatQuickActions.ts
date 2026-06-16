export type ChatQuickAction = {
  id: string;
  label: string;
  prompt: string;
};

const MORNING: ChatQuickAction[] = [
  {
    id: "hoje",
    label: "O que tenho hoje?",
    prompt: "Resumo da minha agenda de hoje em tópicos curtos.",
  },
  {
    id: "marcar",
    label: "Marcar reunião",
    prompt: "Quero marcar um compromisso. Pergunta agenda, título, data e hora.",
  },
  {
    id: "resumo-manha",
    label: "Briefing",
    prompt: "Briefing de café: o que preciso saber para começar bem o dia?",
  },
];

const AFTERNOON: ChatQuickAction[] = [
  {
    id: "tarde",
    label: "Minha tarde",
    prompt: "O que ainda tenho pendente hoje à tarde?",
  },
  {
    id: "marcar",
    label: "Marcar algo",
    prompt: "Quero marcar um compromisso. Pergunta agenda, título, data e hora.",
  },
  {
    id: "feito",
    label: "Já fiz",
    prompt: "Quero marcar um compromisso de hoje como feito ou atualizar a agenda.",
  },
];

const EVENING: ChatQuickAction[] = [
  {
    id: "dia",
    label: "Como foi o dia?",
    prompt: "Como foi meu dia? Resumo breve e o que ficou pendente.",
  },
  {
    id: "amanha",
    label: "Anotar amanhã",
    prompt: "Quero anotar compromissos e lembretes para amanhã.",
  },
  {
    id: "descarregar",
    label: "Descarregar",
    prompt: "Ajude-me a tirar os planos da cabeça antes de dormir — o que tenho para amanhã?",
  },
];

const NIGHT: ChatQuickAction[] = [
  {
    id: "amanha",
    label: "Amanhã",
    prompt: "O que tenho marcado para amanhã?",
  },
  {
    id: "lembrar",
    label: "Lembrar",
    prompt: "Quero um lembrete. Pergunta o quê e quando.",
  },
];

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

type DayPeriod = "morning" | "afternoon" | "evening" | "night";

function periodActions(period: DayPeriod): ChatQuickAction[] {
  switch (period) {
    case "morning":
      return MORNING;
    case "afternoon":
      return AFTERNOON;
    case "evening":
      return EVENING;
    default:
      return NIGHT;
  }
}

export function getContextualQuickActions(
  period: DayPeriod,
  lastIntent?: string | null
): ChatQuickAction[] {
  const base = periodActions(period);
  const intent = lastIntent?.trim();
  if (!intent || intent.length < 4) {
    return base.length ? base : CHAT_QUICK_ACTIONS;
  }
  const repeat: ChatQuickAction = {
    id: "repeat",
    label: "De novo",
    prompt: intent,
  };
  return [repeat, ...base].slice(0, 4);
}

export function getComposerPlaceholder(period: DayPeriod): string {
  switch (period) {
    case "morning":
      return "Fale o que tem hoje…";
    case "afternoon":
      return "Como está sua tarde?";
    case "evening":
      return "O que tirar da cabeça antes de dormir?";
    default:
      return "Mensagem…";
  }
}
