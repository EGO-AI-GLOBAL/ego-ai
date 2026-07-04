import React, { useRef, useState } from "react";
import { Pressable, Share, StyleSheet, Text, View } from "react-native";
import type { PausaEgoInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { PausaBreathSession } from "@/components/pausa/PausaBreathSession";

type Props = {
  colors: AppColors;
  pausa: PausaEgoInfo;
  assistantName: string;
  onComplete: (kind: "breath60" | "sos") => void;
  onSosTalk?: (draft: string) => void;
};

export function PausaEgoScreen({ colors, pausa, assistantName, onComplete, onSosTalk }: Props) {
  const [breathOpen, setBreathOpen] = useState(false);
  const sessionKindRef = useRef<"breath60" | "sos">("breath60");
  const streak = pausa.streak_current ?? 0;

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

  return (
    <>
      <View style={[styles.hero, { backgroundColor: colors.primaryTint, borderColor: colors.primary }]}>
        <Text style={[styles.heroBadge, { color: colors.primary }]}>PAUSA EGO 🌬️</Text>
        <Text style={[styles.heroTitle, { color: colors.text }]}>
          {pausa.moment_emoji} {pausa.moment_title}
        </Text>
        <Text style={[styles.heroPrompt, { color: colors.textMuted }]}>{pausa.moment_prompt}</Text>
        <Text style={[styles.heroStreak, { color: colors.primary }]}>
          {streak >= 2
            ? `🔥 ${streak} dias seguidos`
            : pausa.today_done
              ? "PAUSA de hoje feita ✓"
              : "Comece sua sequência hoje"}
        </Text>
      </View>

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
        onPress={() => openBreath("breath60")}
        style={[styles.primaryBtn, { backgroundColor: colors.primary }]}
      >
        <Text style={styles.primaryBtnText}>Respirar 60s com {assistantName}</Text>
      </Pressable>

      <Pressable
        onPress={() => openBreath("sos")}
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
            message: `${pausa.share_line}\n\nEGO-AI — PAUSA de 2 min.`,
          })
        }
        style={[styles.shareBtn, { borderColor: colors.border }]}
      >
        <Text style={[styles.shareText, { color: colors.textMuted }]}>Compartilhar sequência</Text>
      </Pressable>

      <Text style={[styles.footer, { color: colors.textMuted }]}>
        Alívio de stress e ansiedade em ~2 minutos. Não substitui acompanhamento profissional.
      </Text>

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
  hero: {
    borderRadius: 16,
    borderWidth: 1.5,
    padding: 16,
    marginBottom: 16,
  },
  heroBadge: { fontSize: 11, fontWeight: "900", letterSpacing: 0.4 },
  heroTitle: { fontSize: 22, fontWeight: "900", marginTop: 6 },
  heroPrompt: { fontSize: 14, lineHeight: 20, marginTop: 8 },
  heroStreak: { fontSize: 13, fontWeight: "800", marginTop: 12 },
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
  primaryBtnText: { color: "#fff", fontWeight: "900", fontSize: 16 },
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
