import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { DailyCareMoodJournalEntry } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { formatJournalDatePt } from "@/utils/moodJournalInsights";

type Props = {
  colors: AppColors;
  entries: DailyCareMoodJournalEntry[];
};

export function MoodJournalHistory({ colors, entries }: Props) {
  if (!entries.length) {
    return (
      <View style={[styles.empty, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
        <Text style={[styles.emptyTitle, { color: colors.text }]}>Ainda sem entradas</Text>
        <Text style={[styles.emptyHint, { color: colors.textMuted }]}>
          Faça o check-in de humor no jardim — cada dia fica guardado aqui.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.list}>
      {entries.map((e, idx) => (
        <View
          key={`${e.date}-${idx}`}
          style={[styles.row, { borderColor: colors.border, backgroundColor: colors.bgCard }]}
        >
          <Text style={styles.emoji}>{e.emoji || "🌱"}</Text>
          <View style={styles.body}>
            <Text style={[styles.label, { color: colors.text }]}>{e.label || e.mood || "Humor"}</Text>
            <Text style={[styles.date, { color: colors.textMuted }]}>{formatJournalDatePt(e.date)}</Text>
            {e.note?.trim() ? (
              <Text style={[styles.note, { color: colors.textMuted }]} numberOfLines={4}>
                {e.note.trim()}
              </Text>
            ) : null}
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { gap: 8 },
  row: {
    flexDirection: "row",
    alignItems: "flex-start",
    padding: 12,
    borderRadius: 14,
    borderWidth: 1,
  },
  emoji: { fontSize: 32, marginRight: 12 },
  body: { flex: 1 },
  label: { fontSize: 15, fontWeight: "800" },
  date: { fontSize: 12, fontWeight: "600", marginTop: 2 },
  note: { fontSize: 13, lineHeight: 18, marginTop: 6 },
  empty: {
    padding: 20,
    borderRadius: 14,
    borderWidth: 1,
    alignItems: "center",
  },
  emptyTitle: { fontSize: 16, fontWeight: "800" },
  emptyHint: { fontSize: 13, lineHeight: 19, marginTop: 8, textAlign: "center" },
});
