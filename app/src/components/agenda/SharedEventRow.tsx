import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import type { SharedCalendarEvent } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { formatScheduledLocal } from "@/utils/scheduleTime";

type Props = {
  event: SharedCalendarEvent;
  colors: AppColors;
  currentUserId?: string;
  responderLabel?: string;
  creatorLabel?: string;
  onDismiss?: (eventId: string) => void;
  onRespond?: (eventId: string, accept: boolean) => void;
  busy?: boolean;
};

function inviteStatusLabel(
  event: SharedCalendarEvent,
  currentUserId?: string,
  responderLabel?: string,
  creatorLabel?: string
): string | null {
  const status = event.invite_status || "none";
  if (status === "none") return null;
  const isCreator = currentUserId && event.created_by_user_id === currentUserId;
  const isResponder = currentUserId && event.responded_by_user_id === currentUserId;
  if (status === "pending") {
    if (isCreator) return "Aguardando a outra pessoa confirmar ou recusar";
    return creatorLabel
      ? `Convite de ${creatorLabel} — confirme ou recuse`
      : "Convite para você — confirme ou recuse";
  }
  if (status === "confirmed") {
    if (isResponder) return "Você confirmou";
    return responderLabel ? `${responderLabel} confirmou` : "Confirmado";
  }
  if (status === "declined") {
    if (isResponder) return "Você recusou";
    return responderLabel ? `${responderLabel} recusou` : "Recusado";
  }
  return null;
}

export function SharedEventRow({
  event,
  colors,
  currentUserId,
  responderLabel,
  creatorLabel,
  onDismiss,
  onRespond,
  busy,
}: Props) {
  const id = String(event.id || "");
  const status = event.invite_status || "none";
  const isCreator = !!(currentUserId && event.created_by_user_id === currentUserId);
  const canRespond =
    status === "pending" && !isCreator && !!onRespond && !!currentUserId && !!id;
  const statusLine = inviteStatusLabel(
    event,
    currentUserId,
    responderLabel,
    creatorLabel
  );
  const statusColor =
    status === "confirmed"
      ? colors.primary
      : status === "declined"
        ? colors.danger
        : colors.textMuted;

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
        {statusLine ? (
          <Text style={[styles.status, { color: statusColor }]}>{statusLine}</Text>
        ) : null}
        {canRespond ? (
          <View style={styles.respondRow}>
            <Pressable
              onPress={() => onRespond!(id, true)}
              disabled={busy}
              style={[
                styles.respondBtn,
                { backgroundColor: colors.primary, opacity: busy ? 0.6 : 1 },
              ]}
            >
              {busy ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.respondBtnText}>Confirmar</Text>
              )}
            </Pressable>
            <Pressable
              onPress={() => onRespond!(id, false)}
              disabled={busy}
              style={[
                styles.respondBtnOutline,
                { borderColor: colors.danger, opacity: busy ? 0.6 : 1 },
              ]}
            >
              <Text style={[styles.respondBtnOutlineText, { color: colors.danger }]}>
                Recusar
              </Text>
            </Pressable>
          </View>
        ) : null}
      </View>
      {onDismiss && id ? (
        <Pressable
          onPress={() => onDismiss(id)}
          disabled={busy}
          style={[styles.actionBtn, { borderColor: colors.border, opacity: busy ? 0.5 : 1 }]}
          accessibilityLabel="Apagar compromisso"
        >
          <Text style={[styles.actionText, { color: colors.danger }]}>Apagar</Text>
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
  status: { fontSize: 12, marginTop: 4, fontWeight: "700" },
  respondRow: { flexDirection: "row", gap: 8, marginTop: 8 },
  respondBtn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    minWidth: 96,
    alignItems: "center",
  },
  respondBtnText: { color: "#fff", fontWeight: "700", fontSize: 13 },
  respondBtnOutline: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    minWidth: 88,
    alignItems: "center",
  },
  respondBtnOutlineText: { fontWeight: "700", fontSize: 13 },
  actionBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    marginLeft: 8,
  },
  actionText: { fontSize: 12, fontWeight: "700" },
});
