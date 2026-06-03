import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";
import type { AgendaItem as AgendaRow } from "@/api/types";

export function AgendaItemRow({
  item,
  colors,
  onDelete,
}: {
  item: AgendaRow;
  colors: AppColors;
  onDelete?: (id: string) => void;
}) {
  const hor = String(item.horario || "").slice(0, 5);
  const id = String(item.id || "");
  return (
    <View style={[styles.row, { borderBottomColor: colors.border }]}>
      <View style={[styles.timeBox, { backgroundColor: colors.bgElevated }]}>
        <Text style={[styles.time, { color: colors.primaryLight }]}>{hor || "—"}</Text>
      </View>
      <View style={styles.body}>
        <Text style={[styles.title, { color: colors.text }]} numberOfLines={1}>
          {item.titulo || "Compromisso"}
        </Text>
        <Text style={[styles.days, { color: colors.textMuted }]}>
          {item.dias_da_semana || "—"}
        </Text>
      </View>
      {onDelete && id ? (
        <Pressable
          onPress={() => onDelete(id)}
          style={[styles.delBtn, { borderColor: colors.border }]}
          accessibilityLabel="Remover da agenda"
        >
          <Text style={[styles.delText, { color: colors.danger }]}>Remover</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  timeBox: {
    width: 52,
    paddingVertical: 6,
    paddingHorizontal: 4,
    borderRadius: 8,
    alignItems: "center",
    marginRight: 12,
  },
  time: { fontWeight: "700", fontSize: 13 },
  body: { flex: 1 },
  title: { fontSize: 15, fontWeight: "600" },
  days: { fontSize: 12, marginTop: 2 },
  delBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
  },
  delText: { fontSize: 12, fontWeight: "700" },
});
