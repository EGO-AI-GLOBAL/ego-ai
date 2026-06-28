import { useFocusEffect } from "expo-router";
import React, { useCallback } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { DailyCareChallenge } from "@/components/DailyCareChallenge";
import { ScreenShell } from "@/components/ScreenShell";
import { TrialBanner } from "@/components/TrialBanner";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";

/** Monstrinhos do Humor — check-in, ranking e partilha (WhatsApp, Instagram, TikTok). */
export default function DailyCareScreen() {
  const colors = useColors();
  const { session } = useAuth();
  const { data, loading, refreshing, error, refresh, mergeDailyCare } = useDashboard();
  const userId = data.me?.user_id?.trim() ?? session?.user?.id?.trim() ?? "";

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  return (
    <ScreenShell title="Monstrinhos do Humor" subtitle="1 toque por dia · ranking · Stories">
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
            <TrialBanner colors={colors} access={data.access} journey={data.wellness_journey} />
            <Text style={[styles.lead, { color: colors.textMuted }]}>
              Seu monstrinho vive no jardim — toque no humor de hoje e veja ele reagir.
            </Text>
            <DailyCareChallenge
              colors={colors}
              care={data.daily_care}
              userId={userId}
              onUpdate={(care, journey) => mergeDailyCare(care, journey)}
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
