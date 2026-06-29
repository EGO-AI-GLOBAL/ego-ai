import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { DailyCareAdventure } from "@/api/types";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  adventure?: DailyCareAdventure;
};

export function MoodAdventureBanner({ colors, adventure }: Props) {
  if (!adventure?.title) return null;
  const progress = Math.min(100, Math.max(0, adventure.progress ?? 0));

  return (
    <View style={[styles.wrap, { backgroundColor: colors.primaryTint, borderColor: colors.primary }]}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: colors.text }]}>🎒 {adventure.title}</Text>
        <Text style={[styles.pct, { color: colors.primary }]}>{progress}%</Text>
      </View>
      <View style={[styles.track, { backgroundColor: colors.border }]}>
        <View style={[styles.fill, { width: `${progress}%`, backgroundColor: colors.primary }]} />
      </View>
      <Text style={[styles.sub, { color: colors.textMuted }]}>{adventure.subtitle}</Text>
      {adventure.can_collect ? (
        <Text style={[styles.hint, { color: colors.primary }]}>
          Toque na missão de aventura abaixo para a recompensa.
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { borderWidth: 1.5, borderRadius: 12, padding: 12, marginBottom: 12 },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  title: { fontSize: 13, fontWeight: "800", flex: 1 },
  pct: { fontSize: 12, fontWeight: "900" },
  track: { height: 8, borderRadius: 4, marginTop: 8, overflow: "hidden" },
  fill: { height: "100%", borderRadius: 4 },
  sub: { fontSize: 12, fontWeight: "600", marginTop: 8, lineHeight: 17 },
  hint: { fontSize: 11, fontWeight: "700", marginTop: 6 },
});
