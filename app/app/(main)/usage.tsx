import { router } from "expo-router";
import { useFocusEffect } from "expo-router";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { ScreenShell } from "@/components/ScreenShell";
import { UsageDashboard } from "@/components/UsageDashboard";
import { useDashboard } from "@/hooks/useDashboard";
import { loadLocalChatHistory } from "@/storage/chatHistoryLocal";
import { useColors } from "@/theme/ThemeContext";
import { primaryTokenPercent } from "@/utils/usageStats";

export default function UsageScreen() {
  const colors = useColors();
  const { data, loading, refreshing, error, refresh } = useDashboard();
  const userId = data.me?.user_id || "";
  const chatLocal =
    data.chat_local_history ?? data.access?.chat_local_history ?? true;
  const [localMsgCount, setLocalMsgCount] = useState(0);

  useEffect(() => {
    if (!userId.trim()) {
      setLocalMsgCount(0);
      return;
    }
    void loadLocalChatHistory(userId).then((msgs) => setLocalMsgCount(msgs.length));
  }, [userId, refreshing]);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  const pct = primaryTokenPercent(data.access);

  return (
    <ScreenShell title="Uso" subtitle="Percentagem do seu plano">
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
        {loading && !refreshing ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
        ) : null}

        {error ? (
          <Pressable onPress={refresh}>
            <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
          </Pressable>
        ) : null}

        {!loading && !error ? (
          <>
            <Text style={[styles.intro, { color: colors.textMuted }]}>
              Acompanhe o uso do seu plano em percentagem. Atualize após conversar no chat.
            </Text>

            <UsageDashboard colors={colors} access={data.access} expanded />

            <View style={[styles.summaryRow, { borderColor: colors.border }]}>
              <Text style={[styles.summaryLabel, { color: colors.textMuted }]}>
                Status da conta
              </Text>
              <Text style={[styles.summaryValue, { color: colors.text }]}>
                {data.access?.access_status || "—"}
              </Text>
            </View>

            <View style={[styles.summaryRow, { borderColor: colors.border }]}>
              <Text style={[styles.summaryLabel, { color: colors.textMuted }]}>
                Mensagens no chat
              </Text>
              <Text style={[styles.summaryValue, { color: colors.text }]}>
                {chatLocal ? localMsgCount : data.messages.length}
              </Text>
            </View>
            {chatLocal ? (
              <Text style={[styles.localHint, { color: colors.textMuted }]}>
                O histórico de conversa fica guardado só no seu aparelho.
              </Text>
            ) : null}

            {pct >= 75 ? (
              <Pressable
                onPress={() => router.push("/(main)/plans")}
                style={({ pressed }) => [
                  styles.cta,
                  { backgroundColor: colors.primary, opacity: pressed ? 0.9 : 1 },
                ]}
              >
                <Text style={styles.ctaText}>Ver planos com mais limite</Text>
              </Pressable>
            ) : null}
          </>
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 20, paddingBottom: 40 },
  intro: { fontSize: 15, lineHeight: 22, marginBottom: 16 },
  summaryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  summaryLabel: { fontSize: 14 },
  summaryValue: { fontSize: 14, fontWeight: "600" },
  localHint: { fontSize: 13, lineHeight: 19, marginTop: 4, marginBottom: 8 },
  cta: {
    marginTop: 20,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  ctaText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  error: { fontSize: 14 },
});
