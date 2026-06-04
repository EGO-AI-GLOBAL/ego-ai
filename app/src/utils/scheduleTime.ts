/** Fuso do aparelho — enviado em cada pedido autenticado para o servidor. */
export function clientTimezonePayload(): {
  timezone: string;
  tz_offset_min: number;
} {
  const tz_offset_min = -new Date().getTimezoneOffset();
  const timezone =
    typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone || ""
      : "";
  return { timezone, tz_offset_min };
}

/** Anexa timezone ao corpo JSON ou FormData (voz, chat, bootstrap). */
export function attachDeviceTimezone(data: unknown): unknown {
  const tz = clientTimezonePayload();
  if (typeof FormData !== "undefined" && data instanceof FormData) {
    if (!data.has("timezone")) data.append("timezone", tz.timezone);
    if (!data.has("tz_offset_min")) {
      data.append("tz_offset_min", String(tz.tz_offset_min));
    }
    return data;
  }
  if (data && typeof data === "object" && !Array.isArray(data)) {
    return { ...(data as Record<string, unknown>), ...tz };
  }
  return data;
}

/** Timestamps da API vêm em UTC; sem 'Z' o JS trata como hora local e mostra +3h (ex.: 9h → 12h). */
export function parseScheduledIso(iso?: string): Date | null {
  if (!iso) return null;
  let s = String(iso).trim();
  if (!s) return null;
  if (s.includes(" ")) s = s.replace(" ", "T");
  const hasTz = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(s);
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s) && !hasTz) {
    s = `${s}Z`;
  }
  const d = new Date(s);
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
