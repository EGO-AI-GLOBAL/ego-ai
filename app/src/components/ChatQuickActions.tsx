import React from "react";
import { Pressable, ScrollView, StyleSheet, Text } from "react-native";
import { CHAT_QUICK_ACTIONS, type ChatQuickAction } from "@/constants/chatQuickActions";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  disabled?: boolean;
  onPick: (action: ChatQuickAction) => void;
  actions?: ChatQuickAction[];
};

export function ChatQuickActions({ colors, disabled, onPick, actions }: Props) {
  const items = actions?.length ? actions : CHAT_QUICK_ACTIONS;
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.row}
      keyboardShouldPersistTaps="handled"
    >
      {items.map((action) => (
        <Pressable
          key={action.id}
          disabled={disabled}
          onPress={() => onPick(action)}
          style={({ pressed }) => [
            styles.chip,
            {
              backgroundColor: pressed ? colors.primaryLight : "transparent",
              opacity: disabled ? 0.45 : 1,
            },
          ]}
        >
          <Text style={[styles.chipText, { color: colors.primary }]}>{action.label}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { gap: 8, paddingVertical: 4 },
  chip: {
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 10,
    minHeight: 44,
    justifyContent: "center",
  },
  chipText: { fontSize: 15, fontWeight: "800" },
});
