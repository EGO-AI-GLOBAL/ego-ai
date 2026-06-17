import React, { useState } from "react";
import { ActivityIndicator, Alert, Pressable, Text, View } from "react-native";
import { confirmAgendaDraft, dismissAgendaDraft } from "@/api/client";
import type { AgendaDraft, AgendaDraftItem } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { formatScheduledLocal } from "@/utils/scheduleTime";
import { agendaFormStyles as s } from "./agendaFormStyles";

function describeDraftItem(item: AgendaDraftItem): string {
  if (item.type === "shopping_orphan") {
    return `${item.title || "Item"} · comprar quando puder`;
  }
  const when = item.scheduled_at ? formatScheduledLocal(item.scheduled_at) : "sem hora";
  const shop = (item.shopping_items || []).length;
  const extra = shop > 0 ? ` · ${shop} item(ns) de compra` : "";
  return `${item.title || "Compromisso"} · ${when}${extra}`;
}

export function AgendaDraftsBanner({
  colors,
  drafts,
  onRefresh,
}: {
  colors: AppColors;
  drafts: AgendaDraft[];
  onRefresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const pending = drafts.filter((d) => (d.status || "pending") === "pending");
  if (!pending.length) return null;

  const draft = pending[0];
  const draftId = String(draft.id || "");
  const items = Array.isArray(draft.items) ? draft.items : [];

  const onConfirmAll = async () => {
    if (!draftId) return;
    setBusy(true);
    try {
      const res = await confirmAgendaDraft(draftId);
      if (res.errors?.length) {
        Alert.alert("Parcial", res.errors.join("\n"));
      }
      await onRefresh();
    } catch (e) {
      Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível confirmar.");
    } finally {
      setBusy(false);
    }
  };

  const onDismiss = () => {
    if (!draftId) return;
    Alert.alert("Ignorar rascunho", "Descartar sugestões do descarrego da noite?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Ignorar",
        style: "destructive",
        onPress: async () => {
          setBusy(true);
          try {
            await dismissAgendaDraft(draftId);
            await onRefresh();
          } catch (e) {
            Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível ignorar.");
          } finally {
            setBusy(false);
          }
        },
      },
    ]);
  };

  return (
    <View style={[s.formBox, { borderColor: colors.primary, backgroundColor: colors.primaryLight, marginBottom: 16 }]}>
      <Text style={[s.section, { color: colors.text, marginBottom: 4 }]}>
        Do descarrego da noite
      </Text>
      {draft.comfort_reply ? (
        <Text style={[s.muted, { color: colors.textMuted, marginBottom: 8 }]}>
          {draft.comfort_reply}
        </Text>
      ) : null}
      {items.length === 0 ? (
        <Text style={[s.muted, { color: colors.textMuted }]}>Nada para confirmar.</Text>
      ) : (
        items.map((it, idx) => (
          <Text key={`${draftId}-${idx}`} style={{ color: colors.text, fontSize: 14, marginBottom: 4 }}>
            • {describeDraftItem(it)}
          </Text>
        ))
      )}
      <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
        <Pressable
          onPress={onConfirmAll}
          disabled={busy || !items.length}
          style={[s.inviteBtn, { flex: 1, backgroundColor: colors.primary, opacity: busy ? 0.7 : 1 }]}
        >
          {busy ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={s.inviteBtnText}>Confirmar na agenda</Text>
          )}
        </Pressable>
        <Pressable
          onPress={onDismiss}
          disabled={busy}
          style={{
            borderColor: colors.border,
            borderWidth: 1,
            borderRadius: 10,
            paddingHorizontal: 14,
            justifyContent: "center",
          }}
        >
          <Text style={{ color: colors.textMuted, fontWeight: "600" }}>Ignorar</Text>
        </Pressable>
      </View>
    </View>
  );
}
