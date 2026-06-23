import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  title: string;
  done: boolean;
  busy: boolean;
  onToggle: () => void;
  onApagar: () => void;
};

export function ShoppingItemRow({ colors, title, done, busy, onToggle, onApagar }: Props) {
  return (
    <View style={styles.row}>
      <Pressable
        onPress={onToggle}
        disabled={busy}
        hitSlop={6}
        style={({ pressed }) => [
          styles.main,
          { opacity: pressed || busy ? 0.7 : 1 },
        ]}
        accessibilityRole="checkbox"
        accessibilityState={{ checked: done }}
        accessibilityLabel={title || "Item da lista"}
      >
        <View
          style={[
            styles.checkbox,
            {
              borderColor: colors.primary,
              backgroundColor: done ? colors.primary : colors.primaryTint,
            },
          ]}
        >
          {done ? (
            <Ionicons name="checkmark" size={16} color="#fff" />
          ) : null}
        </View>
        <Text
          style={{
            color: colors.text,
            flex: 1,
            fontSize: 14,
            textDecorationLine: done ? "line-through" : "none",
            opacity: done ? 0.65 : 1,
          }}
        >
          {title || "Item"}
        </Text>
        {busy ? <ActivityIndicator size="small" color={colors.primary} /> : null}
      </Pressable>
      <Pressable
        onPress={onApagar}
        disabled={busy}
        style={[styles.apagarBtn, { borderColor: colors.border }]}
        accessibilityLabel="Apagar item da lista"
      >
        <Text style={[styles.apagarText, { color: colors.danger }]}>Apagar</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", paddingVertical: 4, gap: 6 },
  main: { flex: 1, flexDirection: "row", alignItems: "center", minHeight: 36 },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 2,
    marginRight: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  apagarBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
  },
  apagarText: { fontSize: 12, fontWeight: "700" },
});
