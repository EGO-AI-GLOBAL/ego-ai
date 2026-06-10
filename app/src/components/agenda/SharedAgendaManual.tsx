import { useRouter, type Href } from "expo-router";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  addSharedCalendarMember,
  createSharedCalendar,
  createSharedCalendarEvent,
  deleteSharedCalendar,
  dismissSharedCalendarEvent,
  localDateTimeToIso,
} from "@/api/client";
import type { SharedCalendar } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import {
  memberDisplayName,
  membersCardLine,
  membersGroupLine,
} from "@/utils/sharedCalendarMembers";
import { AgendaDateTimeFields } from "./AgendaDateTimeFields";
import { agendaFormStyles as s } from "./agendaFormStyles";
import {
  defaultDateBr,
  defaultTimeHm,
  filterVisibleSharedEvents,
  sortSharedEvents,
} from "./agendaUtils";
import { SharedEventRow } from "./SharedEventRow";

const AGENDA_UI_VERSION = "jun/2025 · nomes + layout claro";

type Props = {
  colors: AppColors;
  sharedCalendars: SharedCalendar[];
  currentUserId?: string;
  onRefresh: () => Promise<void>;
};

/**
 * Agenda compartilhada 100% manual — isolada de chat/voz/login.
 */
export function SharedAgendaManual({
  colors,
  sharedCalendars,
  currentUserId,
  onRefresh,
}: Props) {
  const router = useRouter();
  const [selectedSharedId, setSelectedSharedId] = useState<string | null>(null);
  const [inviteContact, setInviteContact] = useState("");
  const [inviting, setInviting] = useState(false);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [newCalendarName, setNewCalendarName] = useState("Família");
  const [creatingCalendar, setCreatingCalendar] = useState(false);
  const [showSharedEventForm, setShowSharedEventForm] = useState(false);
  const [sharedEventTitle, setSharedEventTitle] = useState("Reunião");
  const [sharedEventDate, setSharedEventDate] = useState(defaultDateBr);
  const [sharedEventTime, setSharedEventTime] = useState(defaultTimeHm(15, 0));
  const [savingSharedEvent, setSavingSharedEvent] = useState(false);
  const [listTick, setListTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setListTick((t) => t + 1), 60_000);
    return () => clearInterval(id);
  }, []);

  const selectedCalendar = useMemo(() => {
    if (!selectedSharedId) return null;
    return sharedCalendars.find((c) => String(c.id) === selectedSharedId) ?? null;
  }, [sharedCalendars, selectedSharedId]);

  useEffect(() => {
    if (sharedCalendars.length === 0) {
      setSelectedSharedId(null);
      return;
    }
    const ids = sharedCalendars.map((c) => String(c.id));
    if (!selectedSharedId || !ids.includes(selectedSharedId)) {
      setSelectedSharedId(String(sharedCalendars[0].id));
    }
  }, [sharedCalendars, selectedSharedId]);

  const selectedEvents = useMemo(() => {
    if (!selectedCalendar) return [];
    return sortSharedEvents(filterVisibleSharedEvents(selectedCalendar.events ?? []));
  }, [selectedCalendar, listTick]);

  const inputStyle = [
    s.inviteInput,
    { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
  ];

  const onCreateSharedCalendar = async () => {
    const name = newCalendarName.trim();
    if (!name) {
      Alert.alert("Nome", "Digite um nome para a agenda (ex.: Família).");
      return;
    }
    setCreatingCalendar(true);
    try {
      const cal = await createSharedCalendar(name);
      setNewCalendarName("Família");
      setSelectedSharedId(String(cal.id));
      await onRefresh();
      Alert.alert("Agenda criada", `«${name}» está pronta. Marque compromissos ou convide pessoas.`);
    } catch (e) {
      Alert.alert(
        "Erro",
        e instanceof Error ? e.message : "Não foi possível criar a agenda."
      );
    } finally {
      setCreatingCalendar(false);
    }
  };

  const onAddSharedEvent = async () => {
    if (!selectedCalendar?.id) return;
    const title = sharedEventTitle.trim() || "Reunião";
    const iso = localDateTimeToIso(sharedEventDate.trim(), sharedEventTime.trim());
    if (!iso) {
      Alert.alert("Data/hora", "Toque na data e na hora para escolher no calendário.");
      return;
    }
    setSavingSharedEvent(true);
    try {
      await createSharedCalendarEvent(String(selectedCalendar.id), {
        title,
        scheduled_at: iso,
        announce: title,
      });
      setShowSharedEventForm(false);
      setSharedEventTitle("Reunião");
      setSharedEventDate(defaultDateBr());
      setSharedEventTime(defaultTimeHm(15, 0));
      await onRefresh();
      Alert.alert("Marcado", `«${title}» foi adicionado à agenda «${selectedCalendar.name}».`);
    } catch (e) {
      Alert.alert(
        "Erro",
        e instanceof Error ? e.message : "Não foi possível marcar o compromisso."
      );
    } finally {
      setSavingSharedEvent(false);
    }
  };

  const onInviteToSelectedCalendar = async () => {
    if (!selectedCalendar?.id) return;
    const contact = inviteContact.trim();
    if (!contact) {
      Alert.alert("Convite", "Digite telefone ou e-mail.");
      return;
    }
    setInviting(true);
    try {
      const member = await addSharedCalendarMember(String(selectedCalendar.id), contact);
      setInviteContact("");
      await onRefresh();
      const pending = member.status === "pending";
      const label = memberDisplayName(member);
      Alert.alert(
        pending ? "Convite enviado" : "Adicionado",
        pending
          ? `${label} verá a agenda quando entrar no EGO com o mesmo telefone ou e-mail.`
          : `${label} já tem acesso à agenda.`
      );
    } catch (e) {
      Alert.alert("Convite", e instanceof Error ? e.message : "Não foi possível convidar.");
    } finally {
      setInviting(false);
    }
  };

  const onDismissSharedEvent = (eventId: string) => {
    if (!selectedCalendar?.id) return;
    const item = selectedEvents.find((ev) => String(ev.id) === eventId);
    const title = (item?.title || "Compromisso").trim();
    const calendarId = String(selectedCalendar.id);
    Alert.alert("Apagar", `Apagar «${title}» desta agenda?`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Apagar",
        style: "destructive",
        onPress: async () => {
          setActionBusy(eventId);
          try {
            await dismissSharedCalendarEvent(calendarId, eventId);
            await onRefresh();
          } catch (e) {
            Alert.alert(
              "Erro",
              e instanceof Error ? e.message : "Não foi possível apagar o compromisso."
            );
          } finally {
            setActionBusy(null);
          }
        },
      },
    ]);
  };

  const onDeleteSelectedCalendar = () => {
    if (!selectedCalendar?.id) return;
    const cid = String(selectedCalendar.id);
    const name = (selectedCalendar.name || "Agenda").trim();
    Alert.alert(
      "Apagar agenda",
      `Apagar «${name}» para todos? Esta ação não pode ser desfeita.`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Apagar",
          style: "destructive",
          onPress: async () => {
            try {
              await deleteSharedCalendar(cid);
              await onRefresh();
              setSelectedSharedId(null);
            } catch (e) {
              Alert.alert(
                "Erro",
                e instanceof Error ? e.message : "Não foi possível apagar a agenda."
              );
            }
          },
        },
      ]
    );
  };

  if (sharedCalendars.length === 0) {
    return (
      <View style={[s.formBox, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
        <Text style={[s.formLabel, { color: colors.textMuted }]}>
          Criar agenda em grupo (sem usar o chat)
        </Text>
        <TextInput
          value={newCalendarName}
          onChangeText={setNewCalendarName}
          placeholder="Nome (ex.: Família)"
          placeholderTextColor={colors.textMuted}
          style={inputStyle}
        />
        <Pressable
          onPress={onCreateSharedCalendar}
          disabled={creatingCalendar}
          style={[s.inviteBtn, { backgroundColor: colors.primary }]}
        >
          {creatingCalendar ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={s.inviteBtnText}>Criar agenda</Text>
          )}
        </Pressable>
        <Text style={[s.muted, { color: colors.textMuted, marginTop: 4 }]}>
          Depois: marque compromissos, convide por e-mail/telefone e apague com os botões.
        </Text>
      </View>
    );
  }

  return (
    <>
      <Text style={[styles.uiVersion, { color: colors.primary }]}>{AGENDA_UI_VERSION}</Text>
      <Text style={[s.section, { color: colors.textMuted }]}>
        Suas agendas ({sharedCalendars.length})
      </Text>
      {sharedCalendars.map((cal) => {
        const cid = String(cal.id || "");
        const calName = (cal.name || "Agenda").trim();
        const nmem = cal.member_count ?? cal.members?.length ?? 0;
        const peopleLine = membersCardLine(cal.members, nmem, currentUserId);
        const active = selectedSharedId === cid;
        const evCount = filterVisibleSharedEvents(cal.events ?? []).length;
        return (
          <Pressable
            key={cid}
            onPress={() => setSelectedSharedId(cid)}
            style={({ pressed }) => [
              styles.calPick,
              {
                borderColor: colors.border,
                backgroundColor: active ? colors.bgElevated : colors.bgCard,
                borderWidth: 1.5,
                opacity: pressed ? 0.88 : 1,
              },
              active && {
                borderLeftWidth: 4,
                borderLeftColor: colors.primary,
                paddingLeft: 12,
              },
            ]}
          >
            <Text style={[styles.calPickTitle, { color: colors.text }]} numberOfLines={2}>
              {calName}
            </Text>
            {peopleLine ? (
              <>
                <Text style={[styles.calPickPeopleLabel, { color: colors.textMuted }]}>
                  Pessoas no grupo
                </Text>
                <Text style={[styles.calPickMembers, { color: colors.text }]} numberOfLines={6}>
                  {peopleLine}
                </Text>
              </>
            ) : null}
            <Text style={[styles.calPickMeta, { color: colors.textMuted }]}>
              {nmem > 0 ? `${nmem} membro${nmem === 1 ? "" : "s"}` : "Sem membros"}
              {cal.is_owner ? " · você criou" : ""}
              {" · "}
              {evCount} compromisso{evCount === 1 ? "" : "s"}
            </Text>
          </Pressable>
        );
      })}

      {selectedCalendar ? (
        <View style={[styles.calDetail, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
          <Text style={[styles.calDetailTitle, { color: colors.text }]}>
            {(selectedCalendar.name || "Agenda").trim()}
          </Text>
          <Text style={[styles.calDetailMembers, { color: colors.textMuted }]}>
            {membersGroupLine(selectedCalendar.members, currentUserId)}
          </Text>
          <Text style={[s.sectionInner, { color: colors.textMuted }]}>Compromissos marcados</Text>
          <Pressable
            onPress={() => setShowSharedEventForm((v) => !v)}
            style={({ pressed }) => [
              s.addBtn,
              {
                borderColor: colors.primary,
                backgroundColor: showSharedEventForm ? colors.primaryLight : colors.bgCard,
                opacity: pressed ? 0.88 : 1,
                marginBottom: 8,
              },
            ]}
          >
            <Text style={[s.addBtnText, { color: colors.primary }]}>
              {showSharedEventForm ? "Fechar formulário" : "+ Novo compromisso"}
            </Text>
          </Pressable>
          {showSharedEventForm ? (
            <View
              style={[
                s.formBox,
                { borderColor: colors.border, backgroundColor: colors.bg, marginBottom: 10 },
              ]}
            >
              <TextInput
                value={sharedEventTitle}
                onChangeText={setSharedEventTitle}
                placeholder="Título (ex.: Reunião)"
                placeholderTextColor={colors.textMuted}
                style={[
                  s.inviteInput,
                  {
                    color: colors.text,
                    borderColor: colors.border,
                    backgroundColor: colors.bgCard,
                  },
                ]}
              />
              <AgendaDateTimeFields
                colors={colors}
                dateValue={sharedEventDate}
                timeValue={sharedEventTime}
                onDateChange={setSharedEventDate}
                onTimeChange={setSharedEventTime}
              />
              <Pressable
                onPress={onAddSharedEvent}
                disabled={savingSharedEvent}
                style={[s.inviteBtn, { backgroundColor: colors.primary }]}
              >
                {savingSharedEvent ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={s.inviteBtnText}>Marcar</Text>
                )}
              </Pressable>
            </View>
          ) : null}
          {selectedEvents.length === 0 ? (
            <Text style={[s.muted, { color: colors.textMuted }]}>
              Nenhum compromisso. Toque em «+ Novo compromisso» acima.
            </Text>
          ) : (
            selectedEvents.map((ev) => {
              const eid = String(ev.id);
              return (
                <SharedEventRow
                  key={eid}
                  event={ev}
                  colors={colors}
                  onDismiss={onDismissSharedEvent}
                  busy={actionBusy === eid}
                />
              );
            })
          )}
          <Text style={[s.sectionInner, { color: colors.textMuted, marginTop: 14 }]}>
            Convidar pessoa
          </Text>
          <TextInput
            value={inviteContact}
            onChangeText={setInviteContact}
            placeholder="11 99999-9999 ou email@exemplo.com"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
            autoCorrect={false}
            style={inputStyle}
          />
          <Pressable
            onPress={onInviteToSelectedCalendar}
            disabled={inviting}
            style={[s.inviteBtn, { backgroundColor: colors.primary }]}
          >
            {inviting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={s.inviteBtnText}>Convidar</Text>
            )}
          </Pressable>
          {selectedCalendar.is_owner ? (
            <>
              <Pressable
                onPress={() =>
                  router.push(
                    `/(main)/shared-calendar/${String(selectedCalendar.id)}` as Href
                  )
                }
                style={({ pressed }) => [
                  styles.manageBtn,
                  { borderColor: colors.primary, opacity: pressed ? 0.88 : 1 },
                ]}
              >
                <Text style={{ color: colors.primary, fontWeight: "600" }}>
                  Gerir agenda (convidar, membros)
                </Text>
              </Pressable>
              <Pressable
                onPress={onDeleteSelectedCalendar}
                style={({ pressed }) => [
                  styles.deleteBtn,
                  { borderColor: colors.danger, opacity: pressed ? 0.88 : 1 },
                ]}
              >
                <Text style={{ color: colors.danger, fontWeight: "600" }}>
                  Apagar esta agenda
                </Text>
              </Pressable>
            </>
          ) : null}
        </View>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  uiVersion: { fontSize: 12, fontWeight: "700", marginBottom: 8 },
  calPick: { borderWidth: 1.5, borderRadius: 12, padding: 14, marginBottom: 8 },
  calPickTitle: { fontSize: 16, fontWeight: "700" },
  calPickPeopleLabel: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginTop: 8,
    marginBottom: 4,
  },
  calPickMembers: { fontSize: 14, lineHeight: 21, fontWeight: "600" },
  calPickMeta: { fontSize: 12, marginTop: 4 },
  calDetail: { borderWidth: 1, borderRadius: 12, padding: 14, marginTop: 12 },
  calDetailTitle: { fontSize: 17, fontWeight: "800", marginBottom: 6 },
  calDetailMembers: { fontSize: 14, lineHeight: 20, marginBottom: 12 },
  manageBtn: {
    marginTop: 16,
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  deleteBtn: {
    marginTop: 10,
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
});
