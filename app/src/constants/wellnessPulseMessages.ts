/** Horários dos pulsos de autoajuda (hora local do telemóvel). */
export const WELLNESS_PULSE_HOURS = [8, 12, 16, 20] as const;

export type WellnessPulseHour = (typeof WELLNESS_PULSE_HOURS)[number];

/** Mensagens por faixa horária — rotação diária no agendamento local. */
export const WELLNESS_PULSE_MESSAGES: Record<WellnessPulseHour, readonly string[]> = {
  8: [
    "Respire fundo três vezes. O que você quer cultivar hoje — uma palavra só?",
    "Manhã nova: nomeie uma coisa pequena que já está sob seu controle agora.",
    "Antes da correria: o que seu corpo precisa nos próximos dez minutos?",
    "Gratidão rápida: três coisas simples desta manhã, sem julgar.",
    "Se a cabeça acelerou cedo, pause. Você não precisa resolver o dia inteiro agora.",
    "Intenção do dia: como quer se tratar quando algo der errado?",
    "Um passo só: qual a primeira ação leve que aproxima você do que importa?",
    "Olhe pela janela ou levante-se. Ancore os pés no chão por meio minuto.",
    "Manhã difícil também conta. Você merece começar com gentileza, não com pressa.",
    "O que você diria a um amigo cansado? Diga isso a você em voz baixa.",
    "Hidratação e luz: dois gestos mínimos que o cérebro agradece de manhã.",
    "Liste o que pode esperar até depois do almoço. O resto pode ficar na fila.",
    "Se dormiu mal, ajuste a expectativa — um dia menor ainda é um dia válido.",
    "Pergunta suave: o que seria «bom o suficiente» hoje, sem perfeccionismo?",
    "Antes de abrir redes: três respirações. Você escolhe o ritmo do seu dia.",
    "Reconheça uma vitória de ontem, por menor que seja. Isso também é progresso.",
    "Corpo tenso? Ombros para baixo, mandíbula solta, expire devagar.",
    "Manhã de segunda ou qualquer dia: você não precisa carregar tudo sozinho.",
    "Escreva mentalmente uma frase de apoio. Leve ela no bolso hoje.",
    "O dia começa agora. Um compromisso consigo: uma pausa honesta ao meio-dia.",
  ],
  12: [
    "Meio-dia: pare dez segundos. O que seu corpo está pedindo — água, comida, ar?",
    "Metade do dia. O que já deu certo, mesmo pequeno? Reconheça antes de correr.",
    "Respiração box: inspire 4, segure 4, solte 4. Repita duas vezes.",
    "Almoço sem tela, se puder. Saboreie o primeiro gole ou a primeira garfada.",
    "Carga pesada? Divida a tarde em blocos de uma tarefa só.",
    "Sentiu irritação? Nomeie a emoção sem se criticar. Depois escolha o próximo passo.",
    "Caminhe até a janela ou porta. Mudar o ambiente muda o humor, às vezes.",
    "Pergunte: estou com fome, sono, ou emoção? Atender o básico primeiro ajuda.",
    "Mande um «oi» genuíno para alguém de confiança. Conexão regula o sistema nervoso.",
    "Se a manhã foi dura, a tarde pode ser mais leve. Ajuste o ritmo, não desista.",
    "Solte os ombros. Você está fazendo o que pode com o que tem hoje.",
    "Micro-pausa: feche os olhos, conte cinco sons ao seu redor.",
    "Evite a autocrítica no almoço. Você merece comer em paz.",
    "Uma prioridade para a tarde — só uma. O resto pode esperar.",
    "Lembrete gentil: progresso não é linear. Respire e continue.",
    "Estique braços e costas. O corpo guarda tensão que a mente ignora.",
    "O que você pode delegar, adiar ou dizer não hoje?",
    "Meio-dia é checkpoint, não julgamento. Ajuste a rota se precisar.",
    "Três coisas que você fez bem hoje — sem filtro de tamanho.",
    "Hora de recarregar. Cinco minutos só seus já contam como cuidado.",
  ],
  16: [
    "Tarde: energia baixa? Isso é humano. Um passo pequeno ainda vale.",
    "Antes do fim do expediente, solte o que não é seu para carregar.",
    "Respire pelo nariz, solte pela boca. Três vezes, sem pressa.",
    "O que ficou pendente pode ir para amanhã sem culpa, se for o caso.",
    "Pausa de cinco minutos: água, alongamento ou silêncio — você escolhe.",
    "Se a ansiedade subiu, nomeie cinco coisas que vê e quatro que ouve.",
    "Converse consigo como conversaria com alguém que respeita. Tom gentil.",
    "Tarde longa: o que ainda é realmente importante nas próximas duas horas?",
    "Celebre uma coisa que você persistiu hoje, mesmo cansado.",
    "Separar trabalho e descanso começa com um ritual simples agora.",
    "Corpo pedindo pausa? Honrar isso é produtividade emocional.",
    "Evite decisões grandes no cansaço. Adie com consciência, não com medo.",
    "Ligue para alguém ou mande áudio curto — voz humana acalma.",
    "Reveja a lista: o que pode sair sem drama?",
    "Tarde não precisa ser reta final de corrida. Pode ser chegada suave.",
    "Gratidão da tarde: uma pessoa, um momento, um detalhe.",
    "Se bateu culpa, pergunte: isso é fato ou exigência demais de mim?",
    "Alongue pescoço e punhos. Pequenos cuidados evitam o desgaste grande.",
    "Faltam horas no dia — use-as com o mínimo de autopunição possível.",
    "Feche os olhos trinta segundos. Você não precisa estar «on» o tempo todo.",
  ],
  20: [
    "Noite: como foi o dia, em uma frase honesta e sem julgamento?",
    "Desacelere. O que pode ficar para amanhã sem que o mundo desabe?",
    "Três respirações longas. O dia terminou; você pode soltar o modo alerta.",
    "Gratidão noturna: três coisas do dia, incluindo esforço invisível.",
    "Se a cabeça não para, escreva num papel o que preocupa. Feche o papel.",
    "Trate-se como trataria alguém que teve um dia pesado — com cuidado.",
    "Evite se cobrar «produtividade» agora. Descanso também é necessidade.",
    "O que você aprendeu sobre si hoje, mesmo que tenha sido difícil?",
    "Ritual de fechamento: luz mais baixa, tela menos, corpo mais lento.",
    "Perdoe-se por algo pequeno do dia. Amanhã é outra chance.",
    "Converse no chat se quiser desabafar. Estou aqui, sem pressa.",
    "Liste o que deu certo. O cérebro tende a lembrar só o erro.",
    "Antes de dormir: o que você precisa ouvir de encorajamento?",
    "Soltar o dia não é desistir — é permitir recuperação.",
    "Se não dormiu bem ontem, hoje merece um encerramento gentil.",
    "Respiração 4-7-8 uma vez: inspire 4, segure 7, solte 8.",
    "O que você quer levar para amanhã — e o que quer deixar?",
    "Noite de autocuidado: banho, música suave ou silêncio. Você escolhe.",
    "Reconheça que você apareceu hoje. Isso já é coragem.",
    "Boa noite interior: você fez o que pôde com o que tinha.",
  ],
};

export function pickWellnessPulseBody(hour: WellnessPulseHour, date = new Date()): string {
  const start = new Date(date.getFullYear(), 0, 0);
  const dayOfYear = Math.floor((date.getTime() - start.getTime()) / 86_400_000);
  const bank = WELLNESS_PULSE_MESSAGES[hour];
  const slotIndex = WELLNESS_PULSE_HOURS.indexOf(hour);
  const idx = (dayOfYear * 5 + slotIndex * 11 + date.getFullYear()) % bank.length;
  return bank[idx] ?? bank[0];
}
