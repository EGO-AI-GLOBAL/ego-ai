import { router } from "expo-router";
import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AccessInfo, WellnessJourney } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { isTrialUrgent, parseTrialDaysRemaining } from "@/utils/trialAccess";
import { allowsInAppPlanPurchase } from "@/utils/iosAppStoreBilling";

type Props = {
  colors: AppColors;
  access?: AccessInfo | null;
  journey?: WellnessJourney | null;
};

/** Últimos dias do trial — destaca EGO de Bolso + nível (Fase 2 paywall emocional). */
export function EgoDeBolsoTrialNudge({ colors, access, journey }: Props) {
  const days = parseTrialDaysRemaining(access);
  if (days === null || !isTrialUrgent(days)) return null;

  const level = journey?.level ?? 1;
  const stage = journey?.companion_stage_label ?? "EGO de Bolso";
  const emoji = journey?.companion_sprite_emoji ?? journey?.emoji ?? "🥚";

  const body = (
    <>
      <Text style={[styles.title, { color: colors.warning }]}>
        ⏳ {days === 0 ? "Último dia grátis" : `${days} dias grátis`}
      </Text>
      <Text style={[styles.body, { color: colors.text }]}>
        {emoji} Seu {stage} está no nível {level}.{" "}
        {allowsInAppPlanPurchase()
          ? "Assine Conexão para não perder o progresso."
          : "Aproveite os dias grátis restantes."}
      </Text>
      {allowsInAppPlanPurchase() ? (
        <Text style={[styles.cta, { color: colors.primary }]}>Ver planos →</Text>
      ) : null}
    </>
  );

  if (!allowsInAppPlanPurchase()) {
    return (
      <View style={[styles.wrap, { borderColor: colors.warning, backgroundColor: `${colors.warning}14` }]}>
        {body}
      </View>
    );
  }

  return (
    <Pressable
      onPress={() => router.push("/(main)/plans")}
      style={[styles.wrap, { borderColor: colors.warning, backgroundColor: `${colors.warning}14` }]}
    >
      {body}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: 12,
    borderWidth: 1.5,
    padding: 12,
    marginBottom: 12,
  },
  title: { fontSize: 14, fontWeight: "800" },
  body: { fontSize: 13, lineHeight: 18, marginTop: 6 },
  cta: { fontSize: 12, fontWeight: "800", marginTop: 8 },
});
