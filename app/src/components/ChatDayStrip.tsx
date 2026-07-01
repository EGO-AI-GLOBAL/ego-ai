import { router } from "expo-router";
import React from "react";
import { Pressable, StyleSheet, Text, View, type DimensionValue } from "react-native";
import type { AccessInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { allowsInAppPlanPurchase } from "@/utils/iosAppStoreBilling";
import { primaryTokenPercent, usageLevel } from "@/utils/usageStats";
import type { DayProgress } from "@/utils/dayProgress";
import { periodGreeting } from "@/utils/dayProgress";

type Props = {
  colors: AppColors;
  progress: DayProgress;
  access: AccessInfo | null;
  assistantName: string;
  displayName?: string;
  onPressNext?: () => void;
};

function EnergyBar({ colors, access }: { colors: AppColors; access: AccessInfo | null }) {
  if (!access || access.monthly_tokens_limit <= 0) return null;

  const used = access.monthly_tokens_used ?? 0;
  const limit = access.monthly_tokens_limit ?? 0;
  let pct = primaryTokenPercent(access);
  if (used > 0 && pct === 0) pct = 1;
  const level = usageLevel(pct);
  const fillColor =
    level === "critical"
      ? colors.danger
      : level === "warn"
        ? colors.warning
        : colors.success;
  const atCap = used >= limit && limit > 0;
  const blocked = !access.is_test_total && (access.monthly_tokens_ok === false || atCap);
  const fillWidth = `${Math.max(atCap ? 100 : pct, pct > 0 ? 4 : 0)}%` as DimensionValue;
  const low = pct >= 80 && !access.is_test_total;
  const onEnergyPress = allowsInAppPlanPurchase()
    ? () => router.push("/(main)/plans")
    : () => router.push("/(main)/usage");

  return (
    <Pressable
      onPress={onEnergyPress}
      style={({ pressed }) => [styles.energyRow, { opacity: pressed ? 0.88 : 1 }]}
      accessibilityRole="button"
      accessibilityLabel={`Energia do plano ${atCap ? 100 : pct} por cento`}
    >
      <Text style={[styles.energyLabel, { color: colors.textMuted }]}>Energia</Text>
      <View style={[styles.energyTrack, { backgroundColor: colors.border }]}>
        <View style={[styles.energyFill, { backgroundColor: fillColor, width: fillWidth }]} />
      </View>
      {low || blocked ? (
        <Text style={[styles.recharge, { color: blocked ? colors.danger : colors.primary }]}>
          {allowsInAppPlanPurchase() ? "Recarregar" : "Ver uso"}
        </Text>
      ) : (
        <Text style={[styles.energyPct, { color: colors.textMuted }]}>{atCap ? 100 : pct}%</Text>
      )}
    </Pressable>
  );
}

export function ChatDayStrip({
  colors,
  progress,
  access,
  assistantName,
  displayName,
  onPressNext,
}: Props) {
  const greeting = periodGreeting(progress.period, displayName);
  const { total, done, nextItem, emptyHint } = progress;
  const hasProgress = total > 0;
  const ratio = hasProgress ? done / total : 0;
  const progressLabel = hasProgress
    ? `${done} de ${total} compromisso${total === 1 ? "" : "s"} hoje`
    : emptyHint;

  return (
    <View
      style={[
        styles.wrap,
        { backgroundColor: colors.bgCard, borderColor: colors.border },
      ]}
    >
      <Text style={[styles.greeting, { color: colors.text }]}>
        {greeting}
        <Text style={{ color: colors.textMuted }}> · {assistantName}</Text>
      </Text>

      <View style={styles.progressRow}>
        <View style={[styles.progressTrack, { backgroundColor: colors.border }]}>
          <View
            style={[
              styles.progressFill,
              {
                backgroundColor: colors.primary,
                width: (hasProgress
                  ? `${Math.max(ratio * 100, done > 0 ? 8 : 0)}%`
                  : "0%") as DimensionValue,
              },
            ]}
          />
        </View>
        <Text style={[styles.progressText, { color: colors.textMuted }]} numberOfLines={2}>
          {progressLabel}
        </Text>
      </View>

      {nextItem ? (
        <Pressable
          onPress={onPressNext}
          style={({ pressed }) => [
            styles.nextCard,
            { backgroundColor: colors.primaryTint, opacity: pressed ? 0.9 : 1 },
          ]}
        >
          <Text style={[styles.nextLabel, { color: colors.textMuted }]}>Próximo</Text>
          <Text style={[styles.nextTitle, { color: colors.text }]} numberOfLines={1}>
            {nextItem.title}
          </Text>
          <Text style={[styles.nextWhen, { color: colors.primary }]} numberOfLines={1}>
            {nextItem.whenLabel}
          </Text>
        </Pressable>
      ) : null}

      <EnergyBar colors={colors} access={access} />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 14,
    marginBottom: 12,
  },
  greeting: {
    fontSize: 17,
    fontWeight: "700",
    marginBottom: 10,
  },
  progressRow: {
    gap: 6,
    marginBottom: 10,
  },
  progressTrack: {
    height: 6,
    borderRadius: 999,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: 999,
  },
  progressText: {
    fontSize: 14,
    lineHeight: 20,
  },
  nextCard: {
    borderRadius: 10,
    padding: 10,
    marginBottom: 10,
  },
  nextLabel: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.4,
    marginBottom: 2,
  },
  nextTitle: {
    fontSize: 16,
    fontWeight: "700",
  },
  nextWhen: {
    fontSize: 13,
    fontWeight: "600",
    marginTop: 2,
  },
  energyRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 2,
  },
  energyLabel: {
    fontSize: 12,
    fontWeight: "600",
    width: 52,
  },
  energyTrack: {
    flex: 1,
    height: 5,
    borderRadius: 999,
    overflow: "hidden",
  },
  energyFill: {
    height: "100%",
  },
  energyPct: {
    fontSize: 12,
    fontWeight: "700",
    minWidth: 32,
    textAlign: "right",
  },
  recharge: {
    fontSize: 12,
    fontWeight: "800",
    minWidth: 72,
    textAlign: "right",
  },
});
