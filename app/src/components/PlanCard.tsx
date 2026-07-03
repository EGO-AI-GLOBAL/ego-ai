import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import type { PlanCatalogItem, PlanTier } from "@/api/types";
import {
  formatMonthlyPrice,
  PLAN_TAGLINES,
  planFeatureLines,
} from "@/constants/plans";

type Props = {
  colors: AppColors;
  plan: PlanCatalogItem;
  isCurrent: boolean;
  highlighted?: boolean;
  checkoutUrl: string | null;
  onSubscribe: (tier: PlanTier, url: string) => void;
  busy?: boolean;
  /** Ex.: "US$ 14,99/year" em vez do preço mensal formatado */
  priceOverride?: string;
  /** Substitui o selo «Recomendado» (ex.: «Lançamento»). */
  badgeLabel?: string;
  /** Texto do botão (ex.: «Mudar para este plano»). */
  subscribeLabel?: string;
  /** Compra via In-App Purchase (iOS) — ignora checkoutUrl. */
  purchaseViaIap?: boolean;
  onIapPurchase?: (tier: PlanTier) => void;
  /** Nota sob o plano atual (ex.: cancelar para voltar ao grátis). */
  footnote?: string;
};

export function PlanCard({
  colors,
  plan,
  isCurrent,
  highlighted,
  checkoutUrl,
  onSubscribe,
  busy,
  priceOverride,
  badgeLabel,
  subscribeLabel,
  footnote,
  purchaseViaIap,
  onIapPurchase,
}: Props) {
  const features = planFeatureLines(plan);
  const canSubscribeIap =
    purchaseViaIap && !isCurrent && plan.tier !== "essential" && Boolean(onIapPurchase);
  const canSubscribeStripe =
    !purchaseViaIap && !isCurrent && Boolean(checkoutUrl);
  const canSubscribe = canSubscribeIap || canSubscribeStripe;
  const ctaLabel = subscribeLabel || "Assinar";

  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: colors.bgCard,
          borderColor: highlighted ? colors.primary : colors.border,
          borderWidth: highlighted ? 2 : StyleSheet.hairlineWidth,
        },
      ]}
    >
      {highlighted ? (
        <View style={[styles.badge, { backgroundColor: colors.primary }]}>
          <Text style={styles.badgeText}>{badgeLabel || "Recomendado"}</Text>
        </View>
      ) : null}

      <Text style={[styles.name, { color: colors.text }]}>{plan.label}</Text>
      <Text style={[styles.tagline, { color: colors.textMuted }]}>
        {PLAN_TAGLINES[plan.tier]}
      </Text>
      <Text style={[styles.price, { color: colors.primary }]}>
        {priceOverride ??
          (plan.label === "EGO AI Pro" && plan.price_brl < 20
            ? `US$ ${plan.price_brl.toFixed(2)}/month`
            : formatMonthlyPrice(plan.price_brl))}
      </Text>

      <View style={styles.features}>
        {features.map((line) => (
          <View key={line} style={styles.featureRow}>
            <Text style={[styles.bullet, { color: colors.primary }]}>•</Text>
            <Text style={[styles.feature, { color: colors.text }]}>{line}</Text>
          </View>
        ))}
      </View>

      {isCurrent ? (
        <View style={[styles.statusPill, { backgroundColor: colors.userBubble }]}>
          <Text style={[styles.statusText, { color: colors.text }]}>Plano atual</Text>
          {footnote ? (
            <Text style={[styles.footnote, { color: colors.textMuted }]}>{footnote}</Text>
          ) : null}
        </View>
      ) : (
        <Pressable
          disabled={!canSubscribe || busy}
          onPress={() => {
            if (canSubscribeIap && onIapPurchase) {
              onIapPurchase(plan.tier);
              return;
            }
            if (checkoutUrl) onSubscribe(plan.tier, checkoutUrl);
          }}
          style={({ pressed }) => [
            styles.cta,
            {
              backgroundColor: canSubscribe ? colors.primary : colors.border,
              opacity: !canSubscribe ? 0.55 : pressed ? 0.88 : 1,
            },
          ]}
        >
          {busy ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.ctaText}>
              {canSubscribe ? ctaLabel : "Link em configuração"}
            </Text>
          )}
        </Pressable>
      )}
      {!isCurrent && footnote ? (
        <Text style={[styles.footnote, { color: colors.textMuted, marginTop: 10 }]}>
          {footnote}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    padding: 18,
    marginBottom: 16,
    position: "relative",
    overflow: "hidden",
  },
  badge: {
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    marginBottom: 10,
  },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "800" },
  name: { fontSize: 20, fontWeight: "800", letterSpacing: -0.3 },
  tagline: { fontSize: 14, marginTop: 4, lineHeight: 20 },
  price: { fontSize: 26, fontWeight: "800", marginTop: 12, marginBottom: 14 },
  features: { gap: 8, marginBottom: 16 },
  featureRow: { flexDirection: "row", gap: 8, alignItems: "flex-start" },
  bullet: { fontSize: 16, lineHeight: 20, fontWeight: "700" },
  feature: { flex: 1, fontSize: 14, lineHeight: 20 },
  cta: {
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 48,
  },
  ctaText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  statusPill: {
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  statusText: { fontSize: 15, fontWeight: "700" },
  footnote: {
    fontSize: 12,
    lineHeight: 17,
    marginTop: 8,
    textAlign: "center",
  },
});
