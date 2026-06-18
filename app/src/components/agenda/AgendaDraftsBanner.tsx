import React, { useState } from "react";
import { ActivityIndicator, Alert, Pressable, Text, View } from "react-native";
import {
  confirmAgendaDraft,
  dismissAgendaDraft,
  dismissAgendaDraftItem,
} from "@/api/client";
import type { AgendaDraft, AgendaDraftItem } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { formatScheduledLocal } from "@/utils/scheduleTime";
import { agendaFormStyles as s } from "./agendaFormStyles";

function describeDraftItem(item: AgendaDraftItem): string {
  if (item.type === "shopping_orphan") {
    return `${item.title || "Item"} · comprar quando puder`;
  }
  const when = item.scheduled_at ? formatScheduledLocal(item.scheduled_at) : "sem hora";
  const shop = (item.shopping_items || [])
    .map((x) => (typeof x === "string" ? x : x?.title || ""))
    .filter(Boolean);
  const shopLine = shop.length > 0 ? `\n   Compras: ${shop.join(", ")}` : "";
  return `${item.title || "Compromisso"} · ${when}${shopLine}`;
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
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const pending = drafts.filter((d) => (d.status || "pending") === "pending");
  if (!pending.length) return null;

  const draft = pending[0];
  const draftId = String(draft.id || "");
  const items = Array.isArray(draft.items) ? draft.items : [];

  const onAgendar = async (idx: number) => {
    if (!draftId) return;
    const key = `agendar-${idx}`;
    setBusyKey(key);
    try {
      const res = await confirmAgendaDraft(draftId, [idx]);
      if (res.errors?.length) {
        Alert.alert("Aviso", res.errors.join("\n"));
      }
      await onRefresh();
    } catch (e) {
      Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível agendar.");
    } finally {
      setBusyKey(null);
    }
  };

  const onExcluir = (idx: number) => {
    if (!draftId) return;
    Alert.alert("Excluir item", "Remover esta sugestão do descarrego?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Excluir",
        style: "destructive",
        onPress: async () => {
          const key = `excluir-${idx}`;
          setBusyKey(key);
          try {
            await dismissAgendaDraftItem(draftId, idx);
            await onRefresh();
          } catch (e) {
            Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível excluir.");
          } finally {
            setBusyKey(null);
          }
        },
      },
    ]);
  };

  const onDismissAll = () => {
    if (!draftId) return;
    Alert.alert("Ignorar tudo", "Descartar todas as sugestões do descarrego?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Ignorar tudo",
        style: "destructive",
        onPress: async () => {
          setBusyKey("all");
          try {
            await dismissAgendaDraft(draftId);
            await onRefresh();
          } catch (e) {
            Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível ignorar.");
          } finally {
            setBusyKey(null);
          }
        },
      },
    ]);
  };

  return (
    <View
      style={[
        s.formBox,
        { borderColor: colors.primary, backgroundColor: colors.primaryLight, marginBottom: 16 },
      ]}
    >
      <Text style={[s.section, { color: colors.text, marginBottom: 4 }]}>
        Do descarrego da noite
      </Text>
      <Text style={[s.muted, { color: colors.textMuted, marginBottom: 10 }]}>
        Revise item a item — Agendar grava na agenda; Excluir descarta só este.
      </Text>
      {draft.comfort_reply ? (
        <Text style={[s.muted, { color: colors.textMuted, marginBottom: 8 }]}>
          {draft.comfort_reply}
        </Text>
      ) : null}
      {items.length === 0 ? (
        <Text style={[s.muted, { color: colors.textMuted }]}>Nada para confirmar.</Text>
      ) : (
        items.map((it, idx) => {
          const rowBusy = busyKey === `agendar-${idx}` || busyKey === `excluir-${idx}`;
          return (
            <View
              key={`${draftId}-${idx}`}
              style={{
                borderTopWidth: 1,
                borderTopColor: colors.border,
                paddingVertical: 10,
                gap: 8,
              }}
            >
              <Text style={{ color: colors.text, fontSize: 14, lineHeight: 20 }}>
                {describeDraftItem(it)}
              </Text>
              <View style={{ flexDirection: "row", gap: 8 }}>
                <Pressable
                  onPress={() => void onAgendar(idx)}
                  disabled={!!busyKey}
                  style={[
                    s.inviteBtn,
                    {
                      flex: 1,
                      backgroundColor: colors.primary,
                      opacity: rowBusy || busyKey ? 0.7 : 1,
                    },
                  ]}
                >
                  {busyKey === `agendar-${idx}` ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={s.inviteBtnText}>Agendar</Text>
                  )}
                </Pressable>
                <Pressable
                  onPress={() => onExcluir(idx)}
                  disabled={!!busyKey}
                  style={{
                    borderColor: colors.danger,
                    borderWidth: 1,
                    borderRadius: 10,
                    paddingHorizontal: 14,
                    justifyContent: "center",
                    opacity: rowBusy || busyKey ? 0.7 : 1,
                  }}
                >
                  {busyKey === `excluir-${idx}` ? (
                    <ActivityIndicator color={colors.danger} />
                  ) : (
                    <Text style={{ color: colors.danger, fontWeight: "700" }}>Excluir</Text>
                  )}
                </Pressable>
              </View>
            </View>
          );
        })
      )}
      {items.length > 0 ? (
        <Pressable
          onPress={onDismissAll}
          disabled={!!busyKey}
          style={{ marginTop: 12, alignSelf: "flex-start", opacity: busyKey ? 0.7 : 1 }}
        >
          <Text style={{ color: colors.textMuted, fontWeight: "600", fontSize: 13 }}>
            Ignorar tudo
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}
