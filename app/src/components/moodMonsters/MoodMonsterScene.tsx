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
};

export function MoodMonsterScene({ colors, care, celebrate = false, previewMood }: Props) {
  const days = care.current ?? 0;
  const moodKey = previewMood ?? (care.checked_today ? care.last_mood : undefined);
  const displayKey = moodKeyOrDefault(moodKey);
  const moodMeta = (care.moods ?? []).find((m) => m.key === displayKey);
  const displayLabel = resolveMoodLabel(care.moods, displayKey, moodMeta?.label);
  const line =
    care.monster_line ||
    (care.checked_today
      ? `${displayLabel} está no jardim hoje.`
      : "Quem vai aparecer no jardim hoje?");

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
    >
      <MoodMonsterIllustration moodKey={displayKey} size={116} celebrate={celebrate} />
      <Text style={styles.name}>{displayLabel}</Text>
      <Text style={[styles.line, { color: colors.text }]}>{line}</Text>
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
