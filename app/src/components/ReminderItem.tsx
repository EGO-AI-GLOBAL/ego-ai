import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";
import type { Reminder } from "@/api/types";
import { formatScheduledLocal } from "@/utils/scheduleTime";

export function ReminderItem({
  item,
  colors,
  onDismiss,
}: {
  item: Reminder;
  colors: AppColors;
  onDismiss?: (id: string) => void;
}) {
  const id = String(item.id || "");
  return (
    <View style={[styles.row, { borderBottomColor: colors.border }]}>
      <View style={[styles.dot, { backgroundColor: colors.primary }]} />
      <View style={styles.body}>
        <Text style={[styles.title, { color: colors.text }]} numberOfLines={2}>
          {item.title || "Lembrete"}
        </Text>
        <Text style={[styles.when, { color: colors.textMuted }]}>
          {formatScheduledLocal(item.scheduled_at)}
        </Text>
      </View>
      {onDismiss && id ? (
        <Pressable
          onPress={() => onDismiss(id)}
          style={[styles.delBtn, { borderColor: colors.border }]}
          accessibilityLabel="Dispensar lembrete"
        >
          <Text style={[styles.delText, { color: colors.textMuted }]}>OK</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 6,
    marginRight: 12,
  },
  body: { flex: 1 },
  title: { fontSize: 15, fontWeight: "600" },
  when: { fontSize: 13, marginTop: 2 },
  delBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
  },
  delText: { fontSize: 12, fontWeight: "700" },
});
