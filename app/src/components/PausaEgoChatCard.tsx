import { router } from "expo-router";

import React, { useMemo } from "react";

import { Pressable, Share, StyleSheet, Text, View } from "react-native";

import type { PausaEgoInfo } from "@/api/types";

import type { AppColors } from "@/theme/colors";

import {

  PausaDailySessionModal,

  usePausaSessionLauncher,

} from "@/components/pausa/PausaDailySessionModal";

import {

  DEFAULT_DAILY_EXERCISE,

  formatPausaDuration,

  resolveDailyExercise,

} from "@/utils/pausaDailyExercise";



type Props = {

  colors: AppColors;

  pausa?: PausaEgoInfo | null;

  assistantName: string;

  onComplete: (kind: string) => void;

  onSosTalk?: (draft: string) => void;

  celebrate?: boolean;

};



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

    share_line: "Minha Calma 1 min de hoje 🌬️",

    week_dots: [],

    daily_exercise: DEFAULT_DAILY_EXERCISE,

  };

}



/** Cartão PAUSA EGO no chat — pausa diária anti-stress. */

export function PausaEgoChatCard({

  colors,

  pausa,

  assistantName,

  onComplete,

  onSosTalk,

  celebrate = false,

}: Props) {

  const info = pausa ?? defaultPausa();

  const daily = resolveDailyExercise(info);

  const streak = info.streak_current ?? 0;

  const highlight = !info.today_done;

  const launcher = usePausaSessionLauncher();



  const streakLine = useMemo(() => {

    if (info.today_done && streak >= 2) {

      return `Hoje cuidei de mim 🔥 ${streak} dias`;

    }

    if (info.today_done) return "Calma de hoje feita ✓";

    if (streak >= 1) return `Sequência: ${streak} dia${streak > 1 ? "s" : ""} · falta hoje`;

    return `${daily.title} — comece hoje`;

  }, [info.today_done, streak, daily.title]);



  const openSos = () => {

    onSosTalk?.(

      `Estou passando mal agora e preciso de um momento. ${assistantName}, pode me guiar com calma?`

    );

    launcher.openSos();

  };



  const finishSession = (kind: string) => {

    launcher.closeSession();

    onComplete(kind);

  };



  const onShare = () => {

    void Share.share({

      message: `${info.share_line}\n\nEGO-AI — Calma 1 min com ${assistantName}.`,

    });

  };



  const upgradeHint = info.plan_benefit?.upgrade_hint?.trim();



  return (

    <>

      <View

        style={[

          styles.wrap,

          {

            backgroundColor: highlight ? colors.primaryTint : colors.bgCard,

            borderColor: colors.primary,

            borderWidth: highlight ? 2 : 1.5,

          },

          celebrate ? styles.celebrate : null,

        ]}

      >

        <Pressable onPress={() => router.push("/(main)/wellness-journey")} style={styles.row}>

          <View style={[styles.emojiBubble, { backgroundColor: colors.primaryTint }]}>

            <Text style={styles.emoji}>{daily.emoji || "🌬️"}</Text>

          </View>

          <View style={styles.body}>

            <Text style={[styles.badge, { color: colors.primary }]}>CALMA DE HOJE 🌬️</Text>

            <Text style={[styles.title, { color: colors.text }]} numberOfLines={1}>

              {daily.title}

            </Text>

            <Text style={[styles.prompt, { color: colors.textMuted }]} numberOfLines={2}>

              {daily.subtitle}

              {daily.mood_boosted ? " · adaptada ao seu humor" : ""}

            </Text>

            {info.anywhere_line ? (
              <Text style={[styles.anywhere, { color: colors.textMuted }]} numberOfLines={1}>
                {info.anywhere_line}
              </Text>
            ) : null}

            <Text

              style={[styles.streak, { color: info.today_done ? colors.success : colors.primary }]}

            >

              {streakLine}

            </Text>

            {info.retention_line && !info.today_done ? (
              <Text style={[styles.tomorrow, { color: colors.primaryLight }]} numberOfLines={1}>
                {info.retention_line}
              </Text>
            ) : null}

          </View>

        </Pressable>



        <View style={styles.actions}>

          <Pressable

            onPress={launcher.openDaily}

            style={[styles.btn, { backgroundColor: colors.primary, flex: 1 }]}

          >

            <Text style={styles.btnText}>

              {info.today_done ? "Repetir" : "Começar"} · {formatPausaDuration(daily.duration_seconds)}

            </Text>

          </Pressable>

          <Pressable

            onPress={openSos}

            style={[styles.btnOutline, { borderColor: colors.primary, flex: 1 }]}

          >

            <Text style={[styles.btnOutlineText, { color: colors.primary }]}>SOS</Text>

          </Pressable>

        </View>



        {upgradeHint ? (

          <Pressable onPress={() => router.push("/(main)/plans")} style={styles.upgradeLink}>

            <Text style={[styles.upgradeText, { color: colors.primaryLight }]}>{upgradeHint}</Text>

          </Pressable>

        ) : null}



        <Pressable onPress={onShare} style={styles.shareLink}>

          <Text style={[styles.shareLinkText, { color: colors.primaryLight }]}>Compartilhar sequência</Text>

        </Pressable>

      </View>



      <PausaDailySessionModal

        colors={colors}

        exercise={daily}

        assistantName={assistantName}

        visible={launcher.sessionOpen}

        sosMode={launcher.sosMode}

        onClose={launcher.closeSession}

        onComplete={finishSession}

      />

    </>

  );

}



const styles = StyleSheet.create({

  wrap: {

    borderRadius: 14,

    padding: 12,

    marginBottom: 12,

  },

  celebrate: {

    transform: [{ scale: 1.01 }],

  },

  row: { flexDirection: "row", alignItems: "center", gap: 10 },

  emojiBubble: {

    width: 52,

    height: 52,

    borderRadius: 26,

    alignItems: "center",

    justifyContent: "center",

  },

  emoji: { fontSize: 26 },

  body: { flex: 1 },

  badge: { fontSize: 10, fontWeight: "900", letterSpacing: 0.4 },

  title: { fontSize: 13, fontWeight: "800", marginTop: 2 },

  prompt: { fontSize: 11, lineHeight: 15, marginTop: 4 },

  anywhere: { fontSize: 10, lineHeight: 14, marginTop: 3, fontWeight: "600" },

  streak: { fontSize: 11, fontWeight: "800", marginTop: 6 },

  tomorrow: { fontSize: 10, fontWeight: "700", marginTop: 4 },

  actions: { flexDirection: "row", gap: 8, marginTop: 10 },

  btn: {

    borderRadius: 10,

    paddingVertical: 10,

    alignItems: "center",

  },

  btnText: { color: "#fff", fontWeight: "800", fontSize: 12 },

  btnOutline: {

    borderRadius: 10,

    paddingVertical: 10,

    paddingHorizontal: 10,

    alignItems: "center",

    borderWidth: 1.5,

  },

  btnOutlineText: { fontWeight: "800", fontSize: 12 },

  upgradeLink: { marginTop: 8, alignItems: "center" },

  upgradeText: { fontSize: 10, fontWeight: "700", textAlign: "center" },

  shareLink: { marginTop: 6, alignItems: "center" },

  shareLinkText: { fontSize: 11, fontWeight: "700" },

});


