/** Janela noturna do cliffhanger «Amanhã revelado» (21h–6h hora local). */
export function isNightRevealWindow(now = new Date()): boolean {
  const h = now.getHours();
  return h >= 21 || h < 6;
}

export function amanhaReveladoDraftTitle(itemCount: number): string {
  if (itemCount <= 0) return "Desabafo recebido";
  if (itemCount === 1) return "1 item separado para amanhã";
  return `${itemCount} itens separados para amanhã`;
}

export function amanhaReveladoDraftHint(): string {
  return "Abra pela manhã e toque Agendar — ou veja a prévia agora.";
}
