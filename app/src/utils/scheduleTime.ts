/** Timestamps da API vêm em UTC; sem 'Z' o JS trata como hora local e mostra +3h (ex.: 9h → 12h). */
export function parseScheduledIso(iso?: string): Date | null {
  if (!iso) return null;
  let s = String(iso).trim();
  if (!s) return null;
  if (s.includes(" ")) s = s.replace(" ", "T");
  const hasTz = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(s);
  // Sem offset: tratar como hora local do aparelho (evita deslocar o dia em agendas de grupo).
  const d = hasTz ? new Date(s) : new Date(s.replace(" ", "T"));
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatScheduledLocal(iso?: string, locale = "pt-BR"): string {
  const d = parseScheduledIso(iso);
  if (!d) return iso ? String(iso).slice(0, 16).replace("T", " ") : "—";
  return d.toLocaleString(locale, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
