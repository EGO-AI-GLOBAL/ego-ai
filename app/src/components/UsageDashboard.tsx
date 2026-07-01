import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { AccessInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { allowsInAppPlanPurchase } from "@/utils/iosAppStoreBilling";
import {
  buildUsageMetrics,
  primaryTokenPercent,
  type UsageLevel,
  type UsageMetric,
} from "@/utils/usageStats";

type Props = {
  colors: AppColors;
  access: AccessInfo | null;
  /** Destaque grande no topo (tela Uso) */
  expanded?: boolean;
};

function levelColor(colors: AppColors, level: UsageLevel): string {
  if (level === "critical") return colors.danger;
  if (level === "warn") return colors.warning;
  return colors.primary;
}

function MetricRow({
  colors,
  metric,
  large,
}: {
  colors: AppColors;
  metric: UsageMetric;
  large?: boolean;
}) {
  const fill = levelColor(colors, metric.level);
  return (
    <View style={[styles.metric, large && styles.metricLarge]}>
      <View style={styles.metricHeader}>
        <Text style={[styles.metricLabel, { color: colors.text }]}>{metric.label}</Text>
        <Text style={[styles.metricPct, { color: fill }]}>{metric.percent}%</Text>
      </View>
      <View style={[styles.track, { backgroundColor: colors.border }]}>
        <View
          style={[
            styles.fill,
            {
              backgroundColor: fill,
              width: `${Math.max(metric.percent, 2)}%`,
            },
          ]}
        />
      </View>
    </View>
  );
}

export function UsageDashboard({ colors, access, expanded = false }: Props) {
  const metrics = buildUsageMetrics(access);
  const tokenPct = primaryTokenPercent(access);
  const tokenMetric = metrics.find((m) => m.id === "tokens");
  const others = metrics.filter((m) => m.id !== "tokens");

  const planLabel = access?.plan_label || "EGO Essencial";
  const ok = access?.monthly_tokens_ok !== false;

  if (!access) {
    return (
      <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
        <Text style={[styles.empty, { color: colors.textMuted }]}>
          Dados de uso indisponíveis. Puxe para atualizar.
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
      <Text style={[styles.cardTitle, { color: colors.textMuted }]}>Uso do plano</Text>
      <Text style={[styles.planName, { color: colors.text }]}>{planLabel}</Text>

      {tokenMetric ? (
        <View style={styles.hero}>
          <Text
            style={[
              styles.heroPct,
              { color: levelColor(colors, tokenMetric.level) },
            ]}
          >
            {tokenPct}%
          </Text>
          <View style={[styles.trackHero, { backgroundColor: colors.border }]}>
            <View
              style={[
                styles.fill,
                {
                  backgroundColor: levelColor(colors, tokenMetric.level),
                  width: `${Math.max(tokenPct, 2)}%`,
                },
              ]}
            />
          </View>
          {!ok ? (
            <Text style={[styles.alert, { color: colors.danger }]}>
              {allowsInAppPlanPurchase()
                ? "Limite mensal atingido. Faça upgrade ou aguarde o próximo mês."
                : "Limite mensal atingido. Aguarde o próximo mês ou entre com uma conta com acesso ativo."}
            </Text>
          ) : tokenPct >= 75 ? (
            <Text style={[styles.alert, { color: colors.warning }]}>
              Você está perto do limite mensal.
            </Text>
          ) : null}
        </View>
      ) : null}

      {others.length > 0 ? (
        <>
          <Text style={[styles.section, { color: colors.textMuted }]}>
            Limites diários e agenda
          </Text>
          {others.map((m) => (
            <MetricRow key={m.id} colors={colors} metric={m} large={expanded} />
          ))}
        </>
      ) : null}

      {expanded ? (
        <Text style={[styles.footnote, { color: colors.textMuted }]}>
          Renova no início de cada mês. Limites diários zeram à meia-noite.
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 18,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  planName: { fontSize: 20, fontWeight: "800", marginTop: 4, marginBottom: 16 },
  hero: { marginBottom: 8 },
  heroPct: { fontSize: 48, fontWeight: "800", letterSpacing: -1 },
  trackHero: {
    height: 10,
    borderRadius: 999,
    overflow: "hidden",
    marginTop: 8,
  },
  alert: { fontSize: 13, marginTop: 10, lineHeight: 18 },
  section: {
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
    marginTop: 12,
    marginBottom: 10,
  },
  metric: { marginBottom: 14 },
  metricLarge: { marginBottom: 18 },
  metricHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  metricLabel: { fontSize: 14, fontWeight: "600", flex: 1, paddingRight: 8 },
  metricPct: { fontSize: 15, fontWeight: "800" },
  track: {
    height: 6,
    borderRadius: 999,
    overflow: "hidden",
  },
  fill: { height: "100%", borderRadius: 999 },
  footnote: { fontSize: 12, lineHeight: 17, marginTop: 8 },
  empty: { fontSize: 14 },
});
