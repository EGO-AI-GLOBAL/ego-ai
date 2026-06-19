import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";

export type AgendaTab = "personal" | "shared";

type Props = {
  tab: AgendaTab;
  onChange: (t: AgendaTab) => void;
  colors: AppColors;
};

export function AgendaTabBar({ tab, onChange, colors }: Props) {
  return (
    <View style={[styles.tabBar, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
      {(
        [
          ["personal", "Agenda pessoal"],
          ["shared", "Entre Nós"],
        ] as const
      ).map(([id, label]) => {
        const active = tab === id;
        return (
          <Pressable
            key={id}
            onPress={() => onChange(id)}
            style={[
              styles.tabBtn,
              active && {
                backgroundColor: colors.bgCard,
                borderBottomWidth: 3,
                borderBottomColor: colors.primary,
              },
            ]}
          >
            <Text
              style={[
                styles.tabBtnText,
                { color: active ? colors.text : colors.textMuted, fontWeight: active ? "800" : "700" },
              ]}
              numberOfLines={1}
            >
              {label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    flexDirection: "row",
    borderWidth: 1,
    borderRadius: 12,
    padding: 4,
    marginBottom: 12,
    gap: 4,
  },
  tabBtn: {
    flex: 1,
    borderRadius: 9,
    paddingVertical: 10,
    paddingHorizontal: 6,
    alignItems: "center",
  },
  tabBtnText: { fontSize: 13, fontWeight: "700" },
});
