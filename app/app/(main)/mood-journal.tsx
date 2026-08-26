import { router, useFocusEffect } from "expo-router";
import React, { useCallback } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { MoodJournalHistory } from "@/components/moodMonsters/MoodJournalHistory";
import { MoodJournalTodayNote } from "@/components/moodMonsters/MoodJournalTodayNote";
import { ScreenShell } from "@/components/ScreenShell";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";
import {
  buildMoodJournalChatDraft,
  moodJournalTopLabel,
} from "@/utils/moodJournalInsights";
import { queueMonsterChatNotice } from "@/utils/monsterChatNotice";

export default function MoodJournalScreen() {
  const colors = useColors();
  const { data, loading, refreshing, error, refresh, mergeDailyCare } = useDashboard();
  const care = data.daily_care;
  const entries = care?.mood_journal ?? [];

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  const onOpenChat = () => {
    void queueMonsterChatNotice(buildMoodJournalChatDraft(entries)).then(() => {
      router.push("/(main)/chat");
    });
  };

  const insight7 = moodJournalTopLabel(entries, 7);
  const insight30 = moodJournalTopLabel(entries, 30);

  return (
    <ScreenShell
      title="Diário de humor"
      subtitle="Até 6 semanas · nota curta por dia"
      adsAccess={data.access ?? null}
    >
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.primary} />
        }
      >
        {loading && !refreshing ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
        ) : null}
        {error ? <Text style={[styles.error, { color: colors.danger }]}>{error}</Text> : null}

        {!loading || refreshing ? (
          <>
            {entries.length ? (
              <View style={[styles.stats, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
                <Text style={[styles.statsTitle, { color: colors.text }]}>Resumo</Text>
                {insight7 ? (
                  <Text style={[styles.statsLine, { color: colors.textMuted }]}>
                    7 dias: {insight7}
                  </Text>
                ) : null}
                {insight30 && insight30 !== insight7 ? (
                  <Text style={[styles.statsLine, { color: colors.textMuted }]}>
                    30 dias: {insight30}
                  </Text>
                ) : null}
                <Text style={[styles.statsCount, { color: colors.primary }]}>
                  {entries.length} {entries.length === 1 ? "entrada" : "entradas"}
                </Text>
              </View>
            ) : null}

            {care ? (
              <MoodJournalTodayNote
                colors={colors}
                care={care}
                onUpdate={(next) => mergeDailyCare(next)}
              />
            ) : null}

            <MoodJournalHistory colors={colors} entries={entries} />

            {entries.length ? (
              <Pressable
                onPress={onOpenChat}
                style={[styles.chatBtn, { backgroundColor: colors.primary }]}
              >
                <Text style={styles.chatBtnText}>Falar com meu avatar sobre isso</Text>
              </Pressable>
            ) : null}
          </>
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, paddingBottom: 32 },
  error: { marginBottom: 12, fontSize: 14 },
  stats: {
    padding: 12,
    borderRadius: 14,
    borderWidth: 1,
    marginBottom: 12,
  },
  statsTitle: { fontSize: 14, fontWeight: "800" },
  statsLine: { fontSize: 12, fontWeight: "600", marginTop: 4 },
  statsCount: { fontSize: 12, fontWeight: "800", marginTop: 6 },
  chatBtn: {
    marginTop: 16,
    paddingVertical: 14,
    borderRadius: 14,
    alignItems: "center",
  },
  chatBtnText: { color: "#fff", fontSize: 15, fontWeight: "800" },
});
