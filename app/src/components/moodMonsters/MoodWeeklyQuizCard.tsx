import React, { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import * as Haptics from "expo-haptics";
import { submitDailyCareQuiz } from "@/api/client";
import type { DailyCareInfo, DailyCareWeeklyQuiz } from "@/api/types";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  quiz?: DailyCareWeeklyQuiz | null;
  onUpdate: (care: DailyCareInfo) => void;
};

/** Quiz semanal de bem-estar — 1 pergunta, recompensa sementes. */
export function MoodWeeklyQuizCard({ colors, quiz, onUpdate }: Props) {
  const [busy, setBusy] = useState(false);

  if (!quiz?.question) return null;

  const onPick = async (key: string) => {
    if (busy || quiz.done) return;
    setBusy(true);
    try {
      const res = await submitDailyCareQuiz(key);
      if (res?.daily_care) {
        void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        onUpdate(res.daily_care);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.bgCard, borderColor: colors.border },
      ]}
    >
      <Text style={[styles.badge, { color: colors.primary }]}>QUIZ DA SEMANA 🧠</Text>
      <Text style={[styles.question, { color: colors.text }]}>{quiz.question}</Text>
      {quiz.done ? (
        <Text style={[styles.done, { color: colors.success }]}>
          Respondido ✓ · +{quiz.reward_seeds}🌰
        </Text>
      ) : (
        <View style={styles.options}>
          {(quiz.options ?? []).map((opt) => (
            <Pressable
              key={opt.key}
              onPress={() => void onPick(opt.key)}
              disabled={busy}
              style={({ pressed }) => [
                styles.option,
                {
                  borderColor: colors.primarySoft,
                  backgroundColor: colors.primaryTint,
                  opacity: pressed || busy ? 0.85 : 1,
                },
              ]}
            >
              {busy ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <>
                  <Text style={styles.optEmoji}>{opt.emoji}</Text>
                  <Text style={[styles.optLabel, { color: colors.text }]}>{opt.label}</Text>
                </>
              )}
            </Pressable>
          ))}
        </View>
      )}
      {!quiz.done ? (
        <Text style={[styles.hint, { color: colors.textMuted }]}>
          +{quiz.reward_seeds} sementes ao responder
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 14,
    marginTop: 12,
  },
  badge: { fontSize: 11, fontWeight: "900", letterSpacing: 0.4 },
  question: { fontSize: 15, fontWeight: "700", marginTop: 8, lineHeight: 21 },
  done: { fontSize: 13, fontWeight: "700", marginTop: 10 },
  options: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 },
  option: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    minWidth: "30%",
  },
  optEmoji: { fontSize: 18 },
  optLabel: { fontSize: 13, fontWeight: "600" },
  hint: { fontSize: 11, marginTop: 8 },
});
