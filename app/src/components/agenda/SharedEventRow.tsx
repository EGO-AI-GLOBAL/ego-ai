import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { SharedCalendarEvent } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { formatScheduledLocal } from "@/utils/scheduleTime";

type Props = {
  event: SharedCalendarEvent;
  colors: AppColors;
  onDismiss?: (eventId: string) => void;
  busy?: boolean;
};

export function SharedEventRow({ event, colors, onDismiss, busy }: Props) {
  const id = String(event.id || "");
  return (
    <View style={[styles.row, { borderBottomColor: colors.border }]}>
      <View style={[styles.dot, { backgroundColor: colors.primary }]} />
      <View style={styles.body}>
        <Text style={[styles.title, { color: colors.text }]} numberOfLines={2}>
          {event.title || "Compromisso"}
        </Text>
        <Text style={[styles.when, { color: colors.textMuted }]}>
          {formatScheduledLocal(event.scheduled_at)}
        </Text>
      </View>
      {onDismiss && id ? (
        <Pressable
          onPress={() => onDismiss(id)}
          disabled={busy}
          style={[styles.actionBtn, { borderColor: colors.border, opacity: busy ? 0.5 : 1 }]}
          accessibilityLabel="Remover compromisso"
        >
          <Text style={[styles.actionText, { color: colors.danger }]}>Remover</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 6,
    marginRight: 10,
  },
  body: { flex: 1 },
  title: { fontSize: 15, fontWeight: "600" },
  when: { fontSize: 13, marginTop: 2 },
  actionBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    marginLeft: 8,
  },
  actionText: { fontSize: 12, fontWeight: "700" },
});
