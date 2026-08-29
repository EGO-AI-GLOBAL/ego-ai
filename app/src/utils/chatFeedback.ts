import type { DashboardData, SendChatResult } from "@/api/types";

function calendarLabel(data: DashboardData | undefined, calendarId?: string, name?: string): string {
  if (name?.trim()) return name.trim();
  if (!calendarId || !data?.shared_calendars?.length) {
    return data?.shared_calendars?.[0]?.name?.trim() || "Agenda";
  }
  const cal = data.shared_calendars.find((c) => String(c.id) === String(calendarId));
  return cal?.name?.trim() || "Agenda";
}

export function chatShouldSkipNotificationRefresh(result: SendChatResult): boolean {
  if (
    result.shared_events_saved?.length ||
    result.shared_calendars_saved?.length ||
    result.shared_members_saved?.length ||
    result.reminders_saved?.length ||
    result.agenda_saved?.length
  ) {
    return true;
  }
  const notice = chatSavedNotice(result);
  if (notice && /lembrete|agenda|convite/i.test(notice)) {
    return true;
  }
  const reply = (result.reply || "").trim();
  if (
    /convite|convid|adicion/i.test(reply) &&
    /agenda|membro|grupo|e-mail|email/i.test(reply)
  ) {
    return true;
  }
  return false;
}

/** Convite por chat — sem TTS automático (evita crash nativo no Android). */
export function chatMessageLooksLikeInvite(text: string): boolean {
  const raw = (text || "").trim();
  if (!raw) return false;
  if (!/\b(convida|convite|adiciona|adicione|add|inclui|inclua)\b/i.test(raw)) {
    return false;
  }
  return /@[a-z0-9.\-]+\.[a-z]{2,}/i.test(raw);
}

/** @deprecated use chatShouldSkipNotificationRefresh */
export function chatChangedSharedCalendar(result: SendChatResult): boolean {
  return chatShouldSkipNotificationRefresh(result);
}

export function chatSavedNotice(
  result: SendChatResult,
  data?: DashboardData
): string | null {
  const parts: string[] = [];
  for (const ev of result.shared_events_saved || []) {
    const title = ev.title || "Compromisso";
    const cal = calendarLabel(data, ev.calendar_id, ev.calendar_name);
    parts.push(`Agenda «${cal}»: ${title}`);
  }
  for (const cal of result.shared_calendars_saved || []) {
    const name = cal.name || "Agenda";
    parts.push(`Agenda criada: «${name}»`);
  }
  for (const a of result.agenda_saved || []) {
    const hor = String(a.horario || "").slice(0, 5);
    parts.push(`Agenda: ${a.titulo || "Compromisso"} ${hor} (${a.dias_da_semana})`);
  }
  for (const r of result.reminders_saved || []) {
    parts.push(`Lembrete: ${r.title || "Lembrete"}`);
  }
  for (const m of result.shared_members_saved || []) {
    const em = (m.invited_email || "").trim();
    parts.push(em ? `Convite: ${em}` : "Convite na agenda");
  }
  return parts.length ? parts.join(" · ") : null;
}

export function chatWarnings(result: SendChatResult): string | null {
  const addedEmails = new Set(
    (result.shared_members_saved || [])
      .map((m) => (m.invited_email || "").trim().toLowerCase())
      .filter(Boolean)
  );
  const w = (result.warnings || []).filter(Boolean);
  const filtered = w.filter((line) => {
    if (!addedEmails.size) return true;
    const low = line.toLowerCase();
    for (const em of addedEmails) {
      if (low.startsWith(`${em}:`)) return false;
    }
    return true;
  });
  if (result.shared_members_saved?.length && filtered.length === 0) {
    return null;
  }
  if (filtered.length) return filtered.join(" ");
  if (result.shared_members_saved?.length) return null;
  // Não espelhar a bolha do avatar como erro vermelho (modo escuta / redirect agenda).
  return null;
}
