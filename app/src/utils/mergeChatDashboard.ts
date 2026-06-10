import type { DashboardData, SendChatResult } from "@/api/types";
import {
  filterVisibleReminders,
  filterVisibleSharedEvents,
} from "@/components/agenda/agendaUtils";

/** Atualiza o painel com o que o chat gravou — sem refresh (evita crash no Android). */
export function mergeChatIntoDashboard(
  data: DashboardData,
  result: SendChatResult
): DashboardData {
  let reminders = [...(data.reminders ?? [])];
  let agenda = [...(data.agenda ?? [])];
  let sharedCalendars = [...(data.shared_calendars ?? [])];

  for (const r of result.reminders_saved ?? []) {
    const id = String(r.id || "");
    if (!id || reminders.some((x) => String(x.id) === id)) continue;
    reminders = [r, ...reminders];
  }

  for (const a of result.agenda_saved ?? []) {
    const id = String(a.id || "");
    if (!id || agenda.some((x) => String(x.id) === id)) continue;
    agenda = [a, ...agenda];
  }

  for (const cal of result.shared_calendars_saved ?? []) {
    const id = String(cal.id || "");
    if (!id) continue;
    const idx = sharedCalendars.findIndex((c) => String(c.id) === id);
    if (idx >= 0) {
      const prev = sharedCalendars[idx];
      const incomingMembers = cal.members;
      sharedCalendars[idx] = {
        ...prev,
        ...cal,
        members:
          incomingMembers?.length ? incomingMembers : prev.members ?? incomingMembers,
        member_count:
          cal.member_count ?? (incomingMembers?.length ? incomingMembers.length : prev.member_count),
        events: cal.events?.length ? cal.events : prev.events,
      };
    } else {
      sharedCalendars = [cal, ...sharedCalendars];
    }
  }

  for (const ev of result.shared_events_saved ?? []) {
    const eid = String(ev.id || "");
    const cid = String(ev.calendar_id || "");
    if (!eid) continue;
    sharedCalendars = sharedCalendars.map((cal) => {
      if (cid && String(cal.id) !== cid) return cal;
      if (!cid && sharedCalendars.length > 1) return cal;
      const events = cal.events ?? [];
      if (events.some((e) => String(e.id) === eid)) return cal;
      return { ...cal, events: [...events, ev] };
    });
  }

  for (const m of result.shared_members_saved ?? []) {
    const mid = String(m.id || "");
    let cid = String(m.calendar_id || "");
    if (!cid && sharedCalendars.length === 1) {
      cid = String(sharedCalendars[0]?.id || "");
    }
    if (!mid && !cid) continue;
    sharedCalendars = sharedCalendars.map((cal) => {
      if (cid && String(cal.id) !== cid) return cal;
      if (!cid && sharedCalendars.length > 1) return cal;
      const members = [...(cal.members ?? [])];
      if (mid && members.some((x) => String(x.id) === mid)) {
        const next = members.map((x) =>
          String(x.id) === mid ? { ...x, ...m } : x
        );
        return { ...cal, members: next, member_count: next.length };
      }
      return {
        ...cal,
        members: [m, ...members],
        member_count: members.length + 1,
      };
    });
  }

  sharedCalendars = sharedCalendars.map((cal) => ({
    ...cal,
    events: filterVisibleSharedEvents(cal.events ?? []),
  }));

  return {
    ...data,
    reminders: filterVisibleReminders(reminders),
    agenda,
    shared_calendars: sharedCalendars,
  };
}

export function chatResultChangedData(result: SendChatResult): boolean {
  return Boolean(
    result.reminders_saved?.length ||
      result.agenda_saved?.length ||
      result.shared_events_saved?.length ||
      result.shared_calendars_saved?.length ||
      result.shared_members_saved?.length
  );
}
