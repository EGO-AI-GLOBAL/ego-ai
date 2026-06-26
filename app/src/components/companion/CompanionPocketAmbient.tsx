import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";

import type { CompanionStage } from "./CompanionSprite";

type Props = {
  stage?: string;
  needsCare?: boolean;
};

function stageTier(stage?: string): number {
  const s = (stage as CompanionStage) || "egg";
  if (s === "adult") return 4;
  if (s === "teen") return 3;
  if (s === "hatchling") return 2;
  return 1;
}

/** Habitat animado do bolso — céu, nuvens, partículas (Dia 1 v2). */
export function CompanionPocketAmbient({ stage = "egg", needsCare = false }: Props) {
  const tier = stageTier(stage);
  const cloud1 = useRef(new Animated.Value(0)).current;
  const cloud2 = useRef(new Animated.Value(0)).current;
  const cloud3 = useRef(new Animated.Value(0)).current;
  const glow = useRef(new Animated.Value(0)).current;
  const particleA = useRef(new Animated.Value(0)).current;
  const particleB = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const drift1 = Animated.loop(
      Animated.timing(cloud1, {
        toValue: 1,
        duration: needsCare ? 34000 : 24000,
        useNativeDriver: true,
      })
    );
    const drift2 = Animated.loop(
      Animated.timing(cloud2, {
        toValue: 1,
        duration: needsCare ? 40000 : 32000,
        useNativeDriver: true,
      })
    );
    const drift3 = Animated.loop(
      Animated.timing(cloud3, {
        toValue: 1,
        duration: 28000,
        useNativeDriver: true,
      })
    );
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(glow, { toValue: 1, duration: 2200, useNativeDriver: true }),
        Animated.timing(glow, { toValue: 0, duration: 2200, useNativeDriver: true }),
      ])
    );
    const floatA = Animated.loop(
      Animated.sequence([
        Animated.timing(particleA, { toValue: 1, duration: 1600, useNativeDriver: true }),
        Animated.timing(particleA, { toValue: 0, duration: 1600, useNativeDriver: true }),
      ])
    );
    const floatB = Animated.loop(
      Animated.sequence([
        Animated.timing(particleB, { toValue: 1, duration: 2000, useNativeDriver: true }),
        Animated.timing(particleB, { toValue: 0, duration: 2000, useNativeDriver: true }),
      ])
    );

    drift1.start();
    drift2.start();
    if (tier >= 2) drift3.start();
    if (!needsCare) pulse.start();
    if (tier >= 2) floatA.start();
    if (tier >= 3) floatB.start();

    return () => {
      drift1.stop();
      drift2.stop();
      drift3.stop();
      pulse.stop();
      floatA.stop();
      floatB.stop();
    };
  }, [cloud1, cloud2, cloud3, glow, needsCare, particleA, particleB, tier]);

  const c1x = cloud1.interpolate({ inputRange: [0, 1], outputRange: [-28, 36] });
  const c2x = cloud2.interpolate({ inputRange: [0, 1], outputRange: [32, -36] });
  const c3x = cloud3.interpolate({ inputRange: [0, 1], outputRange: [-16, 24] });
  const glowScale = glow.interpolate({ inputRange: [0, 1], outputRange: [0.92, 1.06] });
  const glowOpacity = glow.interpolate({ inputRange: [0, 1], outputRange: [0.25, 0.55] });
  const pAy = particleA.interpolate({ inputRange: [0, 1], outputRange: [0, -10] });
  const pBy = particleB.interpolate({ inputRange: [0, 1], outputRange: [4, -8] });
  const pAOpacity = particleA.interpolate({ inputRange: [0, 1], outputRange: [0.35, 0.95] });
  const pBOpacity = particleB.interpolate({ inputRange: [0, 1], outputRange: [0.3, 0.9] });

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <View style={[styles.horizon, needsCare ? styles.horizonDim : null]} />
      {!needsCare ? (
        <Animated.View
          style={[
            styles.moonGlow,
            { opacity: glowOpacity, transform: [{ scale: glowScale }] },
          ]}
        />
      ) : null}
      <Animated.Text
        style={[styles.cloud, styles.cloudLg, { transform: [{ translateX: c1x }] }]}
      >
        ☁️
      </Animated.Text>
      <Animated.Text
        style={[styles.cloud, styles.cloudMd, { transform: [{ translateX: c2x }] }]}
      >
        ☁️
      </Animated.Text>
      {tier >= 2 ? (
        <Animated.Text
          style={[styles.cloud, styles.cloudSm, { transform: [{ translateX: c3x }] }]}
        >
          ☁️
        </Animated.Text>
      ) : null}
      {!needsCare ? (
        <Animated.Text style={[styles.orb, { transform: [{ scale: glowScale }] }]}>
          {tier >= 4 ? "🌙" : "✨"}
        </Animated.Text>
      ) : (
        <Text style={styles.orbMuted}>🌧️</Text>
      )}
      {tier >= 2 ? (
        <Animated.View style={[styles.particleDot, styles.particleLeft, { opacity: pAOpacity, transform: [{ translateY: pAy }] }]} />
      ) : null}
      {tier >= 3 ? (
        <>
          <Animated.Text style={[styles.spark, styles.sparkA, { opacity: pBOpacity, transform: [{ translateY: pBy }] }]}>
            ✨
          </Animated.Text>
          <Animated.Text style={[styles.spark, styles.sparkB, { opacity: pAOpacity, transform: [{ translateY: pAy }] }]}>
            💫
          </Animated.Text>
        </>
      ) : null}
      {tier >= 4 ? (
        <Animated.Text style={[styles.spark, styles.sparkC, { opacity: pBOpacity }]}>🌟</Animated.Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  horizon: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    height: "42%",
    backgroundColor: "rgba(34, 211, 238, 0.08)",
    borderTopLeftRadius: 120,
    borderTopRightRadius: 120,
  },
  horizonDim: {
    backgroundColor: "rgba(15, 23, 42, 0.35)",
  },
  moonGlow: {
    position: "absolute",
    right: 18,
    top: 10,
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: "rgba(250, 204, 21, 0.22)",
  },
  cloud: { position: "absolute", opacity: 0.5 },
  cloudLg: { left: "8%", top: 12, fontSize: 30 },
  cloudMd: { right: "6%", top: 28, fontSize: 24 },
  cloudSm: { left: "42%", top: 6, fontSize: 18, opacity: 0.38 },
  orb: { position: "absolute", right: 22, top: 16, fontSize: 28 },
  orbMuted: { position: "absolute", right: 22, top: 16, fontSize: 26, opacity: 0.85 },
  particleDot: {
    position: "absolute",
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#A5F3FC",
  },
  particleLeft: { left: "14%", top: 52 },
  spark: { position: "absolute", fontSize: 14 },
  sparkA: { left: "20%", top: 38 },
  sparkB: { right: "28%", top: 58 },
  sparkC: { left: "8%", top: 22, fontSize: 16 },
});
