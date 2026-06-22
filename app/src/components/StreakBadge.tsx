import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { StreakInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";

export function StreakBadge({
  streak,
  colors,
  onSharePress,
}: {
  streak?: StreakInfo;
  colors: AppColors;
  onSharePress?: () => void;
}) {
  const current = streak?.current ?? 0;
  if (current < 1) return null;

  const atRisk = streak?.at_risk && !streak?.active_today;

  const body = (
    <View
      style={[
        styles.wrap,
        {
          backgroundColor: atRisk ? colors.primaryTint : colors.bgCard,
          borderColor: atRisk ? colors.primary : colors.border,
        },
      ]}
    >
      <Text style={styles.flame}>🔥</Text>
      <View style={styles.textCol}>
        <Text style={[styles.count, { color: colors.text }]}>
          {current} {current === 1 ? "dia" : "dias"}
        </Text>
        <Text style={[styles.label, { color: colors.textMuted }]}>
          {atRisk ? "Ofensiva em risco hoje" : "Ofensiva ativa"}
        </Text>
      </View>
      {onSharePress ? (
        <Text style={[styles.share, { color: colors.primary }]}>Partilhar</Text>
      ) : null}
    </View>
  );

  if (!onSharePress) return body;

  return (
    <Pressable
      onPress={onSharePress}
      accessibilityRole="button"
      accessibilityLabel="Partilhar ofensiva"
      style={({ pressed }) => [{ opacity: pressed ? 0.9 : 1 }]}
    >
      {body}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    alignSelf: "center",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
    marginBottom: 8,
  },
  flame: { fontSize: 18 },
  textCol: { flexShrink: 1 },
  count: { fontSize: 14, fontWeight: "800" },
  label: { fontSize: 11, fontWeight: "600" },
  share: { fontSize: 12, fontWeight: "800", marginLeft: 4 },
});
