import React, { useEffect, useState } from "react";
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

function isFamilyDraftItem(item: AgendaDraftItem): boolean {
  return !!(item.assign_to || item.shared_calendar_id);
}

function describeDraftItem(item: AgendaDraftItem): string {
  if (item.type === "shopping_orphan") {
    return `${item.title || "Item"} · comprar quando puder`;
  }
  const when = item.scheduled_at ? formatScheduledLocal(item.scheduled_at) : "sem hora";
  const shop = (item.shopping_items || [])
    .map((x) => (typeof x === "string" ? x : x?.title || ""))
    .filter(Boolean);
  const shopLine = shop.length > 0 ? `\n   Compras: ${shop.join(", ")}` : "";
  const assign = item.assign_to;
  const assignLine =
    assign?.task || assign?.assignee_hint
      ? `\n   Para ${assign.assignee_hint || assign.relationship || "parceiro"}: ${assign.task || "ajudar"}`
      : "";
  const familyLine =
    isFamilyDraftItem(item)
      ? `\n   → ${item.shared_calendar_name || "Entre Nós"}`
      : "";
  return `${item.title || "Compromisso"} · ${when}${shopLine}${assignLine}${familyLine}`;
}

export function AgendaDraftsBanner({
  colors,
  drafts,
  onRefresh,
  familyOnly = false,
}: {
  colors: AppColors;
  drafts: AgendaDraft[];
  onRefresh: () => Promise<void>;
  /** true = aba compartilhada; false = só itens pessoais */
  familyOnly?: boolean;
}) {
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const pending = drafts.filter((d) => (d.status || "pending") === "pending");
  const draft = pending[0];
  const draftId = draft ? String(draft.id || "") : "";
  const allItems = draft && Array.isArray(draft.items) ? draft.items : [];
  const visibleEntries = allItems
    .map((it, idx) => ({ it, idx }))
    .filter(({ it }) => (familyOnly ? isFamilyDraftItem(it) : !isFamilyDraftItem(it)));

  useEffect(() => {
    if (!draftId || allItems.length > 0) return;
    let cancelled = false;
    void (async () => {
      try {
        await dismissAgendaDraft(draftId);
        if (!cancelled) await onRefresh();
      } catch {
        /* banner oculto */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [draftId, allItems.length, onRefresh]);

  if (!pending.length || visibleEntries.length === 0) return null;

  const onAgendar = async (idx: number) => {
    if (!draftId) return;
    const key = `agendar-${idx}`;
    setBusyKey(key);
    try {
      const res = await confirmAgendaDraft(draftId, [idx]);
      if (res.errors?.length) Alert.alert("Aviso", res.errors.join("\n"));
      await onRefresh();
    } catch (e) {
      Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível agendar.");
    } finally {
      setBusyKey(null);
    }
  };

  const onAgendarTodos = async () => {
    if (!draftId) return;
    setBusyKey("agendar-all");
    try {
      const indices = visibleEntries.map(({ idx }) => idx);
      const res = await confirmAgendaDraft(draftId, indices);
      if (res.errors?.length) Alert.alert("Aviso", res.errors.join("\n"));
      await onRefresh();
    } catch (e) {
      Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível agendar.");
    } finally {
      setBusyKey(null);
    }
  };

  const onExcluir = (idx: number) => {
    if (!draftId) return;
    Alert.alert("Excluir item", "Remover esta sugestão do desabafo?", [
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
    Alert.alert("Ignorar tudo", "Descartar todas as sugestões do desabafo?", [
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
        {
          borderColor: colors.primary,
          backgroundColor: colors.bgCard,
          marginBottom: 16,
          borderLeftWidth: 4,
        },
      ]}
    >
      <View
        style={{
          alignSelf: "flex-start",
          backgroundColor: colors.primaryTint,
          paddingHorizontal: 10,
          paddingVertical: 4,
          borderRadius: 8,
          marginBottom: 8,
        }}
      >
        <Text style={[s.section, { color: colors.primary, marginBottom: 0, marginTop: 0 }]}>
          {familyOnly ? "Do desabafo — Entre Nós" : "Do desabafo da noite"}
        </Text>
      </View>
      <Text style={[s.muted, { color: colors.textMuted, marginBottom: 8 }]}>
        {familyOnly
          ? "Grava na agenda Entre Nós — seu parceiro vê ao abrir a Agenda."
          : "Revise item a item — Agendar grava na agenda pessoal; Excluir descarta só este."}
      </Text>
      {draft.comfort_reply ? (
        <Text
          style={[
            s.muted,
            {
              color: colors.text,
              marginBottom: 10,
              fontStyle: "italic",
              backgroundColor: colors.primaryTint,
              padding: 10,
              borderRadius: 8,
            },
          ]}
        >
          {draft.comfort_reply}
        </Text>
      ) : null}
      {visibleEntries.map(({ it, idx }) => {
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
      })}
      {visibleEntries.length > 1 ? (
        <Pressable
          onPress={() => void onAgendarTodos()}
          disabled={!!busyKey}
          style={[
            s.inviteBtn,
            {
              marginTop: 12,
              backgroundColor: colors.primary,
              opacity: busyKey ? 0.7 : 1,
            },
          ]}
        >
          {busyKey === "agendar-all" ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={s.inviteBtnText}>Agendar todos</Text>
          )}
        </Pressable>
      ) : null}
      <Pressable
        onPress={onDismissAll}
        disabled={!!busyKey}
        style={{ marginTop: 12, alignSelf: "flex-start", opacity: busyKey ? 0.7 : 1 }}
      >
        <Text style={{ color: colors.textMuted, fontWeight: "600", fontSize: 13 }}>
          Ignorar tudo
        </Text>
      </Pressable>
    </View>
  );
}
