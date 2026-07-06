import { router } from "expo-router";

import React from "react";

import { Pressable, Share, StyleSheet, Text, View } from "react-native";

import type { PausaEgoInfo } from "@/api/types";

import type { AppColors } from "@/theme/colors";

import {

  PausaDailySessionModal,

  usePausaSessionLauncher,

} from "@/components/pausa/PausaDailySessionModal";

import { formatPausaDuration, resolveDailyExercise } from "@/utils/pausaDailyExercise";



type Props = {

  colors: AppColors;

  pausa: PausaEgoInfo;

  assistantName: string;

  onComplete: (kind: string) => void;

  onSosTalk?: (draft: string) => void;

};



export function PausaEgoScreen({ colors, pausa, assistantName, onComplete, onSosTalk }: Props) {

  const daily = resolveDailyExercise(pausa);

  const streak = pausa.streak_current ?? 0;

  const launcher = usePausaSessionLauncher();

  const benefit = pausa.plan_benefit;



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



  return (

    <>

      <View style={[styles.hero, { backgroundColor: colors.primaryTint, borderColor: colors.primary }]}>

        <Text style={[styles.heroBadge, { color: colors.primary }]}>PAUSA EGO 🌬️</Text>

        <Text style={[styles.heroTitle, { color: colors.text }]}>

          {daily.emoji} {daily.title}

        </Text>

        <Text style={[styles.heroPrompt, { color: colors.textMuted }]}>{daily.subtitle}</Text>
        {pausa.anywhere_line ? (
          <Text style={[styles.anywhereLine, { color: colors.textMuted }]}>{pausa.anywhere_line}</Text>
        ) : null}

        {daily.mood_boosted ? (

          <Text style={[styles.moodBoost, { color: colors.primary }]}>

            Adaptada ao seu humor de hoje (Monstrinhos)

          </Text>

        ) : null}

        {pausa.retention_line ? (
          <Text style={[styles.retentionLine, { color: colors.primaryLight }]}>
            {pausa.retention_line}
          </Text>
        ) : null}

        <Text style={[styles.heroStreak, { color: colors.primary }]}>

          {streak >= 2

            ? `🔥 ${streak} dias seguidos`

            : pausa.today_done

              ? "PAUSA de hoje feita ✓"

              : "Comece sua sequência hoje"}

        </Text>

      </View>



      {benefit?.upgrade_hint?.trim() ? (

        <View style={[styles.planCard, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>

          <Text style={[styles.planHeadline, { color: colors.text }]}>{benefit.headline}</Text>

          <Text style={[styles.planDetail, { color: colors.textMuted }]}>{benefit.detail}</Text>

          {benefit.upgrade_hint ? (

            <Pressable onPress={() => router.push("/(main)/plans")}>

              <Text style={[styles.planUpgrade, { color: colors.primary }]}>{benefit.upgrade_hint}</Text>

            </Pressable>

          ) : null}

        </View>

      ) : null}



      <View style={styles.weekRow}>

        {(pausa.week_dots ?? []).map((dot) => (

          <View key={dot.date} style={styles.weekCell}>

            <View

              style={[

                styles.weekDot,

                {

                  backgroundColor: dot.done ? colors.primary : colors.border,

                  borderColor: dot.today ? colors.primary : "transparent",

                  borderWidth: dot.today ? 2 : 0,

                },

              ]}

            />

            <Text style={[styles.weekLabel, { color: colors.textMuted }]}>

              {dot.date.slice(-2)}

            </Text>

          </View>

        ))}

      </View>



      <Pressable

        onPress={launcher.openDaily}

        style={[styles.primaryBtn, { backgroundColor: colors.primary }]}

      >

        <Text style={styles.primaryBtnText}>

          {pausa.today_done ? "Repetir pausa de hoje" : "Começar pausa de hoje"} ·{" "}

          {formatPausaDuration(daily.duration_seconds)}

        </Text>

      </Pressable>



      <Pressable

        onPress={openSos}

        style={[styles.sosBtn, { borderColor: colors.primary, backgroundColor: colors.bgCard }]}

      >

        <Text style={[styles.sosBtnText, { color: colors.primary }]}>Estou mal agora</Text>

        <Text style={[styles.sosHint, { color: colors.textMuted }]}>

          SOS — respiração guiada + conversa no chat

        </Text>

      </Pressable>



      <Pressable

        onPress={() =>

          void Share.share({

            message: `${pausa.share_line}\n\nEGO-AI — PAUSA anti-stress.`,

          })

        }

        style={[styles.shareBtn, { borderColor: colors.border }]}

      >

        <Text style={[styles.shareText, { color: colors.textMuted }]}>Compartilhar sequência</Text>

      </Pressable>



      <Text style={[styles.footer, { color: colors.textMuted }]}>

        Alívio de stress e ansiedade — em casa, no escritório ou a caminho. Não substitui acompanhamento profissional.

      </Text>



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

  hero: {

    borderRadius: 16,

    borderWidth: 1.5,

    padding: 16,

    marginBottom: 12,

  },

  heroBadge: { fontSize: 11, fontWeight: "900", letterSpacing: 0.4 },

  heroTitle: { fontSize: 22, fontWeight: "900", marginTop: 6 },

  heroPrompt: { fontSize: 14, lineHeight: 20, marginTop: 8 },

  anywhereLine: { fontSize: 12, lineHeight: 17, marginTop: 6, fontWeight: "600" },

  moodBoost: { fontSize: 12, fontWeight: "800", marginTop: 8 },

  retentionLine: { fontSize: 12, fontWeight: "700", marginTop: 8 },

  heroStreak: { fontSize: 13, fontWeight: "800", marginTop: 12 },

  planCard: {

    borderRadius: 12,

    borderWidth: 1,

    padding: 12,

    marginBottom: 16,

  },

  planHeadline: { fontSize: 14, fontWeight: "900" },

  planDetail: { fontSize: 12, lineHeight: 17, marginTop: 4 },

  planUpgrade: { fontSize: 12, fontWeight: "800", marginTop: 8 },

  weekRow: {

    flexDirection: "row",

    justifyContent: "space-between",

    marginBottom: 20,

    paddingHorizontal: 4,

  },

  weekCell: { alignItems: "center", gap: 4 },

  weekDot: { width: 14, height: 14, borderRadius: 7 },

  weekLabel: { fontSize: 10, fontWeight: "700" },

  primaryBtn: {

    borderRadius: 14,

    paddingVertical: 16,

    alignItems: "center",

    marginBottom: 12,

  },

  primaryBtnText: { color: "#fff", fontWeight: "900", fontSize: 15, textAlign: "center" },

  sosBtn: {

    borderRadius: 14,

    borderWidth: 1.5,

    padding: 14,

    marginBottom: 12,

  },

  sosBtnText: { fontWeight: "900", fontSize: 16 },

  sosHint: { fontSize: 12, marginTop: 4, lineHeight: 16 },

  shareBtn: {

    borderRadius: 12,

    borderWidth: 1,

    paddingVertical: 12,

    alignItems: "center",

    marginBottom: 16,

  },

  shareText: { fontWeight: "700", fontSize: 13 },

  footer: { fontSize: 11, lineHeight: 16, textAlign: "center" },

});


