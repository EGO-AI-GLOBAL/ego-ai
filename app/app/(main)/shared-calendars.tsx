import { useFocusEffect, useRouter } from "expo-router";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { fetchSharedCalendars } from "@/api/client";
import type { SharedCalendar } from "@/api/types";
import { ScreenShell } from "@/components/ScreenShell";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";
import type { AppColors } from "@/theme/colors";

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
        Criar ou convidar
      </Text>
      <Text style={[styles.chatHintBody, { color: colors.textMuted }]}>
        Use a aba Agenda compartilhada: + Nova agenda, convide por e-mail ou telefone.
      </Text>
      <Text style={[styles.chatHintLink, { color: colors.primary }]}>
        Dúvida? Pergunte no chat como fazer →
      </Text>
    </Pressable>
  );
}

export default function SharedCalendarsScreen() {
  const colors = useColors();
  const router = useRouter();
  const { session } = useAuth();
  const { data, refresh: refreshDashboard } = useDashboard();
  const [list, setList] = useState<SharedCalendar[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!session) return;
    setError(null);
    try {
      const rows = await fetchSharedCalendars();
      setList(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar agendas.");
    }
  }, [session]);

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

  return (
    <ScreenShell
      title="Agendas compartilhadas"
      subtitle="Consulta · só leitura"
      adsAccess={data.access ?? null}
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

        {!loading || refreshing || Boolean(error) ? (
          <>
            <Text style={[styles.section, { color: colors.textMuted }]}>Suas agendas</Text>
            {list.length === 0 ? (
              <Text style={[styles.muted, { color: colors.textMuted }]}>
                Ainda não participa de agendas compartilhadas.
              </Text>
            ) : (
              list.map((c) => (
                <Pressable
                  key={String(c.id)}
                  onPress={() => router.push(`/(main)/shared-calendar/${c.id}`)}
                  style={({ pressed }) => [
                    styles.row,
                    {
                      borderColor: colors.border,
                      backgroundColor: colors.bgCard,
                      opacity: pressed ? 0.85 : 1,
                    },
                  ]}
                >
                  <Text style={[styles.rowTitle, { color: colors.text }]} numberOfLines={2}>
                    {c.name || "Agenda"}
                  </Text>
                  <Text style={[styles.rowSub, { color: colors.textMuted }]}>
                    {c.member_count ?? c.members?.length ?? 0} membros
                    {c.is_owner ? " · você criou" : ""}
                  </Text>
                </Pressable>
              ))
            )}
          </>
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 20, paddingBottom: 32 },
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
    marginBottom: 10,
  },
  muted: { fontSize: 14, lineHeight: 20 },
  error: { fontSize: 14, marginTop: 12 },
  row: { borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 10 },
  rowTitle: { fontSize: 16, fontWeight: "600" },
  rowSub: { fontSize: 13, marginTop: 4 },
});
