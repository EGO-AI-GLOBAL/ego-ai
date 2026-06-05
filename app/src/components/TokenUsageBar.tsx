import { router } from "expo-router";
import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AccessInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { formatCount, primaryTokenPercent, usageLevel } from "@/utils/usageStats";

type Props = {
  colors: AppColors;
  access: AccessInfo | null;
};

export function TokenUsageBar({ colors, access }: Props) {
  if (!access || access.monthly_tokens_limit <= 0) return null;

  const used = access.monthly_tokens_used ?? 0;
  const limit = access.monthly_tokens_limit ?? 0;
  let pct = primaryTokenPercent(access);
  if (used > 0 && pct === 0) pct = 1;
  const level = usageLevel(pct);
  const fill =
    level === "critical"
      ? colors.danger
      : level === "warn"
        ? colors.warning
        : colors.primary;
  const atCap = used >= limit && limit > 0;
  const blocked = !access.is_test_total && (access.monthly_tokens_ok === false || atCap);
  const planHint = access.plan_label?.trim() || "";
  const fillWidth = `${Math.max(atCap ? 100 : pct, pct > 0 ? 3 : 0)}%`;
  const detail = `${formatCount(used)} / ${formatCount(limit)}`;

  return (
    <Pressable
      onPress={() => router.push("/(main)/usage")}
      style={({ pressed }) => [styles.wrap, { opacity: pressed ? 0.85 : 1 }]}
      accessibilityRole="button"
      accessibilityLabel={
        blocked
          ? `Uso do plano ${pct} por cento. Limite atingido. Abrir detalhes.`
          : `Uso do plano ${pct} por cento. Abrir detalhes.`
      }
    >
      <View style={styles.row}>
        {planHint ? (
          <Text style={[styles.plan, { color: colors.textMuted }]} numberOfLines={1}>
            {planHint}
          </Text>
        ) : null}
        <View style={[styles.track, { backgroundColor: colors.border }]}>
          <View
            style={[styles.fill, { backgroundColor: fill, width: fillWidth }]}
          />
        </View>
        <Text style={[styles.pct, { color: blocked ? colors.danger : colors.text }]}>
          {atCap ? 100 : pct}%
        </Text>
      </View>
      <Text style={[styles.detail, { color: colors.textMuted }]}>{detail}</Text>
      {blocked ? (
        <Text style={[styles.blocked, { color: colors.danger }]}>
          Limite do plano atingido — abra Planos para continuar.
        </Text>
      ) : atCap && access.is_test_total ? (
        <Text style={[styles.blocked, { color: colors.textMuted }]}>
          Conta de teste: 100% exibido, chat continua liberado.
        </Text>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: 6, paddingHorizontal: 2, marginBottom: 2 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  plan: { fontSize: 11, fontWeight: "600", maxWidth: 88 },
  detail: { marginTop: 2, fontSize: 10, textAlign: "center", fontWeight: "600" },
  blocked: { marginTop: 4, fontSize: 11, fontWeight: "600", textAlign: "center" },
  track: {
    flex: 1,
    height: 4,
    borderRadius: 999,
    overflow: "hidden",
  },
  fill: { height: "100%" },
  pct: { fontSize: 13, fontWeight: "800", minWidth: 36, textAlign: "right" },
});
