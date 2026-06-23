import { useFocusEffect } from "expo-router";
import React, { useCallback } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
} from "react-native";
import { ScreenShell } from "@/components/ScreenShell";
import { WellnessJourneyCard } from "@/components/WellnessJourneyCard";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";

/** EGO de Bolso — níveis longos de bem-estar no app. */
export default function WellnessJourneyScreen() {
  const colors = useColors();
  const { data, loading, refreshing, error, refresh, mergeWellnessJourney } = useDashboard();

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  return (
    <ScreenShell title="EGO de Bolso" subtitle="Níveis de bem-estar no seu ritmo">
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.primary} />
        }
      >
        {loading && !refreshing ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
        ) : null}
        {error ? (
          <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
        ) : null}
        {!loading || refreshing ? (
          <>
            <Text style={[styles.lead, { color: colors.textMuted }]}>
              Use o chat, a agenda e o desabafo para evoluir seu EGO de Bolso. Cada nível tem uma
              tarefa clara.
            </Text>
            <WellnessJourneyCard
              colors={colors}
              journey={data.wellness_journey}
              onJourneyUpdate={mergeWellnessJourney}
            />
          </>
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, paddingBottom: 32 },
  lead: { fontSize: 14, lineHeight: 20, marginBottom: 12 },
  error: { marginBottom: 12, fontSize: 14 },
});
