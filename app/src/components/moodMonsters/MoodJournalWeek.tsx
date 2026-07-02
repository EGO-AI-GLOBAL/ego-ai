import { router } from "expo-router";

import React, { useMemo } from "react";

import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import type { DailyCareMoodJournalEntry } from "@/api/types";

import type { AppColors } from "@/theme/colors";

import { moodJournalTopLabel } from "@/utils/moodJournalInsights";



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

  moods?: { key: string; label: string }[];

};



export function MoodJournalWeek({ colors, entries, moods }: Props) {

  const all = entries ?? [];

  const week = useMemo(() => all.slice(0, 7), [all]);



  const insight = useMemo(() => moodJournalTopLabel(all, 7, moods), [all, moods]);



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

      <Pressable

        onPress={() => router.push("/(main)/mood-journal")}

        style={({ pressed }) => [styles.link, { opacity: pressed ? 0.75 : 1 }]}

      >

        <Text style={[styles.linkText, { color: colors.primary }]}>

          Ver histórico completo · {all.length} {all.length === 1 ? "dia" : "dias"}

        </Text>

      </Pressable>

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

  link: { marginTop: 10 },

  linkText: { fontSize: 12, fontWeight: "800" },

});


