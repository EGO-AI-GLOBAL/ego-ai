import React from "react";
import { Alert, Pressable, Text } from "react-native";
import type { AppColors } from "@/theme/colors";
import {
  shareSharedCalendarInviteNative,
  shareSharedCalendarInviteWhatsApp,
} from "@/utils/whatsappShare";
import { agendaFormStyles as s } from "./agendaFormStyles";

type Props = {
  colors: AppColors;
  calendarName: string;
  kind: "entre_nos" | "grupo";
  /** Telefone ou e-mail já registado no convite — obrigatório para partilhar. */
  inviteContact?: string;
};

function requireContact(kind: "entre_nos" | "grupo", inviteContact?: string): string | null {
  const contact = (inviteContact || "").trim();
  if (contact) return contact;
  Alert.alert(
    "Convite",
    kind === "entre_nos"
      ? "Primeiro digite o telefone ou e-mail do parceiro(a) e toque em «Convidar parceiro(a)». Depois partilhe no WhatsApp."
      : "Primeiro digite o telefone ou e-mail da pessoa e toque em «Convidar». Depois partilhe no WhatsApp."
  );
  return null;
}

/** WhatsApp + Instagram/Outros com links Play + TestFlight. */
export function SharedCalendarSocialInvite({
  colors,
  calendarName,
  kind,
  inviteContact,
}: Props) {
  const name =
    calendarName.trim() || (kind === "entre_nos" ? "Entre Nós" : "Família");

  const shareWhatsApp = () => {
    const contact = requireContact(kind, inviteContact);
    if (!contact) return;
    void shareSharedCalendarInviteWhatsApp(name, kind, contact);
  };

  const shareNative = () => {
    const contact = requireContact(kind, inviteContact);
    if (!contact) return;
    void shareSharedCalendarInviteNative(name, kind, contact);
  };

  return (
    <>
      <Pressable
        onPress={shareWhatsApp}
        style={[
          s.inviteBtn,
          {
            backgroundColor: colors.bgCard,
            borderWidth: 1.5,
            borderColor: "#25D366",
            marginTop: 8,
          },
        ]}
      >
        <Text style={[s.inviteBtnText, { color: "#128C7E" }]}>Convidar pelo WhatsApp</Text>
      </Pressable>
      <Pressable
        onPress={shareNative}
        style={[s.inviteBtn, { backgroundColor: colors.primary, marginTop: 8 }]}
      >
        <Text style={s.inviteBtnText}>Instagram / Outros</Text>
      </Pressable>
    </>
  );
}
