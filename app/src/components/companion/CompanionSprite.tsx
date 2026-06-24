import { LinearGradient } from "expo-linear-gradient";
import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";

export type CompanionStage = "egg" | "hatchling" | "teen" | "adult";

type Props = {
  stage?: string;
  size?: number;
  happy?: boolean;
};

const STAGE_PALETTE: Record<
  CompanionStage,
  { body: [string, string, string]; ring: string; glow: string; accent: string }
> = {
  egg: {
    body: ["#1E0A3C", "#5B21B6", "#22D3EE"],
    ring: "#A78BFA",
    glow: "rgba(34, 211, 238, 0.45)",
    accent: "#E879F9",
  },
  hatchling: {
    body: ["#312E81", "#7C3AED", "#38BDF8"],
    ring: "#C4B5FD",
    glow: "rgba(167, 139, 250, 0.5)",
    accent: "#FDE047",
  },
  teen: {
    body: ["#0C4A6E", "#2563EB", "#22D3EE"],
    ring: "#67E8F9",
    glow: "rgba(56, 189, 248, 0.5)",
    accent: "#A5F3FC",
  },
  adult: {
    body: ["#4C1D95", "#7C3AED", "#F472B6"],
    ring: "#F0ABFC",
    glow: "rgba(244, 114, 182, 0.45)",
    accent: "#FDE68A",
  },
};

function GlowRing({
  size,
  color,
  pulse,
}: {
  size: number;
  color: string;
  pulse: Animated.Value;
}) {
  const scale = pulse.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1.08],
  });
  const opacity = pulse.interpolate({
    inputRange: [0, 1],
    outputRange: [0.35, 0.75],
  });
  return (
    <Animated.View
      style={[
        styles.glowRing,
        {
          width: size * 1.15,
          height: size * 1.15,
          borderRadius: size * 0.58,
          borderColor: color,
          opacity,
          transform: [{ scale }],
        },
      ]}
    />
  );
}

function CircuitDots({ size, color }: { size: number; color: string }) {
  return (
    <View style={styles.circuitRow}>
      {[0, 1, 2].map((i) => (
        <View
          key={i}
          style={[
            styles.circuitDot,
            {
              width: size * 0.06,
              height: size * 0.06,
              backgroundColor: color,
              marginHorizontal: size * 0.04,
            },
          ]}
        />
      ))}
    </View>
  );
}

export function CompanionSprite({ stage = "egg", size = 100, happy = false }: Props) {
  const s = (stage as CompanionStage) || "egg";
  const palette = STAGE_PALETTE[s] ?? STAGE_PALETTE.egg;
  const wobble = useRef(new Animated.Value(0)).current;
  const pulse = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 1400, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0, duration: 1400, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  useEffect(() => {
    if (!happy) return;
    Animated.sequence([
      Animated.timing(wobble, { toValue: 1, duration: 120, useNativeDriver: true }),
      Animated.timing(wobble, { toValue: -1, duration: 120, useNativeDriver: true }),
      Animated.timing(wobble, { toValue: 0, duration: 100, useNativeDriver: true }),
    ]).start();
  }, [happy, wobble]);

  const rotate = wobble.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: ["-6deg", "0deg", "6deg"],
  });

  if (s === "egg") {
    return (
      <Animated.View style={[styles.center, { transform: [{ rotate }] }]}>
        <GlowRing size={size} color={palette.ring} pulse={pulse} />
        <LinearGradient
          colors={palette.body}
          start={{ x: 0.1, y: 0 }}
          end={{ x: 0.9, y: 1 }}
          style={[
            styles.egg,
            {
              width: size * 0.72,
              height: size,
              borderRadius: size * 0.36,
              borderColor: palette.ring,
            },
          ]}
        >
          <View style={[styles.eggCore, { backgroundColor: palette.glow }]} />
          <View style={[styles.eggScan, { borderColor: palette.accent }]} />
          <CircuitDots size={size} color={palette.accent} />
          <View style={[styles.eggShine, { backgroundColor: "rgba(255,255,255,0.35)" }]} />
        </LinearGradient>
      </Animated.View>
    );
  }

  const bodyH = s === "adult" ? size * 0.88 : size * 0.78;

  return (
    <Animated.View style={[styles.center, { transform: [{ rotate }] }]}>
      <GlowRing size={size} color={palette.ring} pulse={pulse} />
      <LinearGradient
        colors={palette.body}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[
          styles.creatureBody,
          {
            width: size * 0.84,
            height: bodyH,
            borderRadius: size * 0.42,
            borderColor: palette.ring,
          },
        ]}
      >
        <View style={styles.antennaRow}>
          <View style={[styles.antenna, { backgroundColor: palette.accent }]} />
          <View style={[styles.antenna, { backgroundColor: palette.accent }]} />
        </View>
        <View style={styles.eyes}>
          <View style={[styles.eyeGlow, { shadowColor: palette.accent }]}>
            <View style={[styles.eye, { backgroundColor: "#0F172A" }]} />
          </View>
          <View style={[styles.eyeGlow, { shadowColor: palette.accent }]}>
            <View style={[styles.eye, { backgroundColor: "#0F172A" }]} />
          </View>
        </View>
        <View style={[styles.mouthBar, { backgroundColor: palette.accent }]} />
        {s === "adult" ? (
          <Text style={[styles.crown, { color: palette.accent }]}>◆</Text>
        ) : null}
        {s === "hatchling" ? (
          <View style={[styles.shellChip, { borderColor: palette.ring }]}>
            <Text style={{ fontSize: 9, color: palette.accent }}>BOOT</Text>
          </View>
        ) : null}
      </LinearGradient>
      <View style={styles.feet}>
        <View style={[styles.foot, { backgroundColor: palette.ring }]} />
        <View style={[styles.foot, { backgroundColor: palette.ring }]} />
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: "center", justifyContent: "center" },
  glowRing: {
    position: "absolute",
    borderWidth: 2,
  },
  egg: {
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  eggCore: {
    position: "absolute",
    width: "55%",
    height: "40%",
    borderRadius: 999,
    top: "28%",
    opacity: 0.35,
  },
  eggScan: {
    position: "absolute",
    width: "70%",
    height: 2,
    borderTopWidth: 1,
    top: "46%",
    opacity: 0.8,
  },
  eggShine: {
    position: "absolute",
    top: 14,
    left: 16,
    width: 16,
    height: 28,
    borderRadius: 8,
    transform: [{ rotate: "-18deg" }],
  },
  circuitRow: {
    flexDirection: "row",
    marginTop: 8,
    opacity: 0.9,
  },
  circuitDot: {
    borderRadius: 999,
  },
  creatureBody: {
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
  },
  antennaRow: {
    position: "absolute",
    top: -10,
    flexDirection: "row",
    gap: 22,
  },
  antenna: {
    width: 3,
    height: 12,
    borderRadius: 2,
  },
  eyes: {
    flexDirection: "row",
    gap: 16,
    marginTop: 2,
  },
  eyeGlow: {
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.9,
    shadowRadius: 6,
    elevation: 4,
  },
  eye: {
    width: 13,
    height: 13,
    borderRadius: 7,
    borderWidth: 2,
    borderColor: "#67E8F9",
  },
  mouthBar: {
    width: 18,
    height: 3,
    borderRadius: 2,
    marginTop: 8,
    opacity: 0.85,
  },
  crown: {
    position: "absolute",
    top: -14,
    fontSize: 16,
    fontWeight: "900",
  },
  shellChip: {
    position: "absolute",
    bottom: -5,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
    backgroundColor: "rgba(15, 23, 42, 0.55)",
  },
  feet: {
    flexDirection: "row",
    gap: 18,
    marginTop: -2,
  },
  foot: {
    width: 16,
    height: 6,
    borderRadius: 4,
    opacity: 0.85,
  },
});
