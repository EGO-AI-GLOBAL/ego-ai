import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
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
    <View style={styles.wrap}>
      {items.map((action) => (
        <Pressable
          key={action.id}
          disabled={disabled}
          onPress={() => onPick(action)}
          style={({ pressed }) => [
            styles.chip,
            {
              backgroundColor: pressed ? colors.primaryLight : colors.bgCard,
              borderColor: colors.border,
              opacity: disabled ? 0.45 : 1,
            },
          ]}
        >
          <Text style={[styles.chipText, { color: colors.primary }]} numberOfLines={1}>
            {action.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 4,
    width: "100%",
  },
  chip: {
    borderRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 12,
    paddingVertical: 8,
    minHeight: 40,
    justifyContent: "center",
    maxWidth: "48%",
  },
  chipText: { fontSize: 14, fontWeight: "700", textAlign: "center" },
});
