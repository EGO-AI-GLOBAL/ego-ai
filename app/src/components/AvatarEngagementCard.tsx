import React, { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { avatarOfDaySuggestion } from "@/constants/avatarRituals";
import type { AppColors } from "@/theme/colors";
import {
  avatarsNotChattedThisWeek,
  getWeeklyAvatarStats,
  markAvatarOfDaySeen,
  pickAvatarOfDay,
  wasAvatarOfDaySeenToday,
} from "@/utils/avatarEngagement";

type Props = {
  userId: string;
  currentAvatarId: string;
  colors: AppColors;
  onOpenAvatar: (avatarId: string) => void;
};

export function AvatarEngagementCard({ userId, currentAvatarId, colors, onOpenAvatar }: Props) {
  const [weekly, setWeekly] = useState({ chattedIds: [] as string[], goal: 3, done: 0 });
  const [dismissed, setDismissed] = useState(false);

  const dayAvatar = pickAvatarOfDay(userId);
  const suggestion = avatarOfDaySuggestion(dayAvatar.avatar_id, dayAvatar.shortName, "morning");
  const missed = avatarsNotChattedThisWeek(weekly.chattedIds).filter(
    (a) => a.avatar_id !== currentAvatarId
  );

  useEffect(() => {
    let alive = true;
    (async () => {
      const stats = await getWeeklyAvatarStats(userId);
      const seen = await wasAvatarOfDaySeenToday(userId);
      if (alive) {
        setWeekly(stats);
        if (seen && stats.done >= stats.goal) setDismissed(true);
      }
    })();
    return () => {
      alive = false;
    };
  }, [userId, currentAvatarId]);

  if (dismissed || !userId) return null;

  const weeklyLeft = Math.max(0, weekly.goal - weekly.done);

  return (
    <View style={[styles.wrap, { borderColor: colors.border, backgroundColor: colors.card }]}>
      <Text style={[styles.title, { color: colors.text }]}>{suggestion.title}</Text>
      <Text style={[styles.body, { color: colors.textMuted }]}>{suggestion.body}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Falar com ${dayAvatar.shortName}`}
        onPress={() => {
          void markAvatarOfDaySeen(userId);
          onOpenAvatar(dayAvatar.avatar_id);
        }}
        style={[styles.btn, { backgroundColor: colors.primary }]}
      >
        <Text style={styles.btnText}>Falar com {dayAvatar.shortName}</Text>
      </Pressable>
      {weeklyLeft > 0 ? (
        <Text style={[styles.meta, { color: colors.textMuted }]}>
          Meta da semana: {weekly.done}/{weekly.goal} avatares · faltam {weeklyLeft}
        </Text>
      ) : (
        <Text style={[styles.meta, { color: colors.primary }]}>
          Meta da semana completa — {weekly.done} avatares
        </Text>
      )}
      {missed[0] ? (
        <Pressable
          accessibilityRole="button"
          onPress={() => onOpenAvatar(missed[0]!.avatar_id)}
          style={styles.link}
        >
          <Text style={[styles.linkText, { color: colors.primary }]}>
            Ainda não falou com {missed[0]!.shortName} esta semana — 1 mensagem conta
          </Text>
        </Pressable>
      ) : null}
      <Pressable accessibilityRole="button" onPress={() => setDismissed(true)} style={styles.link}>
        <Text style={[styles.linkText, { color: colors.textMuted }]}>Fechar</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
    gap: 8,
  },
  title: { fontSize: 15, fontWeight: "700" },
  body: { fontSize: 14, lineHeight: 20 },
  btn: { borderRadius: 10, paddingVertical: 10, alignItems: "center" },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
  meta: { fontSize: 12, lineHeight: 18 },
  link: { paddingVertical: 4 },
  linkText: { fontSize: 13, fontWeight: "600" },
});
