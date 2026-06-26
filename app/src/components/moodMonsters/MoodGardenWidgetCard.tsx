import { router } from "expo-router";
import React, { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { MoodMonsterIllustration } from "./MoodMonsterIllustration";

type Props = {
  colors: AppColors;
  care: DailyCareInfo | null | undefined;
};

export function MoodGardenWidgetCard({ colors, care }: Props) {
  if (!care?.question) return null;

  const goals = care.daily_goals ?? [];
  const done = goals.filter((g) => g.done).length;
  const total = goals.length || 5;
  const atRisk = Boolean(care.at_risk);
  const seeds = care.seeds ?? 0;
  const streak = care.current ?? 0;

  const subtitle = useMemo(() => {
    if (!care.checked_today) return "Toque para registrar humor e cuidar do pet";
    if (done < total) return `${done}/${total} missões hoje · ${seeds} sementes`;
    return `Dia completo · ${streak} dias seguidos`;
  }, [care.checked_today, done, total, seeds, streak]);

  return (
    <Pressable
      onPress={() => router.push("/(main)/daily-care")}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: colors.bgCard,
          borderColor: atRisk ? colors.warning : colors.border,
          opacity: pressed ? 0.92 : 1,
        },
      ]}
      accessibilityRole="button"
      accessibilityLabel="Jardim dos Monstrinhos"
    >
      <View style={styles.left}>
        <Text style={[styles.title, { color: colors.text }]}>Jardim dos Monstrinhos</Text>
        <Text style={[styles.sub, { color: colors.textMuted }]} numberOfLines={2}>
          {subtitle}
        </Text>
        {atRisk ? (
          <Text style={[styles.risk, { color: colors.warning }]}>Sequência em risco hoje</Text>
        ) : null}
      </View>
      <View style={styles.pet}>
        {care.checked_today && care.last_mood ? (
          <MoodMonsterIllustration moodKey={care.last_mood} size={56} />
        ) : (
          <Text style={styles.gardenEmoji}>{care.garden_emoji ?? "🌱"}</Text>
        )}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: 16,
    marginBottom: 10,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 14,
    borderWidth: 1,
  },
  left: { flex: 1, paddingRight: 8 },
  title: { fontSize: 15, fontWeight: "700" },
  sub: { fontSize: 13, marginTop: 4, lineHeight: 18 },
  risk: { fontSize: 12, fontWeight: "600", marginTop: 6 },
  pet: { alignItems: "center", justifyContent: "center", width: 64 },
  gardenEmoji: { fontSize: 40 },
});
