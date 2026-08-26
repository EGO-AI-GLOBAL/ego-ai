import { useFocusEffect } from "expo-router";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
} from "react-native";
import { AgendaTabBar, type AgendaTab } from "@/components/agenda/AgendaTabBar";
import { PersonalAgendaManual } from "@/components/agenda/PersonalAgendaManual";
import { SharedAgendaManual } from "@/components/agenda/SharedAgendaManual";
import { ScreenShell } from "@/components/ScreenShell";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";

/** Ecrã fino: só tabs + refresh. Lógica manual em components/agenda/ */
export default function AgendaScreen() {
  const colors = useColors();
  const { session } = useAuth();
  const { data, loading, refreshing, error, refresh, mergeWellnessJourney } = useDashboard();
  const [tab, setTab] = useState<AgendaTab>("personal");

  useEffect(() => {
    if ((data.pending_calendar_invites?.length ?? 0) > 0) {
      setTab("shared");
    }
  }, [data.pending_calendar_invites?.length]);

  const onRefresh = useCallback(
    () => refresh({ skipNotifications: true }),
    [refresh]
  );

  useFocusEffect(
    useCallback(() => {
      if (session) void onRefresh();
    }, [session, onRefresh])
  );

  const subtitle =
    tab === "personal"
      ? "Toque + · escolha data/hora · Marcar compromisso"
      : "Agenda em grupo · abaixo: Entre Nós (você + 1 pessoa)";

  return (
    <ScreenShell title="Agenda" subtitle={subtitle} adsAccess={data.access ?? null}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={refresh}
            tintColor={colors.primary}
          />
        }
      >
        <AgendaTabBar tab={tab} onChange={setTab} colors={colors} />

        {loading && !refreshing ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
        ) : null}

        {error ? (
          <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
        ) : null}

        {!loading || refreshing || Boolean(error) ? (
          tab === "personal" ? (
            <PersonalAgendaManual
              colors={colors}
              reminders={data.reminders}
              habits={data.agenda}
              agendaDrafts={data.agenda_drafts ?? []}
              shoppingOrphans={data.shopping_orphans ?? []}
              onRefresh={onRefresh}
              onWellnessUpdate={mergeWellnessJourney}
              nightDumpNights={data.streak?.night_dump?.current ?? 0}
            />
          ) : (
            <SharedAgendaManual
              colors={colors}
              sharedCalendars={data.shared_calendars ?? []}
              pendingCalendarInvites={data.pending_calendar_invites ?? []}
              agendaDrafts={data.agenda_drafts ?? []}
              currentUserId={session?.user?.id}
              onRefresh={onRefresh}
              onWellnessUpdate={mergeWellnessJourney}
            />
          )
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 20, paddingBottom: 32 },
  error: { fontSize: 14, marginTop: 12 },
});
