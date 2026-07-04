import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { DailyCareSeasonalEvent } from "@/api/types";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  event?: DailyCareSeasonalEvent | null;
};

/** Banner de evento sazonal no jardim (Fase 10). */
export function SeasonalEventBanner({ colors, event }: Props) {
  if (!event?.active && !event?.title) return null;

  return (
    <View
      style={[
        styles.banner,
        {
          backgroundColor: colors.primaryTint,
          borderColor: colors.primary,
        },
      ]}
    >
      <Text style={[styles.emoji, { color: colors.text }]}>{event.emoji ?? "✨"}</Text>
      <View style={styles.body}>
        <Text style={[styles.title, { color: colors.text }]}>{event.title}</Text>
        <Text style={[styles.tagline, { color: colors.textMuted }]} numberOfLines={2}>
          {event.tagline}
          {event.bonus_seeds ? ` · +${event.bonus_seeds}🌰 no quiz` : ""}
        </Text>
      </View>
      {event.decor_emoji ? (
        <Text style={styles.decor}>{event.decor_emoji}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 14,
    borderWidth: 1,
    padding: 12,
    marginBottom: 12,
    gap: 10,
  },
  emoji: { fontSize: 28 },
  body: { flex: 1 },
  title: { fontSize: 15, fontWeight: "800" },
  tagline: { fontSize: 12, marginTop: 4, lineHeight: 17 },
  decor: { fontSize: 22 },
});
