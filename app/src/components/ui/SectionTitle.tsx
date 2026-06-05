import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { COLORS } from "@/constants/config";

export function SectionTitle({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.sub}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 10, marginTop: 4 },
  title: {
    color: COLORS.text,
    fontSize: 17,
    fontWeight: "700",
    letterSpacing: -0.3,
  },
  sub: {
    color: COLORS.textMuted,
    fontSize: 13,
    marginTop: 2,
  },
});
