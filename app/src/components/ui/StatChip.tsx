import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { COLORS } from "@/constants/config";

export function StatChip({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  const color =
    tone === "success"
      ? COLORS.success
      : tone === "warning"
        ? COLORS.warning
        : tone === "danger"
          ? COLORS.danger
          : COLORS.primaryLight;
  return (
    <View style={styles.chip}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, { color }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    flex: 1,
    minWidth: "45%",
    backgroundColor: COLORS.bgElevated,
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  label: {
    color: COLORS.textMuted,
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginBottom: 4,
  },
  value: {
    fontSize: 15,
    fontWeight: "600",
  },
});
