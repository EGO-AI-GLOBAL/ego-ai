import { router } from "expo-router";
import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AccessInfo, DailyCareInfo, StreakInfo, WellnessJourney } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { buildTrialExpiredMessage, isTrialExpired } from "@/utils/trialAccess";
import { allowsInAppPlanPurchase } from "@/utils/iosAppStoreBilling";

type PlanOffer = {
  id: string;
  label: string;
  cta: string;
  tag: string;
  highlight: boolean;
  url: string | null;
};

type Props = {
  colors: AppColors;
  access?: AccessInfo | null;
  streak?: StreakInfo | null;
  journey?: WellnessJourney | null;
  care?: DailyCareInfo | null;
  planOffers: PlanOffer[];
  onOpenCheckout: (url: string | null) => void;
};

/** Paywall emocional após os 20 dias grátis. */
export function TrialExpiredBanner({
  colors,
  access,
  streak,
  journey,
  care,
  planOffers,
  onOpenCheckout,
}: Props) {
  if (!isTrialExpired(access)) return null;

  const message = buildTrialExpiredMessage(streak, journey, care);

  return (
    <View style={[styles.wrap, { borderColor: colors.danger, backgroundColor: colors.bgCard }]}>
      <Text style={[styles.title, { color: colors.danger }]}>Teste grátis encerrado</Text>
      <Text style={[styles.body, { color: colors.text }]}>{message}</Text>
      {allowsInAppPlanPurchase() ? (
        <>
          <View style={styles.actions}>
            {planOffers.map((offer) => (
              <Pressable
                key={offer.id}
                onPress={() => onOpenCheckout(offer.url)}
                style={[
                  styles.planBtn,
                  {
                    backgroundColor: offer.highlight ? colors.primary : colors.bg,
                    borderColor: offer.highlight ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text style={[styles.planTag, { color: offer.highlight ? "#fff" : colors.primary }]}>
                  {offer.tag}
                </Text>
                <Text style={[styles.planName, { color: offer.highlight ? "#fff" : colors.text }]}>
                  {offer.label}
                </Text>
                <Text style={[styles.planCta, { color: offer.highlight ? "#fff" : colors.primary }]}>
                  {offer.cta}
                </Text>
              </Pressable>
            ))}
          </View>
          <Pressable onPress={() => router.push("/(main)/plans")} style={styles.allPlans}>
            <Text style={[styles.allPlansText, { color: colors.textMuted }]}>
              Comparar todos os planos
            </Text>
          </Pressable>
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: 14,
    borderWidth: 2,
    padding: 14,
    marginBottom: 12,
  },
  title: { fontSize: 17, fontWeight: "900", textAlign: "center" },
  body: { fontSize: 14, lineHeight: 21, marginTop: 10, textAlign: "center" },
  actions: { marginTop: 14, gap: 8 },
  planBtn: {
    borderRadius: 12,
    borderWidth: 1.5,
    padding: 12,
    alignItems: "center",
  },
  planTag: { fontSize: 10, fontWeight: "800", letterSpacing: 0.5 },
  planName: { fontSize: 16, fontWeight: "800", marginTop: 4 },
  planCta: { fontSize: 13, fontWeight: "700", marginTop: 4 },
  allPlans: { marginTop: 10, alignItems: "center", paddingVertical: 6 },
  allPlansText: { fontSize: 13, fontWeight: "600" },
});
