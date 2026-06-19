import React, { useState } from "react";
import { ActivityIndicator, Alert, Pressable, Text, View } from "react-native";
import { confirmDelegationRequest, dismissDelegationRequest } from "@/api/client";
import type { DelegationRequest } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { formatScheduledLocal } from "@/utils/scheduleTime";
import { agendaFormStyles as s } from "./agendaFormStyles";

function describeRequest(req: DelegationRequest): string {
  const assistant = (req.assistant_name || "Luna").trim();
  const title = (req.title || "Compromisso").trim();
  const when = req.scheduled_at ? formatScheduledLocal(req.scheduled_at) : "";
  const task = (req.task_description || req.assignee_label || "ajudar").trim();
  const timePart = when ? ` ${when}` : " amanhã";
  return (
    `A ${assistant} avisou que ${title}${timePart} e você ficou responsável por ${task}. ` +
    `Posso incluir na sua agenda?`
  );
}

export function DelegationRequestsBanner({
  colors,
  requests,
  onRefresh,
}: {
  colors: AppColors;
  requests: DelegationRequest[];
  onRefresh: () => Promise<void>;
}) {
  const [busyId, setBusyId] = useState<string | null>(null);
  const pending = requests.filter((r) => (r.status || "pending") === "pending");
  if (!pending.length) return null;

  const onConfirm = async (id: string) => {
    setBusyId(id);
    try {
      await confirmDelegationRequest(id);
      await onRefresh();
    } catch (e) {
      Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível confirmar.");
    } finally {
      setBusyId(null);
    }
  };

  const onDismiss = (id: string) => {
    Alert.alert("Ignorar", "Descartar este pedido da família?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Ignorar",
        style: "destructive",
        onPress: async () => {
          setBusyId(id);
          try {
            await dismissDelegationRequest(id);
            await onRefresh();
          } catch (e) {
            Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível ignorar.");
          } finally {
            setBusyId(null);
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
      <Text style={[s.section, { color: colors.primary, marginBottom: 4 }]}>
        Piloto automático · Família
      </Text>
      <Text style={[s.muted, { color: colors.textMuted, marginBottom: 10 }]}>
        Alguém da família pediu ajuda no desabafo. Confirme para entrar na sua agenda.
      </Text>
      {pending.map((req) => {
        const id = String(req.id || "");
        const busy = busyId === id;
        return (
          <View
            key={id}
            style={{
              borderTopWidth: 1,
              borderTopColor: colors.border,
              paddingVertical: 10,
              gap: 8,
            }}
          >
            <Text style={{ color: colors.text, fontSize: 14, lineHeight: 20 }}>
              {describeRequest(req)}
            </Text>
            <View style={{ flexDirection: "row", gap: 8 }}>
              <Pressable
                onPress={() => void onConfirm(id)}
                disabled={!!busyId}
                style={[
                  s.inviteBtn,
                  {
                    flex: 1,
                    backgroundColor: colors.primary,
                    opacity: busy || busyId ? 0.7 : 1,
                  },
                ]}
              >
                {busy ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={s.inviteBtnText}>Confirmar</Text>
                )}
              </Pressable>
              <Pressable
                onPress={() => onDismiss(id)}
                disabled={!!busyId}
                style={{
                  borderColor: colors.textMuted,
                  borderWidth: 1,
                  borderRadius: 10,
                  paddingHorizontal: 14,
                  justifyContent: "center",
                  opacity: busy || busyId ? 0.7 : 1,
                }}
              >
                <Text style={{ color: colors.textMuted, fontWeight: "700" }}>Ignorar</Text>
              </Pressable>
            </View>
          </View>
        );
      })}
    </View>
  );
}
