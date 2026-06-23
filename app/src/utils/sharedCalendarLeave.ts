import { Alert } from "react-native";
import { removeSharedCalendarMember } from "@/api/client";
import type { SharedCalendar } from "@/api/types";
import { myCalendarMember } from "@/utils/sharedCalendarMembers";

export function promptLeaveSharedCalendar(opts: {
  calendar: SharedCalendar;
  currentUserId?: string;
  onLeft: () => Promise<void>;
}): void {
  const { calendar, currentUserId, onLeft } = opts;
  const calId = String(calendar.id || "");
  const name = (calendar.name || "Agenda").trim();
  if (calendar.is_owner) {
    Alert.alert(
      "Você criou este grupo",
      "Para sair, apague o grupo — o criador não pode sair sem apagar."
    );
    return;
  }
  const me = myCalendarMember(calendar.members, currentUserId);
  const memberId = String(me?.id || "");
  if (!calId || !memberId) {
    Alert.alert("Sair", "Abra «Gerir grupo» para sair desta agenda.");
    return;
  }
  Alert.alert(
    "Sair do grupo",
    `Sair de «${name}»? Você pode voltar se alguém convidar de novo.`,
    [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Sair",
        style: "destructive",
        onPress: async () => {
          try {
            await removeSharedCalendarMember(calId, memberId);
            await onLeft();
          } catch (e) {
            Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível sair.");
          }
        },
      },
    ]
  );
}
