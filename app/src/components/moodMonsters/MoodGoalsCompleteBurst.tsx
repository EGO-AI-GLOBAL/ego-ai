import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  visible: boolean;
  bonus?: number;
  totalGoals?: number;
  congratsLine?: string;
  onDone?: () => void;
};

/** Burst visual quando todas as missões do dia ficam completas. */
export function MoodGoalsCompleteBurst({
  colors,
  visible,
  bonus = 3,
  totalGoals = 5,
  congratsLine,
  onDone,
}: Props) {
  const scale = useRef(new Animated.Value(0.6)).current;
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!visible) return;
    scale.setValue(0.6);
    opacity.setValue(0);
    Animated.sequence([
      Animated.parallel([
        Animated.spring(scale, { toValue: 1.08, friction: 4, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 1, duration: 200, useNativeDriver: true }),
      ]),
      Animated.delay(1400),
      Animated.timing(opacity, { toValue: 0, duration: 350, useNativeDriver: true }),
    ]).start(({ finished }) => {
      if (finished) onDone?.();
    });
  }, [visible, scale, opacity, onDone]);

  if (!visible) return null;

  return (
    <View style={styles.wrap} pointerEvents="none">
      <Animated.View
        style={[
          styles.card,
          {
            backgroundColor: colors.primaryTint,
            borderColor: colors.primary,
            opacity,
            transform: [{ scale }],
          },
        ]}
      >
        <Text style={styles.emoji}>🎉✨🌰</Text>
        <Text style={[styles.title, { color: colors.text }]}>Dia perfeito no jardim!</Text>
        <Text style={[styles.sub, { color: colors.primary }]}>
          {totalGoals}/{totalGoals} missões · +{bonus} sementes bónus
        </Text>
        {congratsLine ? (
          <Text style={[styles.congrats, { color: colors.text }]} numberOfLines={3}>
            {congratsLine}
          </Text>
        ) : null}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
    zIndex: 20,
  },
  card: {
    borderWidth: 2,
    borderRadius: 16,
    paddingHorizontal: 20,
    paddingVertical: 16,
    alignItems: "center",
    maxWidth: "88%",
  },
  emoji: { fontSize: 32 },
  title: { fontSize: 16, fontWeight: "900", marginTop: 6, textAlign: "center" },
  sub: { fontSize: 13, fontWeight: "700", marginTop: 4, textAlign: "center" },
  congrats: { fontSize: 12, fontWeight: "600", marginTop: 8, textAlign: "center", lineHeight: 17 },
});
