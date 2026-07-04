import React from "react";
import { Pressable, Share, StyleSheet, Text, View } from "react-native";
import type { DailyCareSocialInvite } from "@/api/types";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  invite?: DailyCareSocialInvite | null;
};

/** Convite social — partilhar app com amigos (Fase 10). */
export function MoodSocialInviteCard({ colors, invite }: Props) {
  if (!invite?.message) return null;

  const onShare = () => {
    void Share.share({ message: invite.message });
  };

  return (
    <Pressable
      onPress={onShare}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: colors.bgCard,
          borderColor: colors.glassBorder,
          opacity: pressed ? 0.9 : 1,
        },
      ]}
    >
      <Text style={styles.emoji}>{invite.emoji ?? "💬"}</Text>
      <View style={styles.body}>
        <Text style={[styles.title, { color: colors.text }]}>{invite.title}</Text>
        <Text style={[styles.hook, { color: colors.textMuted }]} numberOfLines={2}>
          {invite.share_hook}
        </Text>
      </View>
      <Text style={[styles.cta, { color: colors.primary }]}>Convidar</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 14,
    borderWidth: 1,
    padding: 14,
    marginTop: 12,
    gap: 10,
  },
  emoji: { fontSize: 26 },
  body: { flex: 1 },
  title: { fontSize: 14, fontWeight: "800" },
  hook: { fontSize: 12, marginTop: 4, lineHeight: 17 },
  cta: { fontSize: 13, fontWeight: "800" },
});
