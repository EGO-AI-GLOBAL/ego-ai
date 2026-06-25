import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";

type Props = {
  stage: number;
  atRisk?: boolean;
};

/** Céu vivo — nuvens, sol, partículas (Fase 5 visual). */
export function MoodGardenAmbient({ stage, atRisk = false }: Props) {
  const cloud1 = useRef(new Animated.Value(0)).current;
  const cloud2 = useRef(new Animated.Value(0)).current;
  const sunPulse = useRef(new Animated.Value(1)).current;
  const sparkle = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const drift1 = Animated.loop(
      Animated.timing(cloud1, { toValue: 1, duration: 22000, useNativeDriver: true })
    );
    const drift2 = Animated.loop(
      Animated.timing(cloud2, { toValue: 1, duration: 30000, useNativeDriver: true })
    );
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(sunPulse, { toValue: 1.08, duration: 2400, useNativeDriver: true }),
        Animated.timing(sunPulse, { toValue: 1, duration: 2400, useNativeDriver: true }),
      ])
    );
    const twinkle = Animated.loop(
      Animated.sequence([
        Animated.timing(sparkle, { toValue: 1, duration: 800, useNativeDriver: true }),
        Animated.timing(sparkle, { toValue: 0.2, duration: 800, useNativeDriver: true }),
      ])
    );
    drift1.start();
    drift2.start();
    if (!atRisk) pulse.start();
    if (stage >= 4) twinkle.start();
    return () => {
      drift1.stop();
      drift2.stop();
      pulse.stop();
      twinkle.stop();
    };
  }, [atRisk, cloud1, cloud2, sparkle, stage, sunPulse]);

  const c1x = cloud1.interpolate({ inputRange: [0, 1], outputRange: [-20, 40] });
  const c2x = cloud2.interpolate({ inputRange: [0, 1], outputRange: [30, -30] });

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Animated.Text style={[styles.cloud, { transform: [{ translateX: c1x }] }]}>☁️</Animated.Text>
      <Animated.Text style={[styles.cloud2, { transform: [{ translateX: c2x }] }]}>☁️</Animated.Text>
      {!atRisk ? (
        <Animated.Text style={[styles.sun, { transform: [{ scale: sunPulse }] }]}>
          {stage >= 5 ? "🌤️" : "☀️"}
        </Animated.Text>
      ) : (
        <Text style={styles.rainCloud}>🌧️</Text>
      )}
      {stage >= 3 ? (
        <Animated.Text style={[styles.butterfly, { opacity: sparkle }]}>🦋</Animated.Text>
      ) : null}
      {stage >= 4 ? (
        <>
          <Animated.Text style={[styles.sparkA, { opacity: sparkle }]}>✨</Animated.Text>
          <Animated.Text style={[styles.sparkB, { opacity: sparkle }]}>✨</Animated.Text>
        </>
      ) : null}
      {stage >= 5 ? <Text style={styles.rainbowHint}>🌈</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  cloud: { position: "absolute", left: "12%", top: 18, fontSize: 28, opacity: 0.55 },
  cloud2: { position: "absolute", right: "8%", top: 32, fontSize: 22, opacity: 0.45 },
  sun: { position: "absolute", right: 14, top: 8, fontSize: 30 },
  rainCloud: { position: "absolute", right: 14, top: 8, fontSize: 28 },
  butterfly: { position: "absolute", left: "62%", top: 44, fontSize: 20 },
  sparkA: { position: "absolute", left: "18%", top: 56, fontSize: 14 },
  sparkB: { position: "absolute", right: "22%", top: 70, fontSize: 12 },
  rainbowHint: { position: "absolute", left: "4%", top: 6, fontSize: 22, opacity: 0.7 },
});
