/** Entre Nós: até 10 grupos · cada um = você + 1 pessoa. */
export const ENTRE_NOS_MAX_MEMBERS = 2;
export const ENTRE_NOS_MAX_CALENDARS = 10;

/** Chave estável para comparar nomes (acentos, espaços e pontuação ignorados). */
export function calendarNameKey(name: string): string {
  return (name || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]/g, "");
}

export function isEntreNosCalendarName(name: string): boolean {
  const key = calendarNameKey(name);
  if (!key) return false;
  /** Só grupos «Entre Nós · …» — Família/trabalho ficam na agenda compartilhada clássica. */
  return key === "entrenos" || key.startsWith("entrenos");
}

/** Nome do grupo escolhido → «Entre Nós · Maria». */
export function normalizeEntreNosGroupName(raw: string): string {
  const t = raw.trim();
  if (!t) return "Entre Nós";
  if (isEntreNosCalendarName(t)) return t.slice(0, 120);
  const prefix = "Entre Nós · ";
  const rest = t.slice(0, Math.max(0, 120 - prefix.length));
  return rest ? `${prefix}${rest}` : "Entre Nós";
}

/** Criador + 1 pessoa neste grupo. */
export function entreNosPartnerSlotFull(memberCount: number): boolean {
  return memberCount >= ENTRE_NOS_MAX_MEMBERS;
}

export function canCreateMoreEntreNos(ownedEntreNosCount: number): boolean {
  return ownedEntreNosCount < ENTRE_NOS_MAX_CALENDARS;
}
