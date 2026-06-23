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
  dismissSharedCalendarEvent,
  localDateTimeToIso,
  respondEntreNosEvent,
} from "@/api/client";
import type { SharedCalendar } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { shareEntreNosEventWhatsApp } from "@/utils/whatsappShare";
import { promptLeaveSharedCalendar } from "@/utils/sharedCalendarLeave";
import { formatScheduledLocal } from "@/utils/scheduleTime";
import {
  canCreateMoreEntreNos,
  ENTRE_NOS_MAX_CALENDARS,
  entreNosPartnerSlotFull,
  normalizeEntreNosGroupName,
} from "@/utils/entreNos";
import {
  memberDisplayName,
  membersCardLine,
  membersGroupLine,
} from "@/utils/sharedCalendarMembers";
import { AgendaDateTimeFields } from "./AgendaDateTimeFields";
import { AgendaQuickPick } from "./AgendaQuickPick";
import { agendaFormStyles as s } from "./agendaFormStyles";
import {
  defaultScheduleSlot,
  filterVisibleSharedEvents,
  sortSharedEvents,
} from "./agendaUtils";
import { SharedEventRow } from "./SharedEventRow";
import { SharedCalendarSocialInvite } from "./SharedCalendarSocialInvite";

type Props = {
  colors: AppColors;
  sharedCalendars: SharedCalendar[];
  currentUserId?: string;
  onRefresh: () => Promise<void>;
};

/** Entre Nós — você + 1 pessoa · confirmar / recusar convites e tarefas. */
export function EntreNosAgendaSection({
  colors,
  sharedCalendars,
  currentUserId,
  onRefresh,
}: Props) {
  const router = useRouter();
  const initialSlot = defaultScheduleSlot();
  const [selectedSharedId, setSelectedSharedId] = useState<string | null>(null);
  const [inviteContact, setInviteContact] = useState("");
  const [registeredInviteContact, setRegisteredInviteContact] = useState("");
  const [inviting, setInviting] = useState(false);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [newCalendarName, setNewCalendarName] = useState("");
  const [creatingCalendar, setCreatingCalendar] = useState(false);
  const [showCreateCalendarForm, setShowCreateCalendarForm] = useState(false);
  const [showSharedEventForm, setShowSharedEventForm] = useState(false);
  const [sharedEventTitle, setSharedEventTitle] = useState("");
  const [sharedEventDate, setSharedEventDate] = useState(initialSlot.date);
  const [sharedEventTime, setSharedEventTime] = useState(initialSlot.time);
  const [savingSharedEvent, setSavingSharedEvent] = useState(false);
  const [listTick, setListTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setListTick((t) => t + 1), 60_000);
    return () => clearInterval(id);
  }, []);

  const ownedCount = useMemo(
    () => sharedCalendars.filter((c) => c.is_owner).length,
    [sharedCalendars]
  );
  const mayCreate = canCreateMoreEntreNos(ownedCount);

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

  const memberCount =
    selectedCalendar?.member_count ?? selectedCalendar?.members?.length ?? 0;
  const partnerSlotFull = entreNosPartnerSlotFull(memberCount);

  const inputStyle = [
    s.inviteInput,
    { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
  ];

  const memberLabelFor = (userId?: string) => {
    if (!userId || !selectedCalendar?.members) return "";
    const mem = selectedCalendar.members.find((m) => String(m.user_id || "") === userId);
    return memberDisplayName(mem);
  };

  const onCreateGroup = async () => {
    const raw = newCalendarName.trim();
    if (!raw) {
      Alert.alert("Nome", "Escolha um nome — ex.: Maria, João…");
      return;
    }
    if (!mayCreate) {
      Alert.alert(
        "Limite",
        `Você já tem ${ENTRE_NOS_MAX_CALENDARS} grupos Entre Nós. Apague um para criar outro.`
      );
      return;
    }
    const name = normalizeEntreNosGroupName(raw);
    setCreatingCalendar(true);
    try {
      const cal = await createSharedCalendar(name);
      setNewCalendarName("");
      setShowCreateCalendarForm(false);
      setSelectedSharedId(String(cal.id));
      await onRefresh();
      Alert.alert("Grupo criado", `«${name}» — convide 1 pessoa abaixo.`);
    } catch (e) {
      Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível criar.");
    } finally {
      setCreatingCalendar(false);
    }
  };

  const onAddEvent = async () => {
    if (!selectedCalendar?.id) return;
    const title = sharedEventTitle.trim() || "Compromisso";
    const iso = localDateTimeToIso(sharedEventDate.trim(), sharedEventTime.trim());
    if (!iso) {
      Alert.alert("Data/hora", "Toque na data e na hora.");
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
      setSharedEventTitle("");
      await onRefresh();
      const whenLabel = formatScheduledLocal(iso);
      const groupName = (selectedCalendar.name || "Entre Nós").trim();
      Alert.alert(
        "Convite enviado",
        "A outra pessoa confirma ou recusa no app.",
        [
          { text: "OK", style: "cancel" },
          {
            text: "Avisar no WhatsApp",
            onPress: () => {
              void shareEntreNosEventWhatsApp({
                groupName,
                title,
                whenLabel,
              });
            },
          },
        ]
      );
    } catch (e) {
      Alert.alert("Erro", e instanceof Error ? e.message : "Não foi possível enviar.");
    } finally {
      setSavingSharedEvent(false);
    }
  };

  const onInvitePartner = async () => {
    if (!selectedCalendar?.id) return;
    if (partnerSlotFull) {
      Alert.alert(
        "Entre Nós",
        "Já há 1 pessoa neste grupo. Crie «+ Outro Entre Nós» para outra pessoa."
      );
      return;
    }
    const contact = inviteContact.trim();
    if (!contact) {
      Alert.alert("Convite", "Digite telefone ou e-mail.");
      return;
    }
    setInviting(true);
    try {
      const member = await addSharedCalendarMember(String(selectedCalendar.id), contact);
      setRegisteredInviteContact(contact);
      setInviteContact("");
      await onRefresh();
      const label = memberDisplayName(member);
      Alert.alert(
        member.status === "pending" ? "Convite enviado" : "Adicionado",
        member.status === "pending"
          ? `${label} verá na Agenda → Entre Nós para aceitar, com o mesmo contacto no cadastro.`
          : `${label} já tem acesso.`,
        member.status === "pending"
          ? [
              { text: "OK", style: "cancel" },
              {
                text: "Convidar no WhatsApp",
                onPress: () => {
                  void shareEntreNosInviteWhatsApp(
                    (selectedCalendar?.name || "Entre Nós").trim(),
                    contact
                  );
                },
              },
            ]
          : undefined
      );
    } catch (e) {
      Alert.alert("Convite", e instanceof Error ? e.message : "Não foi possível convidar.");
    } finally {
      setInviting(false);
    }
  };

  return (
    <View style={[styles.wrap, { borderTopColor: colors.border }]}>
      <Text style={[s.section, { color: colors.textMuted, marginTop: 20 }]}>Entre Nós</Text>
      <Text style={[s.muted, { color: colors.textMuted, marginBottom: 8, fontSize: 12 }]}>
        Você + 1 pessoa · os dois criam tarefas · confirmar ou recusar convites.
      </Text>

      {sharedCalendars.length === 0 ? (
        <View style={[s.formBox, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
          <Text style={[s.formLabel, { color: colors.textMuted }]}>1. Nome do grupo</Text>
          <TextInput
            value={newCalendarName}
            onChangeText={setNewCalendarName}
            placeholder="Ex.: Maria, João…"
            placeholderTextColor={colors.textMuted}
            style={inputStyle}
          />
          <Pressable
            onPress={onCreateGroup}
            disabled={creatingCalendar || !mayCreate}
            style={[s.inviteBtn, { backgroundColor: colors.primary, opacity: mayCreate ? 1 : 0.6 }]}
          >
            {creatingCalendar ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={s.inviteBtnText}>Criar Entre Nós</Text>
            )}
          </Pressable>
          <Text style={[s.muted, { color: colors.textMuted, marginTop: 8 }]}>
            2. Depois convide <Text style={{ fontWeight: "700" }}>1 pessoa</Text>.
          </Text>
        </View>
      ) : (
        <>
          {mayCreate ? (
            <Pressable
              onPress={() => setShowCreateCalendarForm((v) => !v)}
              style={({ pressed }) => [
                s.addBtn,
                {
                  borderColor: colors.primary,
                  backgroundColor: showCreateCalendarForm ? colors.primaryTint : colors.bgCard,
                  opacity: pressed ? 0.88 : 1,
                  marginBottom: 10,
                },
              ]}
            >
              <Text style={[s.addBtnText, { color: colors.primary }]}>
                {showCreateCalendarForm ? "Fechar" : "+ Outro Entre Nós"}
              </Text>
            </Pressable>
          ) : null}
          {showCreateCalendarForm && mayCreate ? (
            <View
              style={[
                s.formBox,
                { borderColor: colors.border, backgroundColor: colors.bgCard, marginBottom: 12 },
              ]}
            >
              <TextInput
                value={newCalendarName}
                onChangeText={setNewCalendarName}
                placeholder="Nome do grupo"
                placeholderTextColor={colors.textMuted}
                style={inputStyle}
              />
              <Pressable
                onPress={onCreateGroup}
                disabled={creatingCalendar}
                style={[s.inviteBtn, { backgroundColor: colors.primary }]}
              >
                {creatingCalendar ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={s.inviteBtnText}>Criar grupo</Text>
                )}
              </Pressable>
            </View>
          ) : null}

          {sharedCalendars.map((cal) => {
            const cid = String(cal.id || "");
            const active = selectedSharedId === cid;
            const nmem = cal.member_count ?? cal.members?.length ?? 0;
            return (
              <Pressable
                key={cid}
                onPress={() => setSelectedSharedId(cid)}
                style={({ pressed }) => [
                  styles.calPick,
                  {
                    borderColor: colors.border,
                    backgroundColor: active ? colors.bgElevated : colors.bgCard,
                    opacity: pressed ? 0.88 : 1,
                  },
                  active && { borderLeftWidth: 4, borderLeftColor: colors.primary, paddingLeft: 12 },
                ]}
              >
                <Text style={[styles.calPickTitle, { color: colors.text }]}>
                  {(cal.name || "Entre Nós").trim()}
                </Text>
                <Text style={[styles.calPickMembers, { color: colors.text }]}>
                  {membersCardLine(cal.members, nmem, currentUserId) || "Só você — convide 1 pessoa"}
                </Text>
              </Pressable>
            );
          })}

          {selectedCalendar ? (
            <View
              style={[styles.calDetail, { borderColor: colors.border, backgroundColor: colors.bgCard }]}
            >
              <Text style={[styles.calDetailTitle, { color: colors.text }]}>
                {(selectedCalendar.name || "Entre Nós").trim()}
              </Text>
              <Text style={[styles.calDetailMembers, { color: colors.textMuted }]}>
                {membersGroupLine(selectedCalendar.members, currentUserId)}
              </Text>
              <Pressable
                onPress={() => setShowSharedEventForm((v) => !v)}
                style={({ pressed }) => [
                  s.addBtn,
                  {
                    borderColor: colors.primary,
                    backgroundColor: showSharedEventForm ? colors.primaryTint : colors.bgCard,
                    opacity: pressed ? 0.88 : 1,
                    marginBottom: 8,
                  },
                ]}
              >
                <Text style={[s.addBtnText, { color: colors.primary }]}>
                  {showSharedEventForm ? "Fechar" : "+ Enviar convite / tarefa"}
                </Text>
              </Pressable>
              {showSharedEventForm ? (
                <View style={[s.formBox, { borderColor: colors.border, backgroundColor: colors.bg }]}>
                  <TextInput
                    value={sharedEventTitle}
                    onChangeText={setSharedEventTitle}
                    placeholder="O que é?"
                    placeholderTextColor={colors.textMuted}
                    style={[
                      s.inviteInput,
                      { color: colors.text, borderColor: colors.border, backgroundColor: colors.bgCard },
                    ]}
                  />
                  <AgendaQuickPick
                    colors={colors}
                    dateValue={sharedEventDate}
                    onDatePick={setSharedEventDate}
                    titleValue={sharedEventTitle}
                    onTitlePick={setSharedEventTitle}
                  />
                  <AgendaDateTimeFields
                    colors={colors}
                    dateValue={sharedEventDate}
                    timeValue={sharedEventTime}
                    onDateChange={setSharedEventDate}
                    onTimeChange={setSharedEventTime}
                  />
                  <Pressable
                    onPress={onAddEvent}
                    disabled={savingSharedEvent}
                    style={[s.inviteBtn, { backgroundColor: colors.primary }]}
                  >
                    {savingSharedEvent ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <Text style={s.inviteBtnText}>Enviar</Text>
                    )}
                  </Pressable>
                </View>
              ) : null}
              {selectedEvents.map((ev) => {
                const eid = String(ev.id);
                return (
                  <SharedEventRow
                    key={eid}
                    event={ev}
                    colors={colors}
                    currentUserId={currentUserId}
                    creatorLabel={memberLabelFor(ev.created_by_user_id)}
                    responderLabel={memberLabelFor(ev.responded_by_user_id)}
                    onDismiss={(id) => {
                      Alert.alert("Apagar", "Apagar este item?", [
                        { text: "Cancelar", style: "cancel" },
                        {
                          text: "Apagar",
                          style: "destructive",
                          onPress: async () => {
                            setActionBusy(eid);
                            try {
                              await dismissSharedCalendarEvent(String(selectedCalendar.id), id);
                              await onRefresh();
                            } finally {
                              setActionBusy(null);
                            }
                          },
                        },
                      ]);
                    }}
                    onRespond={async (id, accept) => {
                      setActionBusy(eid);
                      try {
                        await respondEntreNosEvent(String(selectedCalendar.id), id, accept);
                        await onRefresh();
                      } finally {
                        setActionBusy(null);
                      }
                    }}
                    onShareWhatsApp={() => {
                      void shareEntreNosEventWhatsApp({
                        groupName: (selectedCalendar.name || "Entre Nós").trim(),
                        title: String(ev.title || "Compromisso"),
                        whenLabel: formatScheduledLocal(ev.scheduled_at),
                      });
                    }}
                    busy={actionBusy === eid}
                  />
                );
              })}
              {partnerSlotFull ? (
                <Text style={[s.muted, { color: colors.textMuted, marginTop: 12 }]}>
                  Parceiro(a) já neste grupo. Use «+ Outro Entre Nós» para outra pessoa.
                </Text>
              ) : (
                <>
                  <Text style={[s.sectionInner, { color: colors.textMuted, marginTop: 14 }]}>
                    Convidar 1 pessoa
                  </Text>
                  <TextInput
                    value={inviteContact}
                    onChangeText={setInviteContact}
                    placeholder="Telefone ou e-mail"
                    placeholderTextColor={colors.textMuted}
                    autoCapitalize="none"
                    style={inputStyle}
                  />
                  <Text style={[s.muted, { color: colors.textMuted, marginTop: 6, fontSize: 12 }]}>
                    Sem telefone no cadastro? Use o e-mail da pessoa — ela entra com o mesmo e-mail.
                  </Text>
                  <Pressable
                    onPress={onInvitePartner}
                    disabled={inviting}
                    style={[s.inviteBtn, { backgroundColor: colors.primary }]}
                  >
                    {inviting ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <Text style={s.inviteBtnText}>Convidar parceiro(a)</Text>
                    )}
                  </Pressable>
                  <SharedCalendarSocialInvite
                    colors={colors}
                    calendarName={(selectedCalendar?.name || "Entre Nós").trim()}
                    kind="entre_nos"
                    inviteContact={inviteContact.trim() || registeredInviteContact}
                  />
                </>
              )}
              {selectedCalendar.is_owner ? (
                <Pressable
                  onPress={() =>
                    router.push(`/(main)/shared-calendar/${String(selectedCalendar.id)}` as Href)
                  }
                  style={[styles.manageBtn, { borderColor: colors.primary }]}
                >
                  <Text style={{ color: colors.primary, fontWeight: "600" }}>
                    Gerir grupo · apagar Entre Nós
                  </Text>
                </Pressable>
              ) : (
                <Pressable
                  onPress={() =>
                    promptLeaveSharedCalendar({
                      calendar: selectedCalendar,
                      currentUserId,
                      onLeft: async () => {
                        setSelectedSharedId(null);
                        await onRefresh();
                      },
                    })
                  }
                  style={[styles.manageBtn, { borderColor: colors.danger, marginTop: 16 }]}
                >
                  <Text style={{ color: colors.danger, fontWeight: "600" }}>Sair deste Entre Nós</Text>
                </Pressable>
              )}
            </View>
          ) : null}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { borderTopWidth: 1, marginTop: 8, paddingTop: 4 },
  calPick: { borderWidth: 1.5, borderRadius: 12, padding: 14, marginBottom: 8 },
  calPickTitle: { fontSize: 16, fontWeight: "700" },
  calPickMembers: { fontSize: 14, marginTop: 6, lineHeight: 20 },
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
});
