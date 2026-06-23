import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";
import {
  getSocialProfiles,
  openInstagramProfile,
  openTikTokProfile,
} from "@/constants/socialProfiles";

type Props = {
  colors: AppColors;
  compact?: boolean;
};

/** Seguir EGO-AI no Instagram e TikTok. */
export function SocialFollowBar({ colors, compact }: Props) {
  const s = getSocialProfiles();

  return (
    <View style={[styles.wrap, compact && styles.wrapCompact]}>
      {!compact ? (
        <Text style={[styles.title, { color: colors.textMuted }]}>
          Siga a gente e compartilhe o desafio
        </Text>
      ) : null}
      <View style={styles.row}>
        <Pressable
          onPress={() => void openInstagramProfile()}
          style={[styles.btn, { borderColor: "#E1306C", backgroundColor: colors.bgCard }]}
        >
          <Text style={[styles.btnText, { color: "#E1306C" }]}>📸 Instagram</Text>
          <Text style={[styles.handle, { color: colors.textMuted }]} numberOfLines={1}>
            {s.instagramMention}
          </Text>
        </Pressable>
        <Pressable
          onPress={() => void openTikTokProfile()}
          style={[styles.btn, { borderColor: colors.text, backgroundColor: colors.bgCard }]}
        >
          <Text style={[styles.btnText, { color: colors.text }]}>🎵 TikTok</Text>
          <Text style={[styles.handle, { color: colors.textMuted }]} numberOfLines={1}>
            {s.tiktokMention}
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: 10, marginBottom: 4 },
  wrapCompact: { marginTop: 8 },
  title: { fontSize: 11, fontWeight: "600", marginBottom: 8, textAlign: "center" },
  row: { flexDirection: "row", gap: 8 },
  btn: {
    flex: 1,
    borderRadius: 12,
    borderWidth: 1.5,
    paddingVertical: 10,
    paddingHorizontal: 8,
    alignItems: "center",
  },
  btnText: { fontSize: 13, fontWeight: "800" },
  handle: { fontSize: 10, marginTop: 2, maxWidth: "100%" },
});
