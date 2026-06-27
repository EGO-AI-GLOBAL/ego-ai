import { router } from "expo-router";
import React, { useEffect, useRef, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View, type DimensionValue } from "react-native";
import type { AccessInfo, WellnessJourney } from "@/api/types";
import { dismissWellnessLevelUp } from "@/api/client";
import type { AppColors } from "@/theme/colors";
import { CompanionPocketScene } from "@/components/companion/CompanionPocketScene";
import { EgoDeBolsoTrialNudge } from "@/components/EgoDeBolsoTrialNudge";
import { egoDeBolsoDailyCarePercent } from "@/utils/egoDeBolsoDailyCare";
import { formatWellnessPendingLine } from "@/utils/egoDeBolsoStepHints";
import {
  egoDeBolsoDayCompleteMessage,
  egoDeBolsoMissionsComplete,
} from "@/utils/egoDeBolsoCompanionMood";
import { companionNeedsNameSetup } from "@/utils/egoDeBolsoCompanionName";
import { PocketCompanionShareModal } from "./PocketCompanionShareModal";

type Props = {
  colors: AppColors;
  journey?: WellnessJourney;
  onJourneyUpdate?: (j: WellnessJourney) => void;
  access?: AccessInfo | null;
};

export function WellnessJourneyCard({ colors, journey, onJourneyUpdate, access }: Props) {
  const levelUpShown = useRef(false);
  const namePromptShown = useRef(false);
  const [shareOpen, setShareOpen] = useState(false);

  const mergeCompanionName = (name: string) => {
    if (!journey) return;
    onJourneyUpdate?.({
      ...journey,
      companion_name: name,
      companion_name_setup_done: true,
    });
  };

  useEffect(() => {
    if (!journey || namePromptShown.current) return;
    if (!companionNeedsNameSetup(journey)) return;
    namePromptShown.current = true;
    Alert.alert(
      "Dê um nome ao bolso",
      "Escolha um nome para o seu companheiro — aparece nas missões e no lembrete das 18h.",
      [{ text: "OK" }]
    );
  }, [journey]);

  useEffect(() => {
    if (!journey?.show_level_up || levelUpShown.current) return;
    levelUpShown.current = true;
    const finished = journey.journey_finished;
    Alert.alert(
      finished ? "EGO de Bolso completo! 🎉" : `EGO de Bolso — nível ${journey.level}!`,
      finished
        ? `Você completou os ${journey.max_level} níveis. Partilhe com quem precisa de apoio.`
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
              text: "Postar",
              onPress: () => {
                setShareOpen(true);
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

  const pct = egoDeBolsoDailyCarePercent(journey);
  const fillWidth = `${Math.max(pct, pct > 0 ? 6 : 0)}%` as DimensionValue;
  const pending = journey.steps?.filter((s) => !s.done) ?? [];
  const dayComplete = egoDeBolsoMissionsComplete(journey);

  return (
    <>
      <View
        style={[
          styles.wrap,
          { backgroundColor: colors.primaryTint, borderColor: colors.primary },
        ]}
      >
        <EgoDeBolsoTrialNudge colors={colors} access={access} journey={journey} />

        <View style={styles.headRow}>
          <Text style={styles.emoji}>{journey.emoji}</Text>
          <View style={{ flex: 1 }}>
            <Text style={[styles.badge, { color: colors.primary }]}>EGO DE BOLSO 🥚</Text>
            <Text style={[styles.level, { color: colors.text }]}>
              Nível {journey.level}/{journey.max_level} · {journey.title}
              {journey.missions_per_day && !dayComplete
                ? ` · ${journey.missions_today ?? 0}/${journey.missions_per_day} hoje`
                : ""}
            </Text>
            <Text style={[styles.sub, { color: colors.textMuted }]}>{journey.subtitle}</Text>
          </View>
        </View>

        <CompanionPocketScene
          colors={colors}
          journey={journey}
          onCompanionNameChange={mergeCompanionName}
        />

        <View style={[styles.track, { backgroundColor: colors.border }]}>
          <View style={[styles.fill, { backgroundColor: colors.primary, width: fillWidth }]} />
        </View>

        <Text style={[styles.task, { color: dayComplete ? colors.primary : colors.text }]}>
          {dayComplete ? egoDeBolsoDayCompleteMessage(journey) : `Hoje: ${journey.today_task}`}
        </Text>
        {!dayComplete ? (
          <Text style={[styles.why, { color: colors.textMuted }]}>{journey.why}</Text>
        ) : null}

        {!dayComplete && pending.length > 0 ? (
          <Text style={[styles.pending, { color: colors.textMuted }]}>
            Falta: {formatWellnessPendingLine(pending)}
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
          onPress={() => setShareOpen(true)}
          style={[styles.shareBtn, { backgroundColor: colors.primary }]}
        >
          <Text style={styles.shareText}>Postar e desafiar amigos</Text>
        </Pressable>
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
    padding: 14,
    marginBottom: 12,
  },
  headRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 10 },
  emoji: { fontSize: 28 },
  badge: { fontSize: 10, fontWeight: "900", letterSpacing: 0.5 },
  level: { fontSize: 14, fontWeight: "800", marginTop: 2 },
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
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  shareText: { color: "#fff", fontWeight: "800", fontSize: 14 },
});
