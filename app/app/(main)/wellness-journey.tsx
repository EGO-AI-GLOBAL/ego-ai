import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
} from "react-native";
import { completePausaEgoSession } from "@/api/client";
import type { PausaEgoInfo } from "@/api/types";
import { PausaEgoScreen } from "@/components/PausaEgoScreen";
import { ScreenShell } from "@/components/ScreenShell";
import { findAvatarInCatalog } from "@/constants/avatarCatalog";
import { accountPersona, isMaleAvatar } from "@/constants/personas";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";

function defaultPausa(): PausaEgoInfo {
  return {
    streak_current: 0,
    streak_longest: 0,
    today_done: false,
    total_sessions: 0,
    moment_key: "morning",
    moment_emoji: "🌅",
    moment_title: "Manhã",
    moment_prompt: "Antes do dia: solte os ombros e respire com calma.",
    share_line: "Minha PAUSA EGO de hoje 🌬️",
    week_dots: [],
  };
}

/** PAUSA EGO — alívio de stress/ansiedade (substitui ecrã EGO de Bolso). */
export default function WellnessJourneyScreen() {
  const colors = useColors();
  const { data, loading, refreshing, error, refresh, mergePausaEgo } = useDashboard();
  const [busy, setBusy] = useState(false);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  const persona = accountPersona(data.me?.persona);
  const assistantName =
    findAvatarInCatalog(persona.avatar_id)?.shortName ??
    (isMaleAvatar(persona.avatar_id) ? "Leo" : "Luna");
  const pausa = data.pausa_ego ?? defaultPausa();

  const onComplete = useCallback(
    (kind: "breath60" | "breath120" | "sos") => {
      setBusy(true);
      void completePausaEgoSession(kind).then((next) => {
        setBusy(false);
        if (next) mergePausaEgo(next);
      });
    },
    [mergePausaEgo]
  );

  const onSosTalk = useCallback((draft: string) => {
    router.push({ pathname: "/(main)/chat", params: { draft } });
  }, []);

  return (
    <ScreenShell title="PAUSA EGO" subtitle="2 minutos de calma com seu avatar">
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.primary} />
        }
      >
        {loading && !refreshing ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
        ) : null}
        {error ? <Text style={[styles.error, { color: colors.danger }]}>{error}</Text> : null}
        {busy ? <ActivityIndicator color={colors.primary} style={{ marginBottom: 8 }} /> : null}
        {!loading || refreshing ? (
          <PausaEgoScreen
            colors={colors}
            pausa={pausa}
            assistantName={assistantName}
            onComplete={onComplete}
            onSosTalk={onSosTalk}
          />
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, paddingBottom: 32 },
  error: { marginBottom: 12, fontSize: 14 },
});
