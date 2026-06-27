import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import React from "react";
import { Pressable, StyleSheet, Text, View, type DimensionValue } from "react-native";
import type { WellnessJourney } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { egoDeBolsoDailyCarePercent } from "@/utils/egoDeBolsoDailyCare";
import { companionMoodLine, companionNeedsCare } from "@/utils/egoDeBolsoCompanionMood";
import { resolveEgoDeBolsoCareRoute } from "@/utils/egoDeBolsoCareRoute";
import { CompanionPocketAmbient } from "./CompanionPocketAmbient";
import { CompanionSprite } from "./CompanionSprite";
import { CompanionNameChip } from "./CompanionNameChip";

type Props = {
  colors: AppColors;
  journey: WellnessJourney;
  onCompanionNameChange?: (name: string) => void;
};

export function CompanionPocketScene({ colors, journey, onCompanionNameChange }: Props) {
  const stage = journey.companion_stage ?? "egg";
  const care = egoDeBolsoDailyCarePercent(journey);
  const fillWidth = `${Math.max(care, care > 0 ? 8 : 0)}%` as DimensionValue;
  const needsCare = companionNeedsCare(journey);
  const moodLine = companionMoodLine(journey);
  const missionDone =
    Boolean(journey.level_complete) ||
    Boolean(journey.mission_done_today) ||
    care >= 100;
  const celebrate =
    Boolean(journey.show_level_up) ||
    (Boolean(journey.level_complete) && !journey.mission_done_today);

  return (
    <View style={styles.wrap}>
      <LinearGradient
        colors={["#12082A", "#2D1B4E", "#5B3FA8", "#7C5CE0"]}
        style={styles.bg}
        start={{ x: 0.2, y: 0 }}
        end={{ x: 0.8, y: 1 }}
      >
        <CompanionPocketAmbient stage={stage} needsCare={needsCare} />
        <View style={styles.foreground}>
          <Text style={styles.stageBadge}>
            {journey.companion_sprite_emoji ?? "🥚"}{" "}
            {journey.companion_stage_label ?? "Ovo"}
          </Text>
          {onCompanionNameChange ? (
            <CompanionNameChip
              journey={journey}
              variant="pocket"
              onSaved={onCompanionNameChange}
            />
          ) : null}
          <CompanionSprite
            stage={stage}
            size={108}
            happy={missionDone}
            celebrate={celebrate}
          />
          <Text style={styles.careLabel}>Cuidado {care}%</Text>
          <View style={styles.careTrack}>
            <View style={[styles.careFill, { width: fillWidth }]} />
          </View>
          {missionDone ? (
            <Text style={styles.celebrateHint}>Missão concluída — energia no bolso ⚡</Text>
          ) : (
            <Text style={styles.pocketHint}>Companheiro digital — energia no bolso 💜</Text>
          )}
          {moodLine ? (
            <Text style={[styles.moodLine, needsCare ? styles.moodLonely : styles.moodHappy]}>
              {moodLine}
            </Text>
          ) : null}
        </View>
      </LinearGradient>
      {needsCare ? (
        <Pressable
          onPress={() => router.push(resolveEgoDeBolsoCareRoute(journey))}
          style={styles.careBtnOuter}
        >
          <LinearGradient
            colors={[colors.primary, colors.primaryLight]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.careBtn}
          >
            <Text style={styles.careBtnText}>Cuidar agora</Text>
          </LinearGradient>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 12, borderRadius: 16, overflow: "hidden" },
  bg: {
    alignItems: "center",
    paddingVertical: 16,
    paddingHorizontal: 14,
    minHeight: 228,
    overflow: "hidden",
  },
  foreground: { alignItems: "center", width: "100%", zIndex: 2 },
  stageBadge: {
    fontSize: 12,
    fontWeight: "900",
    color: "#FFE566",
    marginBottom: 4,
    letterSpacing: 0.3,
  },
  careLabel: { marginTop: 8, fontSize: 14, fontWeight: "800", color: "#fff" },
  careTrack: {
    width: "88%",
    height: 12,
    borderRadius: 6,
    overflow: "hidden",
    marginTop: 6,
    backgroundColor: "rgba(255,255,255,0.18)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
  },
  careFill: {
    height: "100%",
    borderRadius: 6,
    backgroundColor: "#FFE566",
    shadowColor: "#FFE566",
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 6,
  },
  pocketHint: {
    marginTop: 8,
    fontSize: 11,
    color: "rgba(255,255,255,0.75)",
    fontWeight: "600",
  },
  celebrateHint: {
    marginTop: 8,
    fontSize: 12,
    color: "#A5F3FC",
    fontWeight: "800",
  },
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
  careBtnOuter: {
    marginHorizontal: 14,
    marginBottom: 12,
    marginTop: -4,
    borderRadius: 12,
    overflow: "hidden",
    shadowColor: "#7C3AED",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 8,
    elevation: 4,
  },
  careBtn: {
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  careBtnText: { color: "#fff", fontWeight: "800", fontSize: 14 },
});
