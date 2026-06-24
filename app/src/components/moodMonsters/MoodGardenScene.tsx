import { LinearGradient } from "expo-linear-gradient";
import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { DailyCareDecor, DailyCareShopOwned } from "@/api/types";
import { DECOR_POSITIONS, GARDEN_DECOR, GARDEN_GRADIENTS, gardenStageFromDays } from "@/constants/moodMonsters";

type DecorItem = Pick<DailyCareDecor, "id" | "emoji">;

type Props = {
  gardenStage?: number;
  days?: number;
  gardenLabel?: string;
  gardenEmoji?: string;
  seeds?: number;
  decorUnlocked?: DailyCareDecor[];
  shopOwned?: DailyCareShopOwned[];
  children: React.ReactNode;
};

function renderDecor(items: DecorItem[], keyPrefix: string) {
  return items.map((item) => {
    const pos = DECOR_POSITIONS[item.id];
    if (!pos) return null;
    return (
      <Text
        key={`${keyPrefix}-${item.id}`}
        style={[
          styles.unlockDecor,
          {
            left: pos.left as `${number}%`,
            top: pos.top,
            fontSize: pos.size,
          },
        ]}
      >
        {item.emoji}
      </Text>
    );
  });
}

export function MoodGardenScene({
  gardenStage,
  days = 0,
  gardenLabel,
  gardenEmoji,
  seeds = 0,
  decorUnlocked = [],
  shopOwned = [],
  children,
}: Props) {
  const stage = gardenStage ?? gardenStageFromDays(days);
  const colors = GARDEN_GRADIENTS[stage] ?? GARDEN_GRADIENTS[1];
  const decor = GARDEN_DECOR[stage] ?? GARDEN_DECOR[1];

  return (
    <View style={styles.wrap}>
      <LinearGradient colors={[...colors]} style={styles.sky} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}>
        <View style={styles.topRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>
              {gardenEmoji ?? "🌱"} Jardim · {gardenLabel ?? "Semente"}
            </Text>
          </View>
          <View style={styles.seedsBadge}>
            <Text style={styles.seedsText}>🌰 {seeds}</Text>
          </View>
        </View>
        <View style={styles.decorRow}>
          {decor.map((d, i) => (
            <Text key={`d-${i}`} style={[styles.decor, { opacity: 0.55 + i * 0.12 }]}>
              {d}
            </Text>
          ))}
        </View>
        {renderDecor(decorUnlocked, "streak")}
        {renderDecor(shopOwned, "shop")}
        <View style={styles.ground} />
        <View style={styles.petArea}>{children}</View>
      </LinearGradient>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { borderRadius: 16, overflow: "hidden", marginBottom: 12 },
  sky: { minHeight: 210, paddingTop: 10, paddingHorizontal: 12 },
  topRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  badge: {
    backgroundColor: "rgba(255,255,255,0.35)",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },
  badgeText: { fontSize: 11, fontWeight: "800", color: "#1a3d1a" },
  seedsBadge: {
    backgroundColor: "rgba(255,255,255,0.5)",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },
  seedsText: { fontSize: 11, fontWeight: "900", color: "#5B4A1A" },
  decorRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginTop: 6,
    paddingHorizontal: 8,
  },
  decor: { fontSize: 22 },
  unlockDecor: { position: "absolute", zIndex: 2 },
  ground: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    height: 48,
    backgroundColor: "rgba(90,70,50,0.25)",
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
  },
  petArea: { alignItems: "center", justifyContent: "center", paddingVertical: 8, minHeight: 140 },
});
