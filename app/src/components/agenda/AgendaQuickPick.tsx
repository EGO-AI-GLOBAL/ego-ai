import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";
import { todayDateBr, tomorrowDateBr } from "./agendaUtils";

type Props = {
  colors: AppColors;
  dateValue: string;
  onDatePick: (dateBr: string) => void;
  titleValue?: string;
  onTitlePick?: (title: string) => void;
  showTitleSuggestions?: boolean;
};

const TITLE_SUGGESTIONS = ["Consulta", "Reunião", "Médico", "Aniversário"];

export function AgendaQuickPick({
  colors,
  dateValue,
  onDatePick,
  titleValue,
  onTitlePick,
  showTitleSuggestions = true,
}: Props) {
  const today = todayDateBr();
  const tomorrow = tomorrowDateBr();

  return (
    <View style={styles.wrap}>
      <Text style={[styles.label, { color: colors.textMuted }]}>Atalhos rápidos</Text>
      <View style={styles.row}>
        {[
          { label: "Hoje", value: today },
          { label: "Amanhã", value: tomorrow },
        ].map((chip) => {
          const active = dateValue === chip.value;
          return (
            <Pressable
              key={chip.label}
              onPress={() => onDatePick(chip.value)}
              style={[
                styles.chip,
                {
                  borderColor: active ? colors.primary : colors.border,
                  backgroundColor: active ? colors.primaryLight : colors.bg,
                },
              ]}
            >
              <Text
                style={[
                  styles.chipText,
                  { color: active ? colors.primary : colors.text },
                ]}
              >
                {chip.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
      {showTitleSuggestions && onTitlePick ? (
        <View style={[styles.row, { marginTop: 6 }]}>
          {TITLE_SUGGESTIONS.map((suggestion) => {
            const active = (titleValue || "").trim() === suggestion;
            return (
              <Pressable
                key={suggestion}
                onPress={() => onTitlePick(suggestion)}
                style={[
                  styles.chip,
                  styles.chipSmall,
                  {
                    borderColor: active ? colors.primary : colors.border,
                    backgroundColor: active ? colors.primaryLight : colors.bg,
                  },
                ]}
              >
                <Text
                  style={[
                    styles.chipTextSmall,
                    { color: active ? colors.primary : colors.textMuted },
                  ]}
                >
                  {suggestion}
                </Text>
              </Pressable>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 4 },
  label: { fontSize: 12, fontWeight: "600", marginBottom: 6 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  chipSmall: { paddingHorizontal: 10, paddingVertical: 6 },
  chipText: { fontSize: 14, fontWeight: "700" },
  chipTextSmall: { fontSize: 13, fontWeight: "600" },
});
