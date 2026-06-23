import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";

export type CompanionStage = "egg" | "hatchling" | "teen" | "adult";

type Props = {
  stage?: string;
  size?: number;
  happy?: boolean;
};

export function CompanionSprite({ stage = "egg", size = 100, happy = false }: Props) {
  const s = (stage as CompanionStage) || "egg";
  const wobble = useRef(new Animated.Value(0)).current;

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
        <View style={[styles.egg, { width: size * 0.7, height: size, borderRadius: size * 0.35 }]}>
          <View style={styles.eggShine} />
          <View style={[styles.eggSpot, { width: size * 0.15, height: size * 0.15 }]} />
        </View>
      </Animated.View>
    );
  }

  const bodyColor = s === "hatchling" ? "#FFE566" : s === "teen" ? "#7DD3FC" : "#A78BFA";
  const bodyDark = s === "hatchling" ? "#E5C235" : s === "teen" ? "#38BDF8" : "#7C3AED";
  const bodyH = s === "adult" ? size * 0.85 : size * 0.75;

  return (
    <Animated.View style={[styles.center, { transform: [{ rotate }] }]}>
      <View
        style={[
          styles.birdBody,
          {
            width: size * 0.82,
            height: bodyH,
            borderRadius: size * 0.41,
            backgroundColor: bodyColor,
            borderColor: bodyDark,
          },
        ]}
      >
        <View style={styles.birdEyes}>
          <View style={styles.birdEye} />
          <View style={styles.birdEye} />
        </View>
        <View style={[styles.beak, { borderBottomColor: "#F59E0B" }]} />
        {s === "adult" ? <Text style={styles.crown}>👑</Text> : null}
        {s === "hatchling" ? (
          <View style={[styles.shell, { backgroundColor: "#FFF8E7" }]}>
            <Text style={{ fontSize: 10 }}>🥚</Text>
          </View>
        ) : null}
      </View>
      <View style={styles.birdFeet}>
        <View style={[styles.birdFoot, { backgroundColor: bodyDark }]} />
        <View style={[styles.birdFoot, { backgroundColor: bodyDark }]} />
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: "center" },
  egg: {
    backgroundColor: "#FFF8E7",
    borderWidth: 3,
    borderColor: "#E8D5B5",
    alignItems: "center",
    justifyContent: "center",
  },
  eggShine: {
    position: "absolute",
    top: 12,
    left: 14,
    width: 14,
    height: 22,
    borderRadius: 8,
    backgroundColor: "rgba(255,255,255,0.55)",
    transform: [{ rotate: "-20deg" }],
  },
  eggSpot: {
    borderRadius: 999,
    backgroundColor: "#F5D0A8",
    opacity: 0.7,
    marginTop: 12,
  },
  birdBody: { borderWidth: 3, alignItems: "center", justifyContent: "center" },
  birdEyes: { flexDirection: "row", gap: 14, marginTop: 4 },
  birdEye: { width: 12, height: 12, borderRadius: 6, backgroundColor: "#1E293B" },
  beak: {
    width: 0,
    height: 0,
    borderLeftWidth: 7,
    borderRightWidth: 7,
    borderBottomWidth: 10,
    borderLeftColor: "transparent",
    borderRightColor: "transparent",
    marginTop: 4,
  },
  crown: { position: "absolute", top: -16, fontSize: 18 },
  shell: {
    position: "absolute",
    bottom: -6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  birdFeet: { flexDirection: "row", gap: 16, marginTop: -2 },
  birdFoot: { width: 18, height: 8, borderRadius: 6 },
});
