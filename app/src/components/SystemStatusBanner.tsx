import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { useMaintenance } from "@/context/MaintenanceContext";
import { useColors } from "@/theme/ThemeContext";

export function SystemStatusBanner() {
  const colors = useColors();
  const { showBanner, message } = useMaintenance();

  if (!showBanner) return null;

  return (
    <View
      style={[
        styles.wrap,
        {
          backgroundColor: colors.primary,
          borderBottomColor: colors.primaryLight,
        },
      ]}
      accessibilityRole="alert"
      accessibilityLiveRegion="polite"
    >
      <ActivityIndicator size="small" color="#fff" style={styles.spinner} />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  spinner: { marginRight: 10 },
  text: {
    flex: 1,
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
    lineHeight: 20,
  },
});
