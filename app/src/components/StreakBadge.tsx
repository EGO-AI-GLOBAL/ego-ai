import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { StreakInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";

export function StreakBadge({
  streak,
  colors,
}: {
  streak?: StreakInfo;
  colors: AppColors;
}) {
  const current = streak?.current ?? 0;
  if (current < 1) return null;

  const atRisk = streak?.at_risk && !streak?.active_today;

  return (
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
      <View>
        <Text style={[styles.count, { color: colors.text }]}>
          {current} {current === 1 ? "dia" : "dias"}
        </Text>
        <Text style={[styles.label, { color: colors.textMuted }]}>
          {atRisk ? "Ofensiva em risco hoje" : "Ofensiva ativa"}
        </Text>
      </View>
    </View>
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
  count: { fontSize: 14, fontWeight: "800" },
  label: { fontSize: 11, fontWeight: "600" },
});
