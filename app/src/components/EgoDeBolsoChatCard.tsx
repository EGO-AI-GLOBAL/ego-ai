import { router } from "expo-router";
import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View, type DimensionValue } from "react-native";
import type { WellnessJourney } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { CompanionSprite } from "./companion/CompanionSprite";
import { PocketCompanionShareModal } from "./PocketCompanionShareModal";

type Props = {
  colors: AppColors;
  journey?: WellnessJourney;
  onCareHint?: (message: string) => void;
};

/** Mini-card EGO de Bolso no chat — missão do dia + postar. */
export function EgoDeBolsoChatCard({ colors, journey, onCareHint }: Props) {
  const [shareOpen, setShareOpen] = useState(false);

  if (!journey) return null;

  const care = journey.care_percent ?? Math.round((journey.progress ?? 0) * 100);
  const fillWidth = `${Math.max(care, care > 0 ? 8 : 0)}%` as DimensionValue;
  const pending = journey.steps?.filter((s) => !s.done) ?? [];
  const stage = journey.companion_stage ?? "egg";

  const onCare = () => {
    const key = pending[0]?.key ?? "";
    if (key.includes("agenda") || key.includes("habit") || key.includes("reminder")) {
      router.push("/(main)/agenda");
      return;
    }
    if (key.includes("checkin")) {
      router.push("/(main)/daily-care");
      return;
    }
    onCareHint?.(`Missão de hoje: ${journey.today_task}`);
  };

  return (
    <>
      <View style={[styles.wrap, { backgroundColor: colors.bgCard, borderColor: colors.primary }]}>
        <Pressable onPress={() => router.push("/(main)/wellness-journey")} style={styles.row}>
          <CompanionSprite stage={stage} size={52} happy={journey.level_complete} />
          <View style={styles.body}>
            <Text style={[styles.badge, { color: colors.primary }]}>EGO DE BOLSO 🥚</Text>
            <Text style={[styles.level, { color: colors.text }]} numberOfLines={1}>
              Nível {journey.level}/{journey.max_level} · {journey.title}
            </Text>
            <View style={[styles.track, { backgroundColor: colors.border }]}>
              <View
                style={[styles.fill, { backgroundColor: colors.primary, width: fillWidth }]}
              />
            </View>
            <Text style={[styles.task, { color: colors.textMuted }]} numberOfLines={2}>
              Hoje: {journey.today_task}
            </Text>
          </View>
        </Pressable>
        <View style={styles.actions}>
          <Pressable onPress={onCare} style={[styles.btn, { backgroundColor: colors.primary }]}>
            <Text style={styles.btnText}>Cuidar agora</Text>
          </Pressable>
          <Pressable
            onPress={() => setShareOpen(true)}
            style={[styles.btnOutline, { borderColor: colors.primary }]}
          >
            <Text style={[styles.btnOutlineText, { color: colors.primary }]}>Postar</Text>
          </Pressable>
        </View>
      </View>

      <PocketCompanionShareModal
        colors={colors}
        journey={journey}
        visible={shareOpen}
        onClose={() => setShareOpen(false)}
      />
    </>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: 14,
    borderWidth: 1.5,
    padding: 12,
    marginBottom: 12,
  },
  row: { flexDirection: "row", alignItems: "center", gap: 10 },
  body: { flex: 1 },
  badge: { fontSize: 10, fontWeight: "900", letterSpacing: 0.4 },
  level: { fontSize: 13, fontWeight: "800", marginTop: 2 },
  track: {
    height: 5,
    borderRadius: 3,
    overflow: "hidden",
    marginTop: 6,
    marginBottom: 4,
  },
  fill: { height: "100%", borderRadius: 3 },
  task: { fontSize: 11, lineHeight: 15 },
  actions: { flexDirection: "row", gap: 8, marginTop: 10 },
  btn: {
    flex: 1,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "800", fontSize: 13 },
  btnOutline: {
    flex: 1,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: "center",
    borderWidth: 1.5,
  },
  btnOutlineText: { fontWeight: "800", fontSize: 13 },
});
