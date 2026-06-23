import { router } from "expo-router";
import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AccessInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { isTrialUrgent, parseTrialDaysRemaining } from "@/utils/trialAccess";

type Props = {
  colors: AppColors;
  access?: AccessInfo | null;
};

/** Contador de dias grátis — urgência nos últimos 5 dias. */
export function TrialBanner({ colors, access }: Props) {
  const days = parseTrialDaysRemaining(access);
  if (days === null) return null;

  const urgent = isTrialUrgent(days);
  const border = urgent ? colors.warning : colors.primary;
  const bg = urgent ? `${colors.warning}18` : colors.primaryTint;

  return (
    <Pressable
      onPress={() => router.push("/(main)/plans")}
      style={[styles.wrap, { borderColor: border, backgroundColor: bg }]}
    >
      <Text style={[styles.title, { color: urgent ? colors.warning : colors.primary }]}>
        {urgent ? "⏳" : "🎁"} {days === 0 ? "Último dia grátis" : `${days} dias grátis restantes`}
      </Text>
      <Text style={[styles.sub, { color: colors.textMuted }]}>
        {urgent
          ? "Não perca seus monstrinhos e seu companheiro — assine Conexão e continue."
          : "Teste completo por 20 dias. Depois, escolha um plano para seguir."}
      </Text>
      <Text style={[styles.cta, { color: colors.primary }]}>Ver planos →</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: 12,
    borderWidth: 1.5,
    padding: 12,
    marginBottom: 10,
  },
  title: { fontSize: 14, fontWeight: "800" },
  sub: { fontSize: 12, lineHeight: 17, marginTop: 4 },
  cta: { fontSize: 12, fontWeight: "800", marginTop: 8 },
});
