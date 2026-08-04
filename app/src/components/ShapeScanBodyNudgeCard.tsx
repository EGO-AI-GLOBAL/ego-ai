import {
  openShapeScan,
  SHAPESCAN_BODY_NUDGE_CTA,
  SHAPESCAN_BODY_NUDGE_TITLE,
} from "@/constants/shapeScanPromo";
import type { AppColors } from "@/theme/colors";
import React, { useCallback } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

type Props = {
  colors: AppColors;
  onDismiss?: () => void;
};

/**
 * Card pós check-in / sessão (FREE only — o pai decide).
 * Espelho ShapeScan: «Mente ok. E o corpo?» → Abrir ShapeScan.
 * Não vende IAP ShapeScan; só abre loja/site.
 */
export function ShapeScanBodyNudgeCard({ colors, onDismiss }: Props) {
  const onOpen = useCallback(() => {
    void openShapeScan();
  }, []);

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.bgCard, borderColor: colors.primary },
      ]}
      accessibilityLabel={SHAPESCAN_BODY_NUDGE_TITLE}
    >
      <View style={styles.row}>
        <View style={styles.textCol}>
          <Text style={[styles.title, { color: colors.text }]}>
            {SHAPESCAN_BODY_NUDGE_TITLE}
          </Text>
          <Text style={[styles.sub, { color: colors.textMuted }]}>
            Treino e dieta no ShapeScan — grátis para começar.
          </Text>
        </View>
        {onDismiss ? (
          <Pressable
            onPress={onDismiss}
            hitSlop={10}
            accessibilityRole="button"
            accessibilityLabel="Fechar"
          >
            <Text style={[styles.dismiss, { color: colors.textMuted }]}>✕</Text>
          </Pressable>
        ) : null}
      </View>
      <Pressable
        onPress={onOpen}
        style={({ pressed }) => [
          styles.cta,
          { backgroundColor: "#00DF89" },
          pressed && styles.ctaPressed,
        ]}
        accessibilityRole="button"
        accessibilityLabel={SHAPESCAN_BODY_NUDGE_CTA}
      >
        <Text style={styles.ctaText}>{SHAPESCAN_BODY_NUDGE_CTA}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 14,
    borderWidth: 1.5,
    padding: 14,
    marginBottom: 12,
  },
  row: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  textCol: { flex: 1 },
  title: { fontSize: 17, fontWeight: "900", marginBottom: 4 },
  sub: { fontSize: 13, lineHeight: 18, marginBottom: 12 },
  dismiss: { fontSize: 16, fontWeight: "700", paddingHorizontal: 4 },
  cta: {
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  ctaPressed: { opacity: 0.88 },
  ctaText: { color: "#0A1A14", fontWeight: "900", fontSize: 15 },
});
