import React, { useState } from "react";
import { ActivityIndicator, Alert, Pressable, Text, View } from "react-native";
import { respondSharedCalendarMemberInvite } from "@/api/client";
import type { PendingCalendarInvite } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { agendaFormStyles as s } from "./agendaFormStyles";

type Props = {
  colors: AppColors;
  invites: PendingCalendarInvite[];
  onRefresh: () => Promise<void>;
};

function inviteLabel(inv: PendingCalendarInvite): string {
  const who = (inv.owner_name || "Alguém").trim();
  const cal = (inv.calendar_name || (inv.is_entre_nos ? "Entre Nós" : "Agenda")).trim();
  return `${who} convidou você para «${cal}»`;
}

export function PendingCalendarInvitesBanner({ colors, invites, onRefresh }: Props) {
  const [busyId, setBusyId] = useState<string | null>(null);
  if (!invites.length) return null;

  const onRespond = async (inv: PendingCalendarInvite, accept: boolean) => {
    const mid = String(inv.member_id || "");
    if (!mid) return;
    setBusyId(mid);
    try {
      await respondSharedCalendarMemberInvite(mid, accept);
      await onRefresh();
      Alert.alert(
        accept ? "Convite aceito" : "Convite recusado",
        accept
          ? `Você entrou em «${(inv.calendar_name || "Agenda").trim()}».`
          : "O convite foi removido."
      );
    } catch (e) {
      Alert.alert(
        "Convite",
        e instanceof Error ? e.message : "Não foi possível responder ao convite."
      );
    } finally {
      setBusyId(null);
    }
  };

  return (
    <View style={{ marginBottom: 16 }}>
      {invites.map((inv) => {
        const mid = String(inv.member_id || "");
        const busy = busyId === mid;
        return (
          <View
            key={mid}
            style={[
              s.formBox,
              {
                borderColor: colors.primary,
                backgroundColor: colors.primaryTint,
                marginBottom: 10,
              },
            ]}
          >
            <Text style={[s.formLabel, { color: colors.text, fontWeight: "700" }]}>
              Convite de agenda
            </Text>
            <Text style={[s.muted, { color: colors.text, marginTop: 4 }]}>
              {inviteLabel(inv)}
            </Text>
            <Text style={[s.muted, { color: colors.textMuted, marginTop: 6, fontSize: 12 }]}>
              Aceite para ver tarefas e confirmar compromissos juntos.
            </Text>
            <View style={{ flexDirection: "row", gap: 8, marginTop: 12 }}>
              <Pressable
                onPress={() => void onRespond(inv, true)}
                disabled={busy}
                style={[
                  s.inviteBtn,
                  { flex: 1, backgroundColor: colors.primary, opacity: busy ? 0.7 : 1 },
                ]}
              >
                {busy ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={s.inviteBtnText}>Aceitar</Text>
                )}
              </Pressable>
              <Pressable
                onPress={() => void onRespond(inv, false)}
                disabled={busy}
                style={[
                  s.inviteBtn,
                  {
                    flex: 1,
                    backgroundColor: colors.bgCard,
                    borderWidth: 1,
                    borderColor: colors.border,
                  },
                ]}
              >
                <Text style={[s.inviteBtnText, { color: colors.textMuted }]}>Recusar</Text>
              </Pressable>
            </View>
          </View>
        );
      })}
    </View>
  );
}
