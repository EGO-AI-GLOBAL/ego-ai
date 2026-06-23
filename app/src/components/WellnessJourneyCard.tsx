import { router } from "expo-router";
import React, { useEffect, useRef } from "react";
import { Alert, Pressable, StyleSheet, Text, View, type DimensionValue } from "react-native";
import type { WellnessJourney } from "@/api/types";
import { dismissWellnessLevelUp } from "@/api/client";
import type { AppColors } from "@/theme/colors";
import { shareWellnessJourneyWhatsApp, shareWellnessJourneyNative } from "@/utils/whatsappShare";

type Props = {
  colors: AppColors;
  journey?: WellnessJourney;
  onJourneyUpdate?: (j: WellnessJourney) => void;
};

export function WellnessJourneyCard({ colors, journey, onJourneyUpdate }: Props) {
  const levelUpShown = useRef(false);

  useEffect(() => {
    if (!journey?.show_level_up || levelUpShown.current) return;
    levelUpShown.current = true;
    const finished = journey.journey_finished;
    Alert.alert(
      finished ? "Jornada completa! 🎉" : `Nível ${journey.level} desbloqueado!`,
      finished
        ? `Você completou os ${journey.max_level} níveis de cuidado. Partilhe com quem precisa de apoio.`
        : `${journey.emoji} ${journey.title} — ${journey.subtitle}`,
      [
        {
          text: "OK",
          onPress: () => {
            void dismissWellnessLevelUp().then((next) => {
              if (next) onJourneyUpdate?.(next);
            });
          },
        },
        finished
          ? {
              text: "Desafiar amigos",
              onPress: () => {
                void shareWellnessJourneyWhatsApp(journey);
                void dismissWellnessLevelUp().then((next) => {
                  if (next) onJourneyUpdate?.(next);
                });
              },
            }
          : { text: "Continuar", style: "cancel" },
      ]
    );
  }, [journey, onJourneyUpdate]);

  if (!journey) return null;

  const pct = Math.round(Math.min(1, Math.max(0, journey.progress)) * 100);
  const fillWidth = `${Math.max(pct, pct > 0 ? 6 : 0)}%` as DimensionValue;
  const pending = journey.steps?.filter((s) => !s.done) ?? [];

  return (
    <View
      style={[
        styles.wrap,
        { backgroundColor: colors.primaryTint, borderColor: colors.primary },
      ]}
    >
      <View style={styles.headRow}>
        <Text style={styles.emoji}>{journey.emoji}</Text>
        <View style={{ flex: 1 }}>
          <Text style={[styles.level, { color: colors.primary }]}>
            Nível {journey.level}/{journey.max_level} · {journey.title}
          </Text>
          <Text style={[styles.sub, { color: colors.textMuted }]}>{journey.subtitle}</Text>
        </View>
      </View>

      <View style={[styles.track, { backgroundColor: colors.border }]}>
        <View
          style={[styles.fill, { backgroundColor: colors.primary, width: fillWidth }]}
        />
      </View>

      <Text style={[styles.task, { color: colors.text }]}>
        Hoje: {journey.today_task}
      </Text>
      <Text style={[styles.why, { color: colors.textMuted }]}>{journey.why}</Text>

      {pending.length > 0 ? (
        <Text style={[styles.pending, { color: colors.textMuted }]}>
          Falta: {pending.map((s) => s.label).join(" · ")}
        </Text>
      ) : null}

      {journey.plan_nudge ? (
        <Pressable onPress={() => router.push("/(main)/plans")} style={styles.nudge}>
          <Text style={[styles.nudgeText, { color: colors.primary }]}>
            💡 {journey.plan_nudge} — Ver planos
          </Text>
        </Pressable>
      ) : null}

      <Pressable
        onPress={() => void shareWellnessJourneyWhatsApp(journey)}
        style={[styles.shareBtn, { borderColor: "#25D366" }]}
      >
        <Text style={styles.shareText}>WhatsApp — desafiar amigos</Text>
      </Pressable>
      <Pressable
        onPress={() => void shareWellnessJourneyNative(journey)}
        style={[styles.shareBtn, { borderColor: colors.primary, marginTop: 8 }]}
      >
        <Text style={[styles.shareText, { color: colors.primary }]}>
          Instagram / Stories (links na legenda)
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: 14,
    borderWidth: 1.5,
    padding: 14,
    marginBottom: 12,
  },
  headRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 10 },
  emoji: { fontSize: 28 },
  level: { fontSize: 14, fontWeight: "800" },
  sub: { fontSize: 12, marginTop: 2 },
  track: { height: 6, borderRadius: 3, overflow: "hidden", marginBottom: 10 },
  fill: { height: "100%", borderRadius: 3 },
  task: { fontSize: 15, fontWeight: "700", lineHeight: 21 },
  why: { fontSize: 12, marginTop: 6, lineHeight: 17 },
  pending: { fontSize: 11, marginTop: 6, fontStyle: "italic" },
  nudge: { marginTop: 10 },
  nudgeText: { fontSize: 12, fontWeight: "600", lineHeight: 17 },
  shareBtn: {
    marginTop: 12,
    borderWidth: 1.5,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: "center",
  },
  shareText: { color: "#128C7E", fontWeight: "800", fontSize: 13 },
});
