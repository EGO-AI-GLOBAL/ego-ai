import { router } from "expo-router";
import React, { useMemo, useRef, useState } from "react";
import { Pressable, Share, StyleSheet, Text, View } from "react-native";
import type { PausaEgoInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { PausaBreathSession } from "@/components/pausa/PausaBreathSession";

type Props = {
  colors: AppColors;
  pausa?: PausaEgoInfo | null;
  assistantName: string;
  onComplete: (kind: "breath60" | "sos") => void;
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
    share_line: "Minha PAUSA EGO de hoje 🌬️",
    week_dots: [],
  };
}

/** Cartão PAUSA EGO no chat — substitui EGO de Bolso. */
export function PausaEgoChatCard({
  colors,
  pausa,
  assistantName,
  onComplete,
  onSosTalk,
  celebrate = false,
}: Props) {
  const [breathOpen, setBreathOpen] = useState(false);
  const sessionKindRef = useRef<"breath60" | "sos">("breath60");
  const info = pausa ?? defaultPausa();
  const streak = info.streak_current ?? 0;
  const highlight = !info.today_done;

  const streakLine = useMemo(() => {
    if (info.today_done && streak >= 2) {
      return `Hoje cuidei de mim 🔥 ${streak} dias`;
    }
    if (info.today_done) return "PAUSA de hoje feita ✓";
    if (streak >= 1) return `Sequência: ${streak} dia${streak > 1 ? "s" : ""} · falta hoje`;
    return "2 minutos de calma — comece hoje";
  }, [info.today_done, streak]);

  const openBreath = (kind: "breath60" | "sos") => {
    sessionKindRef.current = kind;
    if (kind === "sos") {
      onSosTalk?.(
        `Estou passando mal agora e preciso de um momento. ${assistantName}, pode me guiar com calma?`
      );
    }
    setBreathOpen(true);
  };

  const finishBreath = () => {
    setBreathOpen(false);
    onComplete(sessionKindRef.current);
  };

  const onShare = () => {
    void Share.share({
      message: `${info.share_line}\n\nEGO-AI — PAUSA de 2 min com ${assistantName}.`,
    });
  };

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
            <Text style={styles.emoji}>{info.moment_emoji || "🌬️"}</Text>
          </View>
          <View style={styles.body}>
            <Text style={[styles.badge, { color: colors.primary }]}>PAUSA EGO 🌬️</Text>
            <Text style={[styles.title, { color: colors.text }]} numberOfLines={1}>
              {info.moment_title} · com {assistantName}
            </Text>
            <Text style={[styles.prompt, { color: colors.textMuted }]} numberOfLines={2}>
              {info.moment_prompt}
            </Text>
            <Text
              style={[styles.streak, { color: info.today_done ? colors.success : colors.primary }]}
            >
              {streakLine}
            </Text>
          </View>
        </Pressable>

        <View style={styles.actions}>
          <Pressable
            onPress={() => openBreath("breath60")}
            style={[styles.btn, { backgroundColor: colors.primary, flex: 1.3 }]}
          >
            <Text style={styles.btnText}>Respirar 60s</Text>
          </Pressable>
          <Pressable
            onPress={() => openBreath("sos")}
            style={[styles.btnOutline, { borderColor: colors.primary, flex: 1 }]}
          >
            <Text style={[styles.btnOutlineText, { color: colors.primary }]}>Estou mal</Text>
          </Pressable>
          <Pressable
            onPress={onShare}
            style={[styles.btnOutline, { borderColor: colors.primary }]}
          >
            <Text style={[styles.btnOutlineText, { color: colors.primary }]}>Postar</Text>
          </Pressable>
        </View>
      </View>

      <PausaBreathSession
        colors={colors}
        visible={breathOpen}
        assistantName={assistantName}
        onClose={() => setBreathOpen(false)}
        onComplete={finishBreath}
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
  streak: { fontSize: 11, fontWeight: "800", marginTop: 6 },
  actions: { flexDirection: "row", gap: 8, marginTop: 10 },
  btn: {
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "800", fontSize: 13 },
  btnOutline: {
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 10,
    alignItems: "center",
    borderWidth: 1.5,
  },
  btnOutlineText: { fontWeight: "800", fontSize: 12 },
});
