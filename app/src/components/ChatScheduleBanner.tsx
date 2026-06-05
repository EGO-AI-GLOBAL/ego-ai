import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { DashboardData, SendChatResult } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { shareEventMessage } from "@/utils/whatsappShare";

export type ScheduleBannerItem = {
  title: string;
  whenLabel: string;
  calendarName: string;
  scheduledAt?: string;
};

function resolveCalendarName(
  data: DashboardData,
  calendarId?: string,
  fallback?: string
): string {
  if (fallback?.trim()) return fallback.trim();
  if (!calendarId) return data.shared_calendars?.[0]?.name?.trim() || "Agenda";
  const cal = data.shared_calendars?.find((c) => String(c.id) === String(calendarId));
  return cal?.name?.trim() || "Agenda";
}

export function extractScheduleBannerItems(
  result: SendChatResult,
  data: DashboardData
): ScheduleBannerItem[] {
  const items: ScheduleBannerItem[] = [];
  for (const ev of result.shared_events_saved ?? []) {
    const scheduledAt = String(ev.scheduled_at || "");
    let whenLabel = "";
    if (scheduledAt) {
      try {
        whenLabel = new Date(scheduledAt).toLocaleString("pt-BR", {
          day: "2-digit",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
        });
      } catch {
        whenLabel = scheduledAt;
      }
    }
    items.push({
      title: (ev.title || "Compromisso").trim(),
      whenLabel,
      scheduledAt,
      calendarName: resolveCalendarName(
        data,
        ev.calendar_id,
        (ev as { calendar_name?: string }).calendar_name
      ),
    });
  }
  for (const r of result.reminders_saved ?? []) {
    const scheduledAt = String(r.scheduled_at || "");
    let whenLabel = scheduledAt;
    try {
      whenLabel = new Date(scheduledAt).toLocaleString("pt-BR", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      /* keep */
    }
    items.push({
      title: (r.title || "Lembrete").trim(),
      whenLabel,
      scheduledAt,
      calendarName: "Lembretes",
    });
  }
  return items;
}

type Props = {
  colors: AppColors;
  items: ScheduleBannerItem[];
  assistantName: string;
  onDismiss?: () => void;
};

export function ChatScheduleBanner({ colors, items, assistantName, onDismiss }: Props) {
  const ev = items[0];
  if (!ev) return null;

  const line = ev.whenLabel
    ? `Marcado: ${ev.title} · ${ev.whenLabel}`
    : `Marcado: ${ev.title}`;

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.bgCard, borderColor: colors.success },
      ]}
    >
      <Text style={[styles.line, { color: colors.text }]}>{line}</Text>
      <Text style={[styles.sub, { color: colors.textMuted }]}>{ev.calendarName}</Text>
      <View style={styles.row}>
        <Pressable
          onPress={() =>
            void shareEventMessage({
              calendarName: ev.calendarName,
              title: ev.title,
              whenLabel: ev.whenLabel,
              assistantName,
            })
          }
          style={[styles.btn, { backgroundColor: colors.primary }]}
        >
          <Text style={styles.btnText}>Partilhar</Text>
        </Pressable>
        {onDismiss ? (
          <Pressable onPress={onDismiss} style={styles.feito}>
            <Text style={[styles.feitoText, { color: colors.textMuted }]}>Feito</Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 12,
    marginBottom: 10,
  },
  line: { fontSize: 15, fontWeight: "700" },
  sub: { fontSize: 13, marginTop: 4, marginBottom: 10 },
  row: { flexDirection: "row", alignItems: "center", gap: 12 },
  btn: { borderRadius: 10, paddingHorizontal: 16, paddingVertical: 10 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
  feito: { paddingVertical: 8, paddingHorizontal: 4 },
  feitoText: { fontSize: 15, fontWeight: "600" },
});
