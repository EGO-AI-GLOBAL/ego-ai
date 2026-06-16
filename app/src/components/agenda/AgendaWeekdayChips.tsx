import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";
import { WEEKDAY_KEYS, WEEKDAY_LABELS, toggleWeekdayCsv } from "./agendaUtils";

type Props = {
  colors: AppColors;
  value: string;
  onChange: (value: string) => void;
};

export function AgendaWeekdayChips({ colors, value, onChange }: Props) {
  const selected = new Set(
    value
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean)
  );

  return (
    <View style={styles.wrap}>
      <Text style={[styles.label, { color: colors.textMuted }]}>Dias da semana</Text>
      <View style={styles.row}>
        {WEEKDAY_KEYS.map((key, i) => {
          const active = selected.has(key);
          return (
            <Pressable
              key={key}
              onPress={() => onChange(toggleWeekdayCsv(value, key))}
              style={[
                styles.day,
                {
                  borderColor: active ? colors.primary : colors.border,
                  backgroundColor: active ? colors.primary : colors.bg,
                },
              ]}
            >
              <Text
                style={[
                  styles.dayText,
                  { color: active ? "#fff" : colors.text },
                ]}
              >
                {WEEKDAY_LABELS[i]}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 4 },
  label: { fontSize: 12, fontWeight: "600", marginBottom: 6 },
  row: { flexDirection: "row", justifyContent: "space-between", gap: 4 },
  day: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
  },
  dayText: { fontSize: 12, fontWeight: "800" },
});
