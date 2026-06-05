import React from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import { COLORS } from "@/constants/config";

const avatarSource = require("../../assets/avatar.png");

export function PraktikaAvatar({ subtitle }: { subtitle?: string }) {
  return (
    <View style={styles.wrap}>
      <Image source={avatarSource} style={styles.image} resizeMode="cover" />
      {subtitle ? <Text style={styles.sub}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: "center",
    marginBottom: 12,
    paddingHorizontal: 16,
  },
  image: {
    width: "100%",
    maxWidth: 300,
    height: 280,
    borderRadius: 28,
    backgroundColor: COLORS.border,
  },
  sub: {
    marginTop: 8,
    color: COLORS.textMuted,
    fontSize: 14,
    textAlign: "center",
  },
});
