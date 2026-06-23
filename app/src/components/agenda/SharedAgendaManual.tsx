import React, { useMemo } from "react";
import type { PendingCalendarInvite, SharedCalendar } from "@/api/types";
import type { AgendaDraft } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { isEntreNosCalendarName } from "@/utils/entreNos";
import { AgendaDraftsBanner } from "./AgendaDraftsBanner";
import { ClassicSharedAgendaSection } from "./ClassicSharedAgendaSection";
import { EntreNosAgendaSection } from "./EntreNosAgendaSection";
import { PendingCalendarInvitesBanner } from "./PendingCalendarInvitesBanner";

type Props = {
  colors: AppColors;
  sharedCalendars: SharedCalendar[];
  pendingCalendarInvites?: PendingCalendarInvite[];
  agendaDrafts?: AgendaDraft[];
  currentUserId?: string;
  onRefresh: () => Promise<void>;
};

/**
 * Aba Agenda compartilhada: clássica (Família…) em cima + Entre Nós (2 pessoas) em baixo.
 */
export function SharedAgendaManual({
  colors,
  sharedCalendars,
  pendingCalendarInvites = [],
  agendaDrafts = [],
  currentUserId,
  onRefresh,
}: Props) {
  const classicCalendars = useMemo(
    () => sharedCalendars.filter((c) => !isEntreNosCalendarName(String(c.name || ""))),
    [sharedCalendars]
  );

  const entreNosCalendars = useMemo(
    () => sharedCalendars.filter((c) => isEntreNosCalendarName(String(c.name || ""))),
    [sharedCalendars]
  );

  return (
    <>
      <PendingCalendarInvitesBanner
        colors={colors}
        invites={pendingCalendarInvites}
        onRefresh={onRefresh}
      />
      <AgendaDraftsBanner
        colors={colors}
        drafts={agendaDrafts}
        onRefresh={onRefresh}
        familyOnly
      />
      <ClassicSharedAgendaSection
        colors={colors}
        sharedCalendars={classicCalendars}
        currentUserId={currentUserId}
        onRefresh={onRefresh}
      />
      <EntreNosAgendaSection
        colors={colors}
        sharedCalendars={entreNosCalendars}
        currentUserId={currentUserId}
        onRefresh={onRefresh}
      />
    </>
  );
}
