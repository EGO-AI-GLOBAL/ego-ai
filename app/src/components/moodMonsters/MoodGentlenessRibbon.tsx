import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { DailyCareGentleness } from "@/api/types";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  gentleness?: DailyCareGentleness | null;
};

/** Faixa «Jardim da Gentileza» — espelho 7d + sequência sobrevivência PAUSA. */
export function MoodGentlenessRibbon({ colors, gentleness }: Props) {
  if (!gentleness) return null;

  const survival = gentleness.survival_streak_current ?? 0;
  const show =
    gentleness.gentle_mode ||
    gentleness.night_garden ||
    gentleness.sunday_garden ||
    survival > 0 ||
    (gentleness.calm_streak_current ?? 0) > 0 ||
    Boolean(gentleness.mirror_line?.trim());

  if (!show) return null;

  const tagline =
    gentleness.tagline?.trim() ||
    (gentleness.sunday_garden
      ? "Domingo no jardim — sem pressa"
      : gentleness.night_garden
        ? "Jardim noturno — descanse sem pressa"
        : "Jardim da Gentileza");

  const streakLine =
    gentleness.survival_streak_line?.trim() ||
    (survival > 0
      ? `${survival} ${survival === 1 ? "dia difícil" : "dias difíceis"} com PAUSA`
      : "");

  const emoji = gentleness.sunday_garden ? "☀️" : gentleness.night_garden ? "🌙" : "💜";

  return (
    <View
      style={[
        styles.wrap,
        {
          borderColor: gentleness.gentle_mode ? colors.primary : colors.border,
          backgroundColor: gentleness.gentle_mode ? colors.primaryTint : colors.bg,
        },
      ]}
    >
      <Text style={[styles.badge, { color: colors.primary }]} numberOfLines={2}>
        {emoji} {tagline.toUpperCase()}
      </Text>
      {streakLine ? (
        <Text style={[styles.calmStreak, { color: colors.textMuted }]} numberOfLines={2}>
          ✨ {streakLine}
        </Text>
      ) : null}
      {gentleness.mirror_line ? (
        <Text style={[styles.mirror, { color: colors.text }]}>{gentleness.mirror_line}</Text>
      ) : gentleness.gentle_mode ? (
        <Text style={[styles.mirror, { color: colors.textMuted }]}>
          Missões leves hoje — sem culpa, sem pressa.
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: 14,
    borderWidth: 1.5,
    padding: 12,
    marginBottom: 10,
    alignSelf: "stretch",
  },
  badge: {
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 0.4,
    lineHeight: 14,
    flexShrink: 1,
  },
  calmStreak: {
    marginTop: 6,
    fontSize: 11,
    fontWeight: "700",
    lineHeight: 15,
    flexShrink: 1,
  },
  mirror: { marginTop: 8, fontSize: 13, fontWeight: "600", lineHeight: 18 },
});
