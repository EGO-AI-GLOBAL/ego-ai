import type { AccessInfo, PlanTier } from "@/api/types";
import * as Linking from "expo-linking";
import React, { useCallback } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

const SHAPESCAN_URL = "https://shapescanapp.com.br";
const COPY =
  "Estresse no peito? O corpo ajuda a mente. Monta o treino no ShapeScan. Baixa já.";

type Props = {
  planTier?: PlanTier | string | null;
  access?: AccessInfo | null;
};

function isEssentialPlan(
  planTier?: PlanTier | string | null,
  access?: AccessInfo | null
): boolean {
  const tier = (planTier || access?.plan_tier || "").toString().trim().toLowerCase();
  return tier === "essential";
}

/**
 * Cross-promo ShapeScan — só Essential, fixo acima do ChatComposer.
 */
export function ShapeScanCrossPromoBanner({ planTier, access }: Props) {
  const show = isEssentialPlan(planTier, access);

  const onPress = useCallback(() => {
    void Linking.openURL(SHAPESCAN_URL).catch(() => {
      /* ignore */
    });
  }, []);

  if (!show) return null;

  return (
    <View style={styles.wrap}>
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
        accessibilityRole="button"
        accessibilityLabel="Abrir ShapeScan"
      >
        <Text style={styles.text}>{COPY}</Text>
        <Text style={styles.cta}>Baixar ShapeScan →</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: "100%",
    paddingHorizontal: 12,
    paddingTop: 6,
    paddingBottom: 4,
  },
  card: {
    backgroundColor: "#00DF89",
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
  },
  cardPressed: {
    opacity: 0.88,
  },
  text: {
    color: "#FFFFFF",
    fontWeight: "600",
    fontSize: 14,
    lineHeight: 20,
  },
  cta: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 13,
    marginTop: 8,
  },
});
