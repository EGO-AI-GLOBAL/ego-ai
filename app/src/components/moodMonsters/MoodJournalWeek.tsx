import React, { useMemo } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import type { DailyCareMoodJournalEntry } from "@/api/types";
import type { AppColors } from "@/theme/colors";

const WEEKDAY_PT = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

function weekdayLabel(dateIso: string): string {
  const parts = dateIso.split("-").map((x) => parseInt(x, 10));
  if (parts.length < 3 || parts.some((n) => Number.isNaN(n))) {
    return dateIso.slice(5);
  }
  const dt = new Date(parts[0], parts[1] - 1, parts[2]);
  return WEEKDAY_PT[dt.getDay()] ?? "";
}

type Props = {
  colors: AppColors;
  entries?: DailyCareMoodJournalEntry[];
};

export function MoodJournalWeek({ colors, entries }: Props) {
  const week = useMemo(() => (entries ?? []).slice(0, 7), [entries]);

  const insight = useMemo(() => {
    if (!week.length) return "";
    const counts: Record<string, number> = {};
    for (const e of week) {
      const k = (e.label || e.mood || "").trim();
      if (!k) continue;
      counts[k] = (counts[k] ?? 0) + 1;
    }
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
    return top ? `${top[1]}× ${top[0]}` : "";
  }, [week]);

  if (!week.length) return null;

  return (
    <View style={[styles.wrap, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: colors.text }]}>Diário de humor</Text>
        {insight ? (
          <Text style={[styles.hint, { color: colors.textMuted }]}>7 dias · {insight}</Text>
        ) : null}
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
      >
        {week.map((e) => (
          <View key={e.date} style={[styles.chip, { borderColor: colors.border }]}>
            <Text style={styles.emoji}>{e.emoji || "🌱"}</Text>
            <Text style={[styles.day, { color: colors.textMuted }]} numberOfLines={1}>
              {weekdayLabel(e.date)}
            </Text>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginBottom: 12,
    padding: 12,
    borderRadius: 14,
    borderWidth: 1,
  },
  head: { marginBottom: 8 },
  title: { fontSize: 14, fontWeight: "800" },
  hint: { fontSize: 11, fontWeight: "600", marginTop: 2 },
  row: { flexDirection: "row", gap: 8, paddingRight: 4 },
  chip: {
    alignItems: "center",
    minWidth: 52,
    paddingVertical: 8,
    paddingHorizontal: 6,
    borderRadius: 12,
    borderWidth: 1,
  },
  emoji: { fontSize: 26 },
  day: { fontSize: 10, fontWeight: "700", marginTop: 4 },
});
