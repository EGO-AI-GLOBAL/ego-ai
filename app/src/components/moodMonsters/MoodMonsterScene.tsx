import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { moodKeyOrDefault, resolveMoodLabel } from "@/constants/moodMonsters";
import { MoodGardenScene } from "./MoodGardenScene";
import { MoodMonsterIllustration } from "./MoodMonsterIllustration";

type Props = {
  colors: AppColors;
  care: DailyCareInfo;
  celebrate?: boolean;
  previewMood?: string;
  /** Pet sticky no topo com vídeo — cena fica só jardim + texto. */
  hidePet?: boolean;
};

export function MoodMonsterScene({
  colors,
  care,
  celebrate = false,
  previewMood,
  hidePet = false,
}: Props) {
  const days = care.current ?? 0;
  const moodKey = previewMood ?? (care.checked_today ? care.last_mood : undefined);
  const displayKey = moodKeyOrDefault(moodKey);
  const moodMeta = (care.moods ?? []).find((m) => m.key === displayKey);
  const displayLabel = resolveMoodLabel(care.moods, displayKey, moodMeta?.label);
  const gentleness = care.gentleness;
  const line =
    care.monster_line ||
    (care.checked_today
      ? `${displayLabel} está no jardim hoje.`
      : "Quem vai aparecer no jardim hoje?");
  const mirrorLine = gentleness?.mirror_line?.trim();
  const heldNote = gentleness?.held_note?.trim();

  return (
    <MoodGardenScene
      gardenStage={care.garden_stage}
      days={days}
      gardenLabel={care.garden_label}
      gardenEmoji={care.garden_emoji}
      seeds={care.seeds ?? 0}
      decorUnlocked={care.decor_unlocked}
      shopOwned={care.shop_owned}
      atRisk={care.at_risk}
      nightMode={Boolean(gentleness?.night_garden || gentleness?.sunday_garden)}
      gentleMode={Boolean(gentleness?.gentle_mode)}
    >
      {hidePet ? null : (
        <MoodMonsterIllustration moodKey={displayKey} size={116} celebrate={celebrate} />
      )}
      {hidePet ? null : <Text style={styles.name}>{displayLabel}</Text>}
      <Text style={[styles.line, { color: colors.text }]}>{line}</Text>
      {mirrorLine ? (
        <Text style={[styles.mirror, { color: colors.primary }]}>{mirrorLine}</Text>
      ) : null}
      {heldNote ? (
        <View style={[styles.heldNote, { backgroundColor: "rgba(255,255,255,0.5)" }]}>
          <Text style={styles.heldLabel}>💌 Carta guardada — só seu monstrinho</Text>
          <Text style={[styles.heldText, { color: colors.text }]} numberOfLines={2}>
            {heldNote}
          </Text>
        </View>
      ) : null}
      {care.daily_mission ? (
        <View style={[styles.mission, { backgroundColor: "rgba(255,255,255,0.45)" }]}>
          <Text style={styles.missionLabel}>Missão do dia</Text>
          <Text style={[styles.missionText, { color: colors.text }]}>{care.daily_mission}</Text>
        </View>
      ) : null}
    </MoodGardenScene>
  );
}

const styles = StyleSheet.create({
  name: {
    marginTop: 4,
    fontSize: 18,
    fontWeight: "900",
    color: "#1a3d1a",
    textShadowColor: "rgba(255,255,255,0.6)",
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  line: {
    marginTop: 6,
    fontSize: 13,
    fontWeight: "600",
    textAlign: "center",
    paddingHorizontal: 12,
    lineHeight: 18,
  },
  mirror: {
    marginTop: 6,
    fontSize: 12,
    fontWeight: "700",
    textAlign: "center",
    paddingHorizontal: 14,
    lineHeight: 17,
  },
  heldNote: {
    marginTop: 10,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    maxWidth: "92%",
  },
  heldLabel: { fontSize: 10, fontWeight: "900", color: "#5B4FCF", letterSpacing: 0.3 },
  heldText: { fontSize: 12, fontWeight: "600", marginTop: 4, lineHeight: 16, textAlign: "center" },
  mission: {
    marginTop: 10,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    maxWidth: "100%",
  },
  missionLabel: { fontSize: 10, fontWeight: "900", color: "#5B4FCF", letterSpacing: 0.4 },
  missionText: { fontSize: 12, fontWeight: "700", marginTop: 2, lineHeight: 16 },
});
