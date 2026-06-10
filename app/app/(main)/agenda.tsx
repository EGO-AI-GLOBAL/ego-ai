import { useFocusEffect, useRouter } from "expo-router";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
} from "react-native";
import { AgendaTabBar, type AgendaTab } from "@/components/agenda/AgendaTabBar";
import { ManualOrChatHint } from "@/components/agenda/ManualOrChatHint";
import { PersonalAgendaManual } from "@/components/agenda/PersonalAgendaManual";
import { SharedAgendaManual } from "@/components/agenda/SharedAgendaManual";
import { ScreenShell } from "@/components/ScreenShell";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";

/** Ecrã fino: só tabs + refresh. Lógica manual em components/agenda/ */
export default function AgendaScreen() {
  const colors = useColors();
  const router = useRouter();
  const { session } = useAuth();
  const { data, loading, refreshing, error, refresh } = useDashboard();
  const [tab, setTab] = useState<AgendaTab>("personal");

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
      ? "Manual ou avatar · compromissos marcados · Apagar"
      : "Manual ou avatar · compromissos na lista · Apagar";

  return (
    <ScreenShell title="Agenda" subtitle={subtitle}>
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
        <ManualOrChatHint colors={colors} onOpenChat={() => router.push("/(main)/chat")} />

        {loading && !refreshing ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
        ) : null}

        {error ? (
          <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
        ) : null}

        {!loading && !error ? (
          tab === "personal" ? (
            <PersonalAgendaManual
              colors={colors}
              reminders={data.reminders}
              habits={data.agenda}
              onRefresh={onRefresh}
            />
          ) : (
            <SharedAgendaManual
              colors={colors}
              sharedCalendars={data.shared_calendars ?? []}
              currentUserId={session?.user?.id}
              onRefresh={onRefresh}
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
