import React, { useState } from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import * as Haptics from "expo-haptics";
import { submitDailyCareCalmMark } from "@/api/client";
import type { DailyCareInfo } from "@/api/types";
import { PausaBreathSession } from "@/components/pausa/PausaBreathSession";
import type { AppColors } from "@/theme/colors";
import { queueMonsterChatNotice } from "@/utils/monsterChatNotice";
import { resolveGentlePausaExercise } from "@/utils/resolveGentlePausa";

type Props = {
  colors: AppColors;
  care: DailyCareInfo;
  assistantName?: string;
  onUpdate: (care: DailyCareInfo) => void;
};

/** Ponte humor difícil → PAUSA 60s inline (sem sair do jardim). */
export function MoodCrisisBridgeCard({ colors, care, assistantName = "Luna", onUpdate }: Props) {
  const [pausaOpen, setPausaOpen] = useState(false);
  const [doneToday, setDoneToday] = useState(false);

  const bridge = care.gentleness?.crisis_bridge;
  if (!bridge?.show) return null;

  const exercise = resolveGentlePausaExercise(bridge);

  const onPausaComplete = async () => {
    setPausaOpen(false);
    setDoneToday(true);
    void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => undefined);
    const res = await submitDailyCareCalmMark();
    if (res?.daily_care) onUpdate(res.daily_care);
  };

  const openChat = () => {
    const draft =
      bridge.chat_draft?.trim() ||
      "Fiz a PAUSA no jardim e quero falar sobre como estou me sentindo.";
    void queueMonsterChatNotice(draft);
    router.push("/(main)/chat");
  };

  const openFullPausa = () => {
    router.push("/(main)/wellness-journey");
  };

  return (
    <>
      <View style={[styles.wrap, { borderColor: colors.primary, backgroundColor: colors.primaryTint }]}>
        <Text style={[styles.step, { color: colors.primary }]}>2º PASSO — PAUSA 1 MIN</Text>
        <Text style={[styles.title, { color: colors.text }]}>
          {bridge.title?.trim() || "Calma 1 min"}
        </Text>
        <Text style={[styles.sub, { color: colors.textMuted }]}>
          {bridge.subtitle?.trim() || "Respiração agora — sem sair do jardim. Conversar é opcional."}
        </Text>

        <Pressable
          onPress={() => setPausaOpen(true)}
          style={[styles.primaryBtn, { backgroundColor: colors.primary }]}
        >
          <Text style={styles.primaryText}>
            {doneToday ? "Repetir Calma 1 min" : "Começar Calma 1 min"}
          </Text>
        </Pressable>

        <View style={styles.row}>
          <Pressable onPress={openFullPausa} style={[styles.secondaryBtn, { borderColor: colors.border }]}>
            <Text style={[styles.secondaryText, { color: colors.text }]}>Mais técnicas Calma 1 min</Text>
          </Pressable>
          <Pressable onPress={openChat} style={[styles.secondaryBtn, { borderColor: colors.border }]}>
            <Text style={[styles.secondaryText, { color: colors.text }]}>Falar com {assistantName}</Text>
          </Pressable>
        </View>

        <Pressable
          onPress={() => {
            void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => undefined);
            setDoneToday(true);
          }}
          style={styles.silenceBtn}
        >
          <Text style={[styles.silenceText, { color: colors.textMuted }]}>
            Ficar em silêncio — sem conversa agora
          </Text>
        </Pressable>

        <Pressable onPress={() => void Linking.openURL("tel:188")}>
          <Text style={[styles.cvv, { color: colors.textMuted }]}>{bridge.cvv_line}</Text>
        </Pressable>
      </View>

      <PausaBreathSession
        colors={colors}
        visible={pausaOpen}
        assistantName={assistantName}
        durationSeconds={exercise.duration_seconds}
        title={exercise.title}
        subtitle={exercise.subtitle}
        inhaleSeconds={exercise.breath_inhale ?? 4}
        exhaleSeconds={exercise.breath_exhale ?? 6}
        onClose={() => setPausaOpen(false)}
        onComplete={() => void onPausaComplete()}
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
  step: { fontSize: 10, fontWeight: "900", letterSpacing: 0.5, marginBottom: 6 },
  title: { fontSize: 18, fontWeight: "900" },
  sub: { fontSize: 12, marginTop: 6, lineHeight: 17, marginBottom: 12 },
  primaryBtn: { borderRadius: 12, paddingVertical: 14, alignItems: "center" },
  primaryText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  row: { flexDirection: "row", gap: 8, marginTop: 10 },
  secondaryBtn: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    paddingVertical: 10,
    alignItems: "center",
  },
  secondaryText: { fontSize: 12, fontWeight: "700", textAlign: "center" },
  cvv: { marginTop: 12, fontSize: 11, fontWeight: "600", textAlign: "center" },
  silenceBtn: { marginTop: 10, paddingVertical: 6, alignItems: "center" },
  silenceText: { fontSize: 12, fontWeight: "700", textAlign: "center" },
});
