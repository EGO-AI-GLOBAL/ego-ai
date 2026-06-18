import { useLocalSearchParams, useFocusEffect, useRouter } from "expo-router";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  addSharedCalendarMember,
  createSharedCalendarEvent,
  deleteSharedCalendar,
  dismissSharedCalendarEvent,
  fetchSharedCalendar,
  localDateTimeToIso,
  removeSharedCalendarMember,
} from "@/api/client";
import { markSharedCalendarEventsSeen } from "@/utils/sharedCalendarNotifications";
import { memberDisplayName, membersGroupLine } from "@/utils/sharedCalendarMembers";
import { formatScheduledLocal } from "@/utils/scheduleTime";
import type { SharedCalendar, SharedCalendarEvent } from "@/api/types";
import { ScreenShell } from "@/components/ScreenShell";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";
import type { AppColors } from "@/theme/colors";

function defaultDateBr(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${day}/${month}/${d.getFullYear()}`;
}

function formatWhen(iso?: string) {
  if (!iso) return "—";
  try {
    return formatScheduledLocal(iso);
  } catch {
    return iso.slice(0, 16).replace("T", " ");
  }
}

function sortEvents(events: SharedCalendarEvent[]) {
  return [...events].sort((a, b) => {
    const ta = a.scheduled_at ? new Date(a.scheduled_at).getTime() : 0;
    const tb = b.scheduled_at ? new Date(b.scheduled_at).getTime() : 0;
    return ta - tb;
  });
}

function ChatHint({ colors, onPress }: { colors: AppColors; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.chatHint,
        {
          borderColor: colors.primary,
          backgroundColor: colors.bgCard,
          opacity: pressed ? 0.88 : 1,
        },
      ]}
    >
      <Text style={[styles.chatHintTitle, { color: colors.text }]}>
        Marque aqui na agenda
      </Text>
      <Text style={[styles.chatHintBody, { color: colors.textMuted }]}>
        Use + Novo compromisso abaixo. Apagar funciona na lista.
      </Text>
      <Text style={[styles.chatHintLink, { color: colors.primary }]}>
        Dúvida? Pergunte no chat como fazer →
      </Text>
    </Pressable>
  );
}

export default function SharedCalendarDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const calendarId = String(id || "");
  const colors = useColors();
  const router = useRouter();
  const { session } = useAuth();
  const { refresh: refreshDashboard } = useDashboard();
  const [cal, setCal] = useState<SharedCalendar | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [inviteContact, setInviteContact] = useState("");
  const [inviting, setInviting] = useState(false);
  const [eventTitle, setEventTitle] = useState("Reunião");
  const [eventDate, setEventDate] = useState(defaultDateBr);
  const [eventTime, setEventTime] = useState("15:00");
  const [savingEvent, setSavingEvent] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    if (!session || !calendarId) return;
    setError(null);
    try {
      const row = await fetchSharedCalendar(calendarId);
      setCal(row);
      if (row) {
        await markSharedCalendarEventsSeen([row]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar agenda.");
    }
  }, [session, calendarId]);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      load().finally(() => setLoading(false));
    }, [load])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    await refreshDashboard();
    setRefreshing(false);
  };

  const isOwner = Boolean(cal?.is_owner);
  const myUserId = session?.user?.id || "";
  const events = sortEvents((cal?.events ?? []).filter((ev) => !ev.dismissed));
  const members = cal?.members ?? [];
  const calName = cal?.name?.trim() || "Agenda compartilhada";

  const onInviteContact = async () => {
    const contact = inviteContact.trim();
    if (!contact) {
      Alert.alert("Convite", "Digite telefone ou e-mail.");
      return;
    }
    setInviting(true);
    try {
      const member = await addSharedCalendarMember(calendarId, contact);
      setInviteContact("");
      await load();
      await refreshDashboard({ skipNotifications: true }).catch(() => {});
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

  const onAddEvent = async () => {
    const title = eventTitle.trim() || "Reunião";
    const iso = localDateTimeToIso(eventDate.trim(), eventTime.trim());
    if (!iso) {
      Alert.alert("Data/hora", "Use DD/MM/AAAA e HH:MM (ex.: 30/05/2026 e 15:00).");
      return;
    }
    setSavingEvent(true);
    try {
      await createSharedCalendarEvent(calendarId, {
        title,
        scheduled_at: iso,
        announce: title,
      });
      await load();
      await refreshDashboard({ skipNotifications: true }).catch(() => {});
      Alert.alert("Compromisso", `"${title}" marcado na agenda.`);
    } catch (e) {
      Alert.alert("Compromisso", e instanceof Error ? e.message : "Não foi possível marcar.");
    } finally {
      setSavingEvent(false);
    }
  };

  const onRemoveMember = (memberId: string, email: string, isMe: boolean) => {
    Alert.alert(
      isMe ? "Sair da agenda" : "Remover membro",
      isMe
        ? `Sair da agenda «${cal?.name?.trim() || "compartilhada"}»?`
        : `Remover ${email} desta agenda?`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: isMe ? "Sair" : "Remover",
          style: "destructive",
          onPress: async () => {
            setBusyId(memberId);
            try {
              await removeSharedCalendarMember(calendarId, memberId);
              await load();
              await refreshDashboard();
              if (isMe) {
                router.back();
              }
            } catch (e) {
              Alert.alert("Erro", e instanceof Error ? e.message : "Falha ao remover.");
            } finally {
              setBusyId(null);
            }
          },
        },
      ]
    );
  };

  const onDismissEvent = (eventId: string) => {
    const item = events.find((ev) => String(ev.id) === eventId);
    const title = (item?.title || "Compromisso").trim();
    Alert.alert("Apagar", `Apagar «${title}» desta agenda?`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Apagar",
        style: "destructive",
        onPress: async () => {
          setBusyId(eventId);
          try {
            await dismissSharedCalendarEvent(calendarId, eventId);
            await load();
            await refreshDashboard({ skipNotifications: true });
          } catch (e) {
            Alert.alert(
              "Erro",
              e instanceof Error ? e.message : "Não foi possível apagar o compromisso."
            );
          } finally {
            setBusyId(null);
          }
        },
      },
    ]);
  };

  const onDeleteCalendar = () => {
    Alert.alert(
      "Apagar agenda",
      `Apagar «${calName}» para todos? Esta ação não pode ser desfeita.`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Apagar",
          style: "destructive",
          onPress: async () => {
            setDeleting(true);
            try {
              await deleteSharedCalendar(calendarId);
              await refreshDashboard();
              router.replace("/(main)/agenda");
            } catch (e) {
              Alert.alert(
                "Erro",
                e instanceof Error ? e.message : "Falha ao apagar a agenda."
              );
            } finally {
              setDeleting(false);
            }
          },
        },
      ]
    );
  };

  return (
    <ScreenShell
      title={calName}
      subtitle={
        isOwner
          ? "+ Novo compromisso · Apagar na lista"
          : "Compromissos do grupo · Apagar na lista"
      }
    >
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primary}
          />
        }
      >
        <ChatHint colors={colors} onPress={() => router.push("/(main)/chat")} />

        {loading && !refreshing ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
        ) : null}
        {error ? (
          <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
        ) : null}

        {!loading && cal ? (
          <>
            <View
              style={[
                styles.groupHeader,
                { borderColor: colors.border, backgroundColor: colors.bgCard },
              ]}
            >
              <Text style={[styles.groupTitle, { color: colors.text }]}>{calName}</Text>
              <Text style={[styles.groupMembers, { color: colors.textMuted }]}>
                {membersGroupLine(members, myUserId)}
              </Text>
            </View>

            <Text style={[styles.section, { color: colors.textMuted }]}>Compromissos</Text>
            <View style={[styles.inviteBox, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
              <Text style={[styles.inviteLabel, { color: colors.textMuted }]}>
                Marcar compromisso (sem usar o chat)
              </Text>
              <TextInput
                value={eventTitle}
                onChangeText={setEventTitle}
                placeholder="Título (ex.: Reunião)"
                placeholderTextColor={colors.textMuted}
                style={[
                  styles.inviteInput,
                  { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
                ]}
              />
              <View style={styles.eventRowInputs}>
                <TextInput
                  value={eventDate}
                  onChangeText={setEventDate}
                  placeholder="DD/MM/AAAA"
                  placeholderTextColor={colors.textMuted}
                  keyboardType="numbers-and-punctuation"
                  style={[
                    styles.inviteInput,
                    styles.eventDateInput,
                    { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
                  ]}
                />
                <TextInput
                  value={eventTime}
                  onChangeText={setEventTime}
                  placeholder="HH:MM"
                  placeholderTextColor={colors.textMuted}
                  keyboardType="numbers-and-punctuation"
                  style={[
                    styles.inviteInput,
                    styles.eventTimeInput,
                    { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
                  ]}
                />
              </View>
              <Pressable
                onPress={onAddEvent}
                disabled={savingEvent}
                style={[styles.inviteBtn, { backgroundColor: colors.primary }]}
              >
                {savingEvent ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.inviteBtnText}>Marcar</Text>
                )}
              </Pressable>
            </View>
            {events.length === 0 ? (
              <Text style={[styles.muted, { color: colors.textMuted }]}>
                Nenhuma reunião marcada. Toque em + Novo compromisso.
              </Text>
            ) : (
              events.map((ev) => {
                const eid = String(ev.id);
                return (
                  <View
                    key={eid}
                    style={[styles.eventRow, { borderBottomColor: colors.border }]}
                  >
                    <View style={styles.eventBody}>
                      <Text style={[styles.eventTitle, { color: colors.text }]}>
                        {ev.title || "Reunião"}
                      </Text>
                      <Text style={[styles.eventWhen, { color: colors.textMuted }]}>
                        {formatWhen(ev.scheduled_at)}
                      </Text>
                    </View>
                    <Pressable
                      onPress={() => onDismissEvent(eid)}
                      disabled={busyId === eid}
                      style={[
                        styles.eventDismissBtn,
                        { borderColor: colors.border, opacity: busyId === eid ? 0.5 : 1 },
                      ]}
                      accessibilityLabel="Apagar compromisso"
                    >
                      <Text style={[styles.eventDismissText, { color: colors.danger }]}>
                        Apagar
                      </Text>
                    </Pressable>
                  </View>
                );
              })
            )}

            <Text style={[styles.section, { color: colors.textMuted }]}>Gerenciar membros</Text>
            <View style={[styles.inviteBox, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
                <Text style={[styles.inviteLabel, { color: colors.textMuted }]}>
                  Convidar por telefone ou e-mail
                </Text>
                <TextInput
                  value={inviteContact}
                  onChangeText={setInviteContact}
                  placeholder="11 99999-9999 ou email@exemplo.com"
                  placeholderTextColor={colors.textMuted}
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="default"
                  style={[
                    styles.inviteInput,
                    { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
                  ]}
                />
                <Pressable
                  onPress={onInviteContact}
                  disabled={inviting}
                  style={[styles.inviteBtn, { backgroundColor: colors.primary }]}
                >
                  {inviting ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.inviteBtnText}>Convidar</Text>
                  )}
                </Pressable>
              </View>
            {members.length === 0 ? (
              <Text style={[styles.muted, { color: colors.textMuted }]}>
                Nenhum membro listado.
              </Text>
            ) : (
              members.map((m) => {
                const mid = String(m.id || "");
                const email = m.invited_email || "—";
                const label = memberDisplayName(m);
                const isMe = String(m.user_id || "") === myUserId;
                const canRemove =
                  !busyId &&
                  m.role !== "owner" &&
                  (isOwner || isMe);
                return (
                  <View
                    key={mid}
                    style={[styles.memberRow, { borderBottomColor: colors.border }]}
                  >
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.memberEmail, { color: colors.text }]}>{label}</Text>
                      {email !== "—" && label.toLowerCase() !== email.toLowerCase() ? (
                        <Text style={[styles.memberEmailSub, { color: colors.textMuted }]}>
                          {email}
                        </Text>
                      ) : null}
                      <Text style={[styles.memberRole, { color: colors.textMuted }]}>
                        {m.role === "owner"
                          ? "Criador"
                          : m.status === "pending"
                            ? "Convite pendente"
                            : "Membro"}
                        {isMe ? " · você" : ""}
                      </Text>
                    </View>
                    {canRemove ? (
                      <Pressable onPress={() => onRemoveMember(mid, email, isMe)}>
                        <Text style={{ color: colors.danger, fontSize: 13 }}>
                          {isMe ? "Sair" : "Remover"}
                        </Text>
                      </Pressable>
                    ) : null}
                  </View>
                );
              })
            )}

            {isOwner ? (
              <Pressable
                onPress={onDeleteCalendar}
                disabled={deleting}
                style={({ pressed }) => [
                  styles.deleteBtn,
                  {
                    borderColor: colors.danger,
                    opacity: deleting || pressed ? 0.7 : 1,
                  },
                ]}
              >
                <Text style={[styles.deleteBtnText, { color: colors.danger }]}>
                  {deleting ? "Apagando…" : "Apagar agenda para todos"}
                </Text>
              </Pressable>
            ) : null}
          </>
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 20, paddingBottom: 32 },
  groupHeader: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
  },
  groupTitle: { fontSize: 18, fontWeight: "800", marginBottom: 8 },
  groupMembers: { fontSize: 14, lineHeight: 20 },
  chatHint: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
  },
  chatHintTitle: { fontSize: 14, fontWeight: "800", marginBottom: 6 },
  chatHintBody: { fontSize: 13, lineHeight: 18 },
  chatHintLink: { fontSize: 13, fontWeight: "700", marginTop: 10 },
  section: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginTop: 8,
    marginBottom: 10,
  },
  inviteBox: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    gap: 8,
  },
  inviteLabel: { fontSize: 12, lineHeight: 16 },
  inviteInput: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
  },
  inviteBtn: {
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
  },
  inviteBtnText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  eventRowInputs: { flexDirection: "row", gap: 8 },
  eventDateInput: { flex: 1.4 },
  eventTimeInput: { flex: 0.8 },
  muted: { fontSize: 14, lineHeight: 20, marginBottom: 8 },
  memberRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  memberEmail: { fontSize: 15, fontWeight: "600" },
  memberEmailSub: { fontSize: 12, marginTop: 2 },
  memberRole: { fontSize: 12, marginTop: 2 },
  eventRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  eventBody: { flex: 1 },
  eventTitle: { fontSize: 16, fontWeight: "600" },
  eventCalendar: { fontSize: 12, fontWeight: "600", marginTop: 4 },
  eventWhen: { fontSize: 13, marginTop: 4 },
  eventDismissBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    marginLeft: 8,
  },
  eventDismissText: { fontSize: 12, fontWeight: "700" },
  error: { fontSize: 14, marginTop: 12 },
  deleteBtn: {
    marginTop: 28,
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  deleteBtnText: { fontSize: 15, fontWeight: "700" },
});
