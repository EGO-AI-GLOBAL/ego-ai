import React from "react";
import { StyleSheet, Text, View, type DimensionValue } from "react-native";
import type { WeeklyChallenge } from "@/api/types";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  weekly?: WeeklyChallenge;
};

/** Desafio semanal — 4 dias com 5/5 missões na semana. */
export function CompanionWeeklyBar({ colors, weekly }: Props) {
  if (!weekly) return null;

  const pct = weekly.days_goal > 0 ? weekly.days_done / weekly.days_goal : 0;
  const fillWidth = `${Math.min(100, Math.round(pct * 100))}%` as DimensionValue;

  return (
    <View style={[styles.wrap, { borderColor: colors.border }]}>
      <View style={styles.head}>
        <Text style={[styles.label, { color: colors.primary }]}>DESAFIO DA SEMANA</Text>
        {weekly.complete ? (
          <Text style={[styles.badge, { color: colors.primary }]}>✓</Text>
        ) : (
          <Text style={[styles.count, { color: colors.textMuted }]}>
            {weekly.days_done}/{weekly.days_goal}
          </Text>
        )}
      </View>
      <View style={[styles.track, { backgroundColor: colors.border }]}>
        <View
          style={[
            styles.fill,
            {
              backgroundColor: colors.primary,
              width: fillWidth,
            },
          ]}
        />
      </View>
      <Text style={[styles.msg, { color: colors.textMuted }]} numberOfLines={2}>
        {weekly.message}
      </Text>
      {weekly.complete && weekly.bonus_awarded && weekly.bonus_stars ? (
        <Text style={[styles.bonus, { color: colors.primary }]}>
          +{weekly.bonus_stars} estrelas na loja de cores
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  head: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  label: { fontSize: 10, fontWeight: "900", letterSpacing: 0.4 },
  count: { fontSize: 11, fontWeight: "800" },
  badge: { fontSize: 14, fontWeight: "900" },
  track: {
    height: 5,
    borderRadius: 3,
    overflow: "hidden",
  },
  fill: { height: "100%", borderRadius: 3 },
  msg: { fontSize: 10, lineHeight: 14, marginTop: 6 },
  bonus: { fontSize: 10, lineHeight: 14, marginTop: 4, fontWeight: "800" },
});
