import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import * as Haptics from "expo-haptics";
import * as Notifications from "expo-notifications";
import { submitDailyCareGoal } from "@/api/client";
import type { DailyCareGoal, DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { savePendingAvatarCongrats } from "@/storage/pendingAvatarCongrats";

type Props = {
  colors: AppColors;
  care: DailyCareInfo;
  userId?: string;
  onUpdate: (care: DailyCareInfo) => void;
  onGoalsBonus?: (congratsLine?: string) => void;
};

function goalKind(goal: DailyCareGoal): string {
  if (goal.kind) return goal.kind;
  if (goal.key === "checkin") return "checkin";
  if (goal.key === "adventure") return "adventure";
  if (goal.key === "breathe" || goal.key === "calm_breath") return "breathe";
  return "tap";
}

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
  const isBreathe = goalKind(goal) === "breathe";
  const breatheActive = isBreathe && breatheCount !== null && breatheCount > 0;

  return (
    <Pressable
      onPress={onPress}
      disabled={busy || done || locked}
      style={[
        styles.row,
        {
          borderColor: done
            ? colors.success
            : goal.surprise
              ? colors.primary
              : locked
                ? colors.border
                : colors.primary,
          backgroundColor: done
            ? "rgba(34,197,94,0.08)"
            : goal.surprise
              ? colors.primaryTint
              : colors.bg,
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
          {goal.surprise ? "✨ surpresa · " : ""}+{goal.seeds_reward} sementes
        </Text>
      </View>
      {busy ? <ActivityIndicator color={colors.primary} size="small" /> : null}
    </Pressable>
  );
}

export function MoodDailyGoals({ colors, care, userId, onUpdate, onGoalsBonus }: Props) {
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
    if (goalKind(goal) === "checkin") return;

    setBusyKey(goal.key);
    try {
      const kind = goalKind(goal);
      if (kind === "breathe") {
        await runBreathe();
      } else if (kind === "tap") {
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => undefined);
      }
      const res = await submitDailyCareGoal(goal.key);
      if (!res?.daily_care) return;
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => undefined);
      onUpdate(res.daily_care);
      const congratsLine = res.daily_care.avatar_congrats?.trim();
      if (congratsLine && userId) {
        void savePendingAvatarCongrats(userId, congratsLine);
        if (Platform.OS !== "web") {
          void Notifications.scheduleNotificationAsync({
            content: {
              title: "Jardim completo",
              body: congratsLine,
              sound: true,
              data: { screen: "chat", type: "avatar_congrats" },
            },
            trigger: null,
          }).catch(() => undefined);
        }
      }
      if (res.daily_care.goals_bonus_granted) {
        onGoalsBonus?.(congratsLine);
      }
    } finally {
      setBusyKey(null);
    }
  };

  const doneCount = goals.filter((g) => g.done).length;
  const congrats = care.avatar_congrats?.trim();
  const hasSurprise = goals.some((g) => g.surprise);

  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: colors.text }]}>Missões de hoje</Text>
        <Text style={[styles.counter, { color: colors.primary }]}>
          {doneCount}/{goals.length}
        </Text>
      </View>
      {hasSurprise ? (
        <Text style={[styles.surpriseHint, { color: colors.textMuted }]}>
          Inclui 1 missão surpresa — muda todo dia ✨
        </Text>
      ) : null}
      {congrats ? (
        <Text style={[styles.congrats, { color: colors.primary }]}>{congrats}</Text>
      ) : null}
      {goals.map((g) => (
        <GoalRow
          key={g.key}
          colors={colors}
          goal={g}
          busy={busyKey === g.key}
          breatheCount={goalKind(g) === "breathe" ? breatheCount : null}
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
  surpriseHint: { fontSize: 10, fontWeight: "600", marginBottom: 6, lineHeight: 14 },
  congrats: { fontSize: 13, lineHeight: 19, fontWeight: "600", marginBottom: 8 },
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
