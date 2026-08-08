import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";

export type MoodRewardKind = "level" | "bonus" | "shield" | "name";

export type MoodReward = {
  kind: MoodRewardKind;
  emoji: string;
  title: string;
  sub?: string;
};

type Props = {
  colors: AppColors;
  reward: MoodReward | null;
  onDone?: () => void;
};

/**
 * Festa curta para recompensas do monstrinho (subir de nível, bónus surpresa,
 * escudo ganho). Reforço variável só funciona se for sentido — sem isto, é invisível.
 */
export function MoodRewardBurst({ colors, reward, onDone }: Props) {
  const scale = useRef(new Animated.Value(0.6)).current;
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!reward) return;
    scale.setValue(0.6);
    opacity.setValue(0);
    Animated.sequence([
      Animated.parallel([
        Animated.spring(scale, { toValue: 1.06, friction: 4, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 1, duration: 200, useNativeDriver: true }),
      ]),
      Animated.delay(1500),
      Animated.timing(opacity, { toValue: 0, duration: 350, useNativeDriver: true }),
    ]).start(({ finished }) => {
      if (finished) onDone?.();
    });
  }, [reward, scale, opacity, onDone]);

  if (!reward) return null;

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
        <Text style={styles.emoji}>{reward.emoji}</Text>
        <Text style={[styles.title, { color: colors.text }]}>{reward.title}</Text>
        {reward.sub ? (
          <Text style={[styles.sub, { color: colors.primary }]} numberOfLines={2}>
            {reward.sub}
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
    zIndex: 22,
  },
  card: {
    borderWidth: 2,
    borderRadius: 16,
    paddingHorizontal: 20,
    paddingVertical: 16,
    alignItems: "center",
    maxWidth: "88%",
  },
  emoji: { fontSize: 34 },
  title: { fontSize: 16, fontWeight: "900", marginTop: 6, textAlign: "center" },
  sub: { fontSize: 13, fontWeight: "700", marginTop: 4, textAlign: "center" },
});
