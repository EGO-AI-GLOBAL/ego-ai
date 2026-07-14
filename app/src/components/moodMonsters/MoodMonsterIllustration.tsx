import React, { useEffect, useRef } from "react";
import { Animated, Easing, StyleSheet, Text, View } from "react-native";
import { MOOD_PALETTES, moodKeyOrDefault } from "@/constants/moodMonsters";

type Props = {
  moodKey?: string;
  size?: number;
  celebrate?: boolean;
};

/** Pet do jardim — idle vivo + reação forte no toque (alinhar Reel humor ~230). */
export function MoodMonsterIllustration({ moodKey, size = 112, celebrate = false }: Props) {
  const key = moodKeyOrDefault(moodKey);
  const p = MOOD_PALETTES[key];
  const scale = useRef(new Animated.Value(1)).current;
  const bounce = useRef(new Animated.Value(0)).current;
  const blink = useRef(new Animated.Value(1)).current;
  const wiggle = useRef(new Animated.Value(0)).current;
  const glow = useRef(new Animated.Value(0)).current;
  const breath = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!celebrate) return;
    scale.setValue(1);
    bounce.setValue(0);
    glow.setValue(0);
    Animated.parallel([
      Animated.sequence([
        Animated.spring(scale, { toValue: 1.22, friction: 3.2, tension: 120, useNativeDriver: true }),
        Animated.spring(scale, { toValue: 1, friction: 4.5, useNativeDriver: true }),
      ]),
      Animated.sequence([
        Animated.timing(bounce, {
          toValue: -22,
          duration: 160,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.spring(bounce, { toValue: 0, friction: 3.5, tension: 90, useNativeDriver: true }),
        Animated.timing(bounce, { toValue: -10, duration: 120, useNativeDriver: true }),
        Animated.spring(bounce, { toValue: 0, friction: 4, useNativeDriver: true }),
      ]),
      Animated.sequence([
        Animated.timing(glow, { toValue: 1, duration: 220, useNativeDriver: true }),
        Animated.timing(glow, { toValue: 0.35, duration: 400, useNativeDriver: true }),
        Animated.timing(glow, { toValue: 0, duration: 450, useNativeDriver: true }),
      ]),
      Animated.sequence([
        Animated.timing(wiggle, { toValue: 1.4, duration: 140, useNativeDriver: true }),
        Animated.timing(wiggle, { toValue: -1.4, duration: 180, useNativeDriver: true }),
        Animated.timing(wiggle, { toValue: 0, duration: 160, useNativeDriver: true }),
      ]),
    ]).start();
  }, [celebrate, scale, bounce, glow, wiggle]);

  useEffect(() => {
    if (celebrate) return;
    bounce.setValue(0);
    wiggle.setValue(0);
    const idle = Animated.loop(
      Animated.sequence([
        Animated.timing(bounce, {
          toValue: -10,
          duration: 900,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.timing(bounce, {
          toValue: 0,
          duration: 900,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ])
    );
    const sway = Animated.loop(
      Animated.sequence([
        Animated.timing(wiggle, {
          toValue: 1,
          duration: 1400,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.timing(wiggle, {
          toValue: -1,
          duration: 1400,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ])
    );
    const breathe = Animated.loop(
      Animated.sequence([
        Animated.timing(breath, {
          toValue: 1.045,
          duration: 1600,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.timing(breath, {
          toValue: 1,
          duration: 1600,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ])
    );
    idle.start();
    sway.start();
    breathe.start();
    return () => {
      idle.stop();
      sway.stop();
      breathe.stop();
    };
  }, [celebrate, bounce, wiggle, breath]);

  useEffect(() => {
    const blinkLoop = Animated.loop(
      Animated.sequence([
        Animated.delay(2200),
        Animated.timing(blink, { toValue: 0.12, duration: 80, useNativeDriver: true }),
        Animated.timing(blink, { toValue: 1, duration: 100, useNativeDriver: true }),
        Animated.delay(400),
        Animated.timing(blink, { toValue: 0.12, duration: 70, useNativeDriver: true }),
        Animated.timing(blink, { toValue: 1, duration: 100, useNativeDriver: true }),
      ])
    );
    blinkLoop.start();
    return () => blinkLoop.stop();
  }, [blink]);

  const eyeY = key === "heavy" ? 2 : 0;
  const mouthWide = key === "good" || key === "calm";
  const mouthSad = key === "heavy" || key === "anxious";
  const rotate = wiggle.interpolate({ inputRange: [-1.5, 1.5], outputRange: ["-5deg", "5deg"] });
  const earTilt = key === "heavy" ? "12deg" : key === "anxious" ? "-8deg" : "0deg";
  const glowOpacity = glow.interpolate({ inputRange: [0, 1], outputRange: [0, 0.55] });
  const bodyScale = celebrate ? scale : Animated.multiply(scale, breath);

  return (
    <Animated.View
      style={[
        styles.wrap,
        {
          transform: [{ scale: bodyScale }, { translateY: bounce }, { rotate }],
        },
      ]}
    >
      <Animated.View
        pointerEvents="none"
        style={[
          styles.glowRing,
          {
            width: size * 1.28,
            height: size * 1.18,
            borderRadius: size * 0.64,
            backgroundColor: p.accent,
            opacity: glowOpacity,
            transform: [{ scale: glow.interpolate({ inputRange: [0, 1], outputRange: [0.85, 1.12] }) }],
          },
        ]}
      />
      <View style={styles.earRow}>
        <View
          style={[
            styles.ear,
            { backgroundColor: p.bodyDark, transform: [{ rotate: `-${earTilt}` }] },
          ]}
        />
        <View
          style={[
            styles.ear,
            { backgroundColor: p.bodyDark, transform: [{ rotate: earTilt }] },
          ]}
        />
      </View>
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
          <Animated.View style={[styles.eye, { backgroundColor: p.eye, transform: [{ scaleY: blink }] }]} />
          <Animated.View style={[styles.eye, { backgroundColor: p.eye, transform: [{ scaleY: blink }] }]} />
          {key === "good" ? <Text style={styles.eyeSpark}>✦</Text> : null}
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
        {key === "good" ? <Text style={styles.sparkEmoji}>✨</Text> : null}
        {key === "calm" ? <Text style={styles.calmAura}>💫</Text> : null}
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
  glowRing: {
    position: "absolute",
    alignSelf: "center",
    top: 8,
    zIndex: 0,
  },
  earRow: {
    position: "absolute",
    top: 2,
    width: "80%",
    alignSelf: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    zIndex: 5,
  },
  ear: {
    width: 16,
    height: 22,
    borderRadius: 10,
    marginTop: -8,
  },
  shadow: { backgroundColor: "rgba(0,0,0,0.12)", alignSelf: "center", zIndex: 1 },
  body: {
    borderWidth: 3,
    alignItems: "center",
    overflow: "visible",
    zIndex: 2,
  },
  cheek: {
    position: "absolute",
    width: 18,
    height: 10,
    borderRadius: 8,
    top: "52%",
    opacity: 0.55,
  },
  eyes: { flexDirection: "row", gap: 18, alignItems: "center" },
  eye: { width: 14, height: 14, borderRadius: 7 },
  eyeSpark: { position: "absolute", right: -8, top: -10, fontSize: 10, color: "#FFD54F" },
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
  sparkEmoji: { position: "absolute", top: -10, right: 2, fontSize: 16 },
  calmAura: { position: "absolute", top: -8, left: 6, fontSize: 14, opacity: 0.85 },
  feet: { flexDirection: "row", gap: 20, marginTop: -4, zIndex: 2 },
  foot: { width: 22, height: 12, borderRadius: 8 },
});
