import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import * as Haptics from "expo-haptics";
import { submitDailyCareGoal } from "@/api/client";
import type { DailyCareGoal, DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  care: DailyCareInfo;
  onUpdate: (care: DailyCareInfo) => void;
};

function GoalRow({
  colors,
  goal,
  busy,
  breatheCount,
  onPress,
}: {
  colors: AppColors;
  goal: DailyCareGoal;
  busy: boolean;
  breatheCount: number | null;
  onPress: () => void;
}) {
  const locked = goal.locked && !goal.done;
  const done = goal.done;
  const breatheActive = goal.key === "breathe" && breatheCount !== null && breatheCount > 0;

  return (
    <Pressable
      onPress={onPress}
      disabled={busy || done || locked}
      style={[
        styles.row,
        {
          borderColor: done ? colors.success : locked ? colors.border : colors.primary,
          backgroundColor: done ? "rgba(34,197,94,0.08)" : colors.bg,
          opacity: locked ? 0.55 : 1,
        },
      ]}
    >
      <Text style={styles.rowEmoji}>{done ? "✓" : goal.emoji}</Text>
      <View style={styles.rowBody}>
        <Text style={[styles.rowLabel, { color: colors.text }]} numberOfLines={2}>
          {breatheActive ? `Respire… ${breatheCount}` : goal.label}
        </Text>
        <Text style={[styles.rowReward, { color: colors.textMuted }]}>
          +{goal.seeds_reward} sementes
        </Text>
      </View>
      {busy ? <ActivityIndicator color={colors.primary} size="small" /> : null}
    </Pressable>
  );
}

export function MoodDailyGoals({ colors, care, onUpdate }: Props) {
  const goals = care.daily_goals ?? [];
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [breatheCount, setBreatheCount] = useState<number | null>(null);
  const breatheTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (breatheTimer.current) clearInterval(breatheTimer.current);
    };
  }, []);

  if (!goals.length) return null;

  const runBreathe = () =>
    new Promise<void>((resolve) => {
      setBreatheCount(3);
      void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => undefined);
      let n = 3;
      breatheTimer.current = setInterval(() => {
        n -= 1;
        if (n <= 0) {
          if (breatheTimer.current) clearInterval(breatheTimer.current);
          setBreatheCount(null);
          resolve();
          return;
        }
        setBreatheCount(n);
        void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => undefined);
      }, 1100);
    });

  const onGoalPress = async (goal: DailyCareGoal) => {
    if (goal.done || goal.locked || busyKey) return;
    if (goal.key === "checkin") return;

    setBusyKey(goal.key);
    try {
      if (goal.key === "breathe") {
        await runBreathe();
      }
      const res = await submitDailyCareGoal(goal.key as "breathe" | "adventure");
      if (!res?.daily_care) return;
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => undefined);
      onUpdate(res.daily_care);
    } finally {
      setBusyKey(null);
    }
  };

  const doneCount = goals.filter((g) => g.done).length;

  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: colors.text }]}>Missões de hoje</Text>
        <Text style={[styles.counter, { color: colors.primary }]}>
          {doneCount}/{goals.length}
        </Text>
      </View>
      {goals.map((g) => (
        <GoalRow
          key={g.key}
          colors={colors}
          goal={g}
          busy={busyKey === g.key}
          breatheCount={g.key === "breathe" ? breatheCount : null}
          onPress={() => void onGoalPress(g)}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 12 },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  title: { fontSize: 14, fontWeight: "800" },
  counter: { fontSize: 12, fontWeight: "800" },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderWidth: 1.5,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 8,
  },
  rowEmoji: { fontSize: 20, width: 28, textAlign: "center" },
  rowBody: { flex: 1 },
  rowLabel: { fontSize: 13, fontWeight: "700", lineHeight: 17 },
  rowReward: { fontSize: 11, fontWeight: "600", marginTop: 2 },
});
