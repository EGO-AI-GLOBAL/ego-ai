import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, View } from "react-native";
import { MOOD_PALETTES, moodKeyOrDefault, type MoodKey } from "@/constants/moodMonsters";

type Props = {
  moodKey?: string;
  size?: number;
  celebrate?: boolean;
};

export function MoodMonsterIllustration({ moodKey, size = 112, celebrate = false }: Props) {
  const key = moodKeyOrDefault(moodKey);
  const p = MOOD_PALETTES[key];
  const scale = useRef(new Animated.Value(1)).current;
  const bounce = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!celebrate) return;
    scale.setValue(1);
    bounce.setValue(0);
    Animated.parallel([
      Animated.sequence([
        Animated.spring(scale, { toValue: 1.12, friction: 4, useNativeDriver: true }),
        Animated.spring(scale, { toValue: 1, friction: 5, useNativeDriver: true }),
      ]),
      Animated.sequence([
        Animated.timing(bounce, { toValue: -10, duration: 180, useNativeDriver: true }),
        Animated.spring(bounce, { toValue: 0, friction: 4, useNativeDriver: true }),
      ]),
    ]).start();
  }, [celebrate, scale, bounce]);

  const eyeY = key === "heavy" ? 2 : 0;
  const mouthWide = key === "good" || key === "calm";
  const mouthSad = key === "heavy" || key === "anxious";

  return (
    <Animated.View
      style={[
        styles.wrap,
        {
          transform: [{ scale }, { translateY: bounce }],
        },
      ]}
    >
      <View
        style={[
          styles.shadow,
          {
            width: size * 0.85,
            height: size * 0.12,
            borderRadius: size * 0.06,
            marginTop: size * 0.02,
          },
        ]}
      />
      <View
        style={[
          styles.body,
          {
            width: size,
            height: size * 0.92,
            borderRadius: size * 0.46,
            backgroundColor: p.body,
            borderColor: p.bodyDark,
          },
        ]}
      >
        <View style={[styles.cheek, { left: size * 0.12, backgroundColor: p.cheek }]} />
        <View style={[styles.cheek, { right: size * 0.12, backgroundColor: p.cheek }]} />
        <View style={[styles.eyes, { marginTop: size * 0.28 + eyeY }]}>
          <View style={[styles.eye, { backgroundColor: p.eye }]} />
          <View style={[styles.eye, { backgroundColor: p.eye }]} />
        </View>
        <View
          style={[
            mouthSad ? styles.mouthSad : mouthWide ? styles.mouthHappy : styles.mouthNeutral,
            { borderColor: p.mouth, backgroundColor: mouthSad ? "transparent" : p.accent },
          ]}
        />
        {key === "anxious" ? (
          <View style={[styles.sweat, { backgroundColor: p.accent, right: size * 0.18, top: size * 0.22 }]} />
        ) : null}
        {key === "good" ? (
          <View style={[styles.spark, { backgroundColor: p.accent, top: -6, right: 8 }]} />
        ) : null}
      </View>
      <View style={styles.feet}>
        <View style={[styles.foot, { backgroundColor: p.bodyDark }]} />
        <View style={[styles.foot, { backgroundColor: p.bodyDark }]} />
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center" },
  shadow: { backgroundColor: "rgba(0,0,0,0.12)", alignSelf: "center" },
  body: {
    borderWidth: 3,
    alignItems: "center",
    overflow: "visible",
  },
  cheek: {
    position: "absolute",
    width: 18,
    height: 10,
    borderRadius: 8,
    top: "52%",
    opacity: 0.55,
  },
  eyes: { flexDirection: "row", gap: 18 },
  eye: { width: 14, height: 14, borderRadius: 7 },
  mouthHappy: {
    width: 28,
    height: 14,
    borderBottomLeftRadius: 14,
    borderBottomRightRadius: 14,
    marginTop: 8,
  },
  mouthNeutral: {
    width: 16,
    height: 4,
    borderRadius: 2,
    marginTop: 12,
  },
  mouthSad: {
    width: 20,
    height: 10,
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderRightWidth: 3,
    borderBottomWidth: 0,
    borderTopLeftRadius: 12,
    borderTopRightRadius: 12,
    marginTop: 10,
  },
  sweat: { position: "absolute", width: 8, height: 12, borderRadius: 4 },
  spark: { position: "absolute", width: 12, height: 12, borderRadius: 6 },
  feet: { flexDirection: "row", gap: 20, marginTop: -4 },
  foot: { width: 22, height: 12, borderRadius: 8 },
});
