import { useFocusEffect, useRouter } from "expo-router";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import type { SharedCalendar, SharedCalendarEvent } from "@/api/types";
import { AgendaItemRow } from "@/components/AgendaItem";
import { ReminderItem } from "@/components/ReminderItem";
import { ScreenShell } from "@/components/ScreenShell";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";
import type { AppColors } from "@/theme/colors";

type AgendaTab = "personal" | "shared";

function formatWhen(iso?: string) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
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

function SharedEventRow({
  event,
  colors,
}: {
  event: SharedCalendarEvent;
  colors: AppColors;
}) {
  return (
    <View style={[styles.eventRow, { borderBottomColor: colors.border }]}>
      <View style={[styles.dotShared, { backgroundColor: colors.primary }]} />
      <View style={styles.eventBody}>
        <Text style={[styles.eventTitle, { color: colors.text }]} numberOfLines={2}>
          {event.title || "Compromisso"}
        </Text>
        <Text style={[styles.eventWhen, { color: colors.textMuted }]}>
          {formatWhen(event.scheduled_at)}
        </Text>
      </View>
    </View>
  );
}

function TabBar({
  tab,
  onChange,
  colors,
}: {
  tab: AgendaTab;
  onChange: (t: AgendaTab) => void;
  colors: AppColors;
}) {
  return (
    <View style={[styles.tabBar, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
      {(
        [
          ["personal", "Agenda pessoal"],
          ["shared", "Agenda compartilhada"],
        ] as const
      ).map(([id, label]) => {
        const active = tab === id;
        return (
          <Pressable
            key={id}
            onPress={() => onChange(id)}
            style={[styles.tabBtn, active && { backgroundColor: colors.primary }]}
          >
            <Text
              style={[styles.tabBtnText, { color: active ? "#fff" : colors.textMuted }]}
              numberOfLines={1}
            >
              {label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
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
      <Text style={[styles.chatHintTitle, { color: colors.primary }]}>
        Marcar, criar ou convidar
      </Text>
      <Text style={[styles.chatHintBody, { color: colors.textMuted }]}>
        Peça no chat ao avatar: compromissos pessoais, criar agenda compartilhada, dar nome
        e adicionar pessoas por e-mail.
      </Text>
      <Text style={[styles.chatHintLink, { color: colors.primary }]}>Ir para o chat →</Text>
    </Pressable>
  );
}

export default function AgendaScreen() {
  const colors = useColors();
  const router = useRouter();
  const { session } = useAuth();
  const { data, loading, refreshing, error, refresh } = useDashboard();
  const [tab, setTab] = useState<AgendaTab>("personal");
  const [selectedSharedId, setSelectedSharedId] = useState<string | null>(null);

  const sharedCalendars = data.shared_calendars ?? [];

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
    return sortEvents((selectedCalendar.events ?? []).filter((ev) => !ev.dismissed));
  }, [selectedCalendar]);

  useFocusEffect(
    useCallback(() => {
      if (session) void refresh();
    }, [session, refresh])
  );

  const subtitle =
    tab === "personal"
      ? "Consulta · só leitura"
      : "Toque numa agenda para ver os compromissos";

  return (
    <ScreenShell title="Agenda" subtitle={subtitle}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={refresh}
            tintColor={colors.primary}
          />
        }
      >
        <TabBar tab={tab} onChange={setTab} colors={colors} />
        <ChatHint colors={colors} onPress={() => router.push("/(main)/chat")} />

        {loading && !refreshing ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
        ) : null}

        {error ? (
          <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
        ) : null}

        {!loading && !error ? (
          tab === "personal" ? (
            <>
              <Text style={[styles.section, { color: colors.textMuted }]}>Compromissos</Text>
              {data.reminders.length === 0 ? (
                <Text style={[styles.muted, { color: colors.textMuted }]}>
                  Nenhum. Peça ao avatar no chat, ex.: «marca consulta sexta às 10h na minha
                  agenda».
                </Text>
              ) : (
                data.reminders.map((r) => (
                  <ReminderItem key={String(r.id)} item={r} colors={colors} />
                ))
              )}

              <Text style={[styles.section, { color: colors.textMuted }]}>Hábitos semanais</Text>
              {data.agenda.length === 0 ? (
                <Text style={[styles.muted, { color: colors.textMuted }]}>
                  Nenhum. Ex.: «academia seg–sex às 8h» no chat.
                </Text>
              ) : (
                data.agenda.map((a) => (
                  <AgendaItemRow key={String(a.id)} item={a} colors={colors} />
                ))
              )}
            </>
          ) : sharedCalendars.length === 0 ? (
            <Text style={[styles.muted, { color: colors.textMuted }]}>
              Ainda não participa de agendas compartilhadas. No chat, peça ao avatar: «cria uma
              agenda Família e convida email@exemplo.com».
            </Text>
          ) : (
            <>
              <Text style={[styles.section, { color: colors.textMuted }]}>
                Suas agendas ({sharedCalendars.length})
              </Text>
              {sharedCalendars.map((cal) => {
                const cid = String(cal.id || "");
                const calName = (cal.name || "Agenda").trim();
                const nmem = cal.member_count ?? cal.members?.length ?? 0;
                const active = selectedSharedId === cid;
                const evCount = (cal.events ?? []).filter((e) => !e.dismissed).length;
                return (
                  <Pressable
                    key={cid}
                    onPress={() => setSelectedSharedId(cid)}
                    style={({ pressed }) => [
                      styles.calPick,
                      {
                        borderColor: active ? colors.primary : colors.border,
                        backgroundColor: active ? colors.primaryLight : colors.bgCard,
                        opacity: pressed ? 0.88 : 1,
                      },
                    ]}
                  >
                    <Text
                      style={[
                        styles.calPickTitle,
                        { color: active ? colors.primary : colors.text },
                      ]}
                      numberOfLines={2}
                    >
                      {calName}
                    </Text>
                    <Text style={[styles.calPickMeta, { color: colors.textMuted }]}>
                      {nmem} membro{nmem === 1 ? "" : "s"}
                      {cal.is_owner ? " · você criou" : ""}
                      {" · "}
                      {evCount} compromisso{evCount === 1 ? "" : "s"}
                    </Text>
                  </Pressable>
                );
              })}

              {selectedCalendar ? (
                <View
                  style={[
                    styles.calDetail,
                    { borderColor: colors.border, backgroundColor: colors.bgCard },
                  ]}
                >
                  <Text style={[styles.calDetailTitle, { color: colors.text }]}>
                    {(selectedCalendar.name || "Agenda").trim()}
                  </Text>
                  <Text style={[styles.sectionInner, { color: colors.textMuted }]}>
                    Compromissos marcados
                  </Text>
                  {selectedEvents.length === 0 ? (
                    <Text style={[styles.muted, { color: colors.textMuted }]}>
                      Nenhum nesta agenda. Peça no chat para marcar um compromisso aqui.
                    </Text>
                  ) : (
                    selectedEvents.map((ev) => (
                      <SharedEventRow key={String(ev.id)} event={ev} colors={colors} />
                    ))
                  )}
                </View>
              ) : null}
            </>
          )
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 20, paddingBottom: 32 },
  tabBar: {
    flexDirection: "row",
    borderWidth: 1,
    borderRadius: 12,
    padding: 4,
    marginBottom: 12,
    gap: 4,
  },
  tabBtn: {
    flex: 1,
    borderRadius: 9,
    paddingVertical: 10,
    paddingHorizontal: 6,
    alignItems: "center",
  },
  tabBtnText: { fontSize: 13, fontWeight: "700" },
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
    marginTop: 4,
    marginBottom: 10,
  },
  sectionInner: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginTop: 8,
    marginBottom: 8,
  },
  muted: { fontSize: 14, lineHeight: 20, marginBottom: 8 },
  error: { fontSize: 14, marginTop: 12 },
  calPick: {
    borderWidth: 1.5,
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
  },
  calPickTitle: { fontSize: 16, fontWeight: "700" },
  calPickMeta: { fontSize: 12, marginTop: 4 },
  calDetail: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginTop: 12,
  },
  calDetailTitle: { fontSize: 17, fontWeight: "800", marginBottom: 4 },
  eventRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  dotShared: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 6,
    marginRight: 10,
  },
  eventBody: { flex: 1 },
  eventTitle: { fontSize: 15, fontWeight: "600" },
  eventWhen: { fontSize: 13, marginTop: 2 },
});
