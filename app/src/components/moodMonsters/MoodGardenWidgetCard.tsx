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
  const goals = care?.daily_goals ?? [];
  const done = goals.filter((g) => g.done).length;
  const total = goals.length || 5;
  const atRisk = Boolean(care?.at_risk);
  const seeds = care?.seeds ?? 0;
  const streak = care?.current ?? 0;

  const remaining = Math.max(0, total - done);

  const subtitle = useMemo(() => {
    if (!care?.question) return "";
    const congrats = care.avatar_congrats?.trim();
    if (congrats) return congrats;
    if (atRisk) {
      if (!care.checked_today) {
        return streak > 0
          ? `Sequência de ${streak} dias em risco — faça check-in hoje`
          : "Check-in pendente — não perca o dia";
      }
      if (remaining > 0) {
        return `Faltam ${remaining} missões · ${streak} dias em risco`;
      }
    }
    if (!care.checked_today) {
      return "1 toque: marque o humor — o monstrinho reage já";
    }
    if (remaining > 0) return `Faltam ${remaining} missões · ${seeds} sementes · ${streak} dias`;
    return `Dia completo · ${streak} dias seguidos`;
  }, [
    care?.question,
    care?.avatar_congrats,
    care?.checked_today,
    atRisk,
    remaining,
    seeds,
    streak,
  ]);

  if (!care?.question) return null;

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
          <Text style={[styles.risk, { color: colors.warning }]}>
            {remaining > 0
              ? `⚠ Faltam ${remaining} missões · streak em risco`
              : "⚠ Sequência em risco hoje"}
          </Text>
        ) : remaining > 0 && care.checked_today ? (
          <Text style={[styles.risk, { color: colors.primary }]}>
            Faltam {remaining} missões hoje
          </Text>
        ) : null}
        {care.checked_today ? (
          <Text style={[styles.widgetHint, { color: colors.textMuted }]}>
            Widget na home: segure o ícone → Widgets → Jardim
          </Text>
        ) : (
          <Text style={[styles.cta, { color: colors.primary }]}>Abrir jardim → humor</Text>
        )}
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
  widgetHint: { fontSize: 10, fontWeight: "600", marginTop: 6, lineHeight: 14 },
  cta: { fontSize: 12, fontWeight: "800", marginTop: 6 },
  pet: { alignItems: "center", justifyContent: "center", width: 64 },
  gardenEmoji: { fontSize: 40 },
});
