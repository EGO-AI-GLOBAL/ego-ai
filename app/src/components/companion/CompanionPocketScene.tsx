import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import React from "react";
import { Pressable, StyleSheet, Text, View, type DimensionValue } from "react-native";
import type { WellnessJourney } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import {
  companionMoodLine,
  companionNeedsCare,
} from "@/utils/egoDeBolsoCompanionMood";
import { resolveEgoDeBolsoCareRoute } from "@/utils/egoDeBolsoCareRoute";
import { CompanionSprite } from "./CompanionSprite";

type Props = {
  colors: AppColors;
  journey: WellnessJourney;
};

export function CompanionPocketScene({ colors, journey }: Props) {
  const stage = journey.companion_stage ?? "egg";
  const care = journey.care_percent ?? Math.round((journey.progress ?? 0) * 100);
  const fillWidth = `${Math.max(care, care > 0 ? 8 : 0)}%` as DimensionValue;
  const needsCare = companionNeedsCare(journey);
  const moodLine = companionMoodLine(journey);

  return (
    <View style={styles.wrap}>
      <LinearGradient
        colors={["#2D1B4E", "#4A3080", "#6B4FCF"]}
        style={styles.bg}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
      >
        <Text style={styles.stageBadge}>
          {journey.companion_sprite_emoji ?? "🥚"} {journey.companion_stage_label ?? "Ovo"}
        </Text>
        <CompanionSprite stage={stage} size={108} happy={journey.level_complete} />
        <Text style={styles.careLabel}>Cuidado {care}%</Text>
        <View style={[styles.careTrack, { backgroundColor: "rgba(255,255,255,0.2)" }]}>
          <View style={[styles.careFill, { width: fillWidth, backgroundColor: "#FFE566" }]} />
        </View>
        <Text style={styles.pocketHint}>Estilo anos 90 — no bolso, com a Luna 💜</Text>
        {moodLine ? (
          <Text style={[styles.moodLine, needsCare ? styles.moodLonely : styles.moodHappy]}>
            {moodLine}
          </Text>
        ) : null}
      </LinearGradient>
      {needsCare ? (
        <Pressable
          onPress={() => router.push(resolveEgoDeBolsoCareRoute(journey))}
          style={[styles.careBtn, { backgroundColor: colors.primary }]}
        >
          <Text style={styles.careBtnText}>Cuidar agora</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 12, borderRadius: 16, overflow: "hidden" },
  bg: { alignItems: "center", paddingVertical: 16, paddingHorizontal: 14 },
  stageBadge: {
    fontSize: 12,
    fontWeight: "900",
    color: "#FFE566",
    marginBottom: 4,
    letterSpacing: 0.3,
  },
  careLabel: { marginTop: 8, fontSize: 13, fontWeight: "800", color: "#fff" },
  careTrack: {
    width: "88%",
    height: 10,
    borderRadius: 5,
    overflow: "hidden",
    marginTop: 6,
  },
  careFill: { height: "100%", borderRadius: 5 },
  pocketHint: { marginTop: 8, fontSize: 11, color: "rgba(255,255,255,0.75)", fontWeight: "600" },
  moodLine: {
    marginTop: 10,
    fontSize: 12,
    fontWeight: "700",
    textAlign: "center",
    lineHeight: 17,
    paddingHorizontal: 8,
  },
  moodLonely: { color: "#FFE566" },
  moodHappy: { color: "rgba(255,255,255,0.9)" },
  careBtn: {
    marginHorizontal: 14,
    marginBottom: 12,
    marginTop: -4,
    borderRadius: 12,
    paddingVertical: 11,
    alignItems: "center",
  },
  careBtnText: { color: "#fff", fontWeight: "800", fontSize: 14 },
});
