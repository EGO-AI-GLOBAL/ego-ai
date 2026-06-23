import React, { useState } from "react";
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { submitDailyCareCheckin } from "@/api/client";
import type { DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { DailyCareShareModal } from "./DailyCareShareModal";
import { SocialFollowBar } from "./SocialFollowBar";

type Props = {
  colors: AppColors;
  care?: DailyCareInfo;
  onUpdate: (care: DailyCareInfo, journey?: import("@/api/types").WellnessJourney) => void;
};

function RankingLadder({
  colors,
  care,
}: {
  colors: AppColors;
  care: DailyCareInfo;
}) {
  const rank = care.ranking;
  if (!rank?.ladder?.length) return null;
  return (
    <View style={styles.ladderWrap}>
      <View style={styles.ladderHead}>
        <Text style={[styles.ladderTitle, { color: colors.text }]}>
          🏆 {rank.tier_emoji} {rank.tier_label}
        </Text>
        <Text style={[styles.ladderSub, { color: colors.textMuted }]}>
          Top comunidade: {rank.community_top_days} dias
        </Text>
      </View>
      <View style={styles.ladderRow}>
        {rank.ladder.map((step) => (
          <View key={step.label} style={styles.ladderStep}>
            <View
              style={[
                styles.ladderDot,
                {
                  backgroundColor: step.reached ? colors.primary : colors.border,
                  opacity: step.reached ? 1 : 0.45,
                },
              ]}
            />
            <Text style={[styles.ladderEmoji, { opacity: step.reached ? 1 : 0.5 }]}>
              {step.emoji}
            </Text>
            <Text
              style={[
                styles.ladderLabel,
                { color: step.reached ? colors.text : colors.textMuted },
              ]}
              numberOfLines={1}
            >
              {step.min_days}d
            </Text>
          </View>
        ))}
      </View>
      <Text style={[styles.challengeLine, { color: colors.primary }]}>
        {rank.challenge_line}
      </Text>
      {rank.personal_best > (care.current ?? 0) ? (
        <Text style={[styles.best, { color: colors.textMuted }]}>
          Seu recorde: {rank.personal_best} dias
        </Text>
      ) : null}
    </View>
  );
}

/** Desafio diário de 1 toque — ranking visível (estilo Zip). */
export function DailyCareChallenge({ colors, care, onUpdate }: Props) {
  const [busy, setBusy] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);

  if (!care?.question) return null;

  const onPickMood = async (key: string) => {
    if (busy) return;
    setBusy(true);
    try {
      const res = await submitDailyCareCheckin(key);
      if (!res?.daily_care) {
        Alert.alert("Desafio", "Não foi possível guardar. Tente de novo.");
        return;
      }
      onUpdate(res.daily_care, res.wellness_journey);
      if (!care.checked_today) {
        const r = res.daily_care.ranking;
        const tier = r ? `${r.tier_emoji} ${r.tier_label}` : "";
        Alert.alert(
          "Desafio de hoje ✓",
          `${res.daily_care.current} dias · ${tier}\nDesafie alguém a bater seu número!`,
          [
            { text: "Depois", style: "cancel" },
            { text: "Postar", onPress: () => setShareOpen(true) },
          ]
        );
      }
    } finally {
      setBusy(false);
    }
  };

  const days = care.current ?? 0;
  const borderColor = care.at_risk ? colors.warning : colors.primary;

  return (
    <>
      <View style={[styles.wrap, { borderColor, backgroundColor: colors.bgCard }]}>
        <View style={styles.head}>
          <Text style={[styles.badge, { color: colors.primary }]}>DESAFIO DIÁRIO 💜</Text>
          {days > 0 ? (
            <Text style={[styles.streak, { color: colors.textMuted }]}>
              🔥 {days} {days === 1 ? "dia" : "dias"}
            </Text>
          ) : null}
        </View>

        <RankingLadder colors={colors} care={care} />

        <Text style={[styles.question, { color: colors.text }]}>{care.question.text}</Text>
        <Text style={[styles.hint, { color: colors.textMuted }]}>
          1 toque · volta amanhã · sobe no ranking
        </Text>

        <View style={styles.moodRow}>
          {(care.moods ?? []).map((m) => {
            const selected = care.checked_today && care.last_mood === m.key;
            return (
              <Pressable
                key={m.key}
                onPress={() => void onPickMood(m.key)}
                disabled={busy}
                style={[
                  styles.moodBtn,
                  {
                    borderColor: selected ? colors.primary : colors.border,
                    backgroundColor: selected ? colors.primaryTint : colors.bg,
                  },
                ]}
                accessibilityLabel={m.label}
              >
                <Text style={styles.moodEmoji}>{m.emoji}</Text>
              </Pressable>
            );
          })}
        </View>

        {busy ? <ActivityIndicator color={colors.primary} style={{ marginTop: 8 }} /> : null}

        {care.checked_today ? (
          <>
            <Text style={[styles.done, { color: colors.success }]}>
              ✓ Hoje: {care.last_mood_emoji} {care.last_mood_label}
            </Text>
            <Text style={[styles.hook, { color: colors.textMuted }]}>{care.share_hook}</Text>
            <Pressable
              onPress={() => setShareOpen(true)}
              style={[styles.shareBtn, { backgroundColor: colors.primary }]}
            >
              <Text style={styles.shareText}>Postar e desafiar amigos</Text>
            </Pressable>
          </>
        ) : care.at_risk ? (
          <Text style={[styles.risk, { color: colors.warning }]}>
            ⚠️ Sequência em risco — check-in hoje ou desce no ranking!
          </Text>
        ) : null}

        <SocialFollowBar colors={colors} compact />
      </View>

      <DailyCareShareModal
        colors={colors}
        care={care}
        visible={shareOpen}
        onClose={() => setShareOpen(false)}
      />
    </>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: 16,
    borderWidth: 2,
    padding: 14,
    marginBottom: 12,
  },
  head: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  badge: { fontSize: 11, fontWeight: "900", letterSpacing: 0.6 },
  streak: { fontSize: 12, fontWeight: "700" },
  ladderWrap: {
    marginBottom: 12,
    paddingBottom: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "rgba(128,128,128,0.25)",
  },
  ladderHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  ladderTitle: { fontSize: 14, fontWeight: "800" },
  ladderSub: { fontSize: 11, fontWeight: "600" },
  ladderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 10,
    paddingHorizontal: 2,
  },
  ladderStep: { alignItems: "center", flex: 1 },
  ladderDot: { width: 8, height: 8, borderRadius: 4, marginBottom: 4 },
  ladderEmoji: { fontSize: 16 },
  ladderLabel: { fontSize: 9, fontWeight: "700", marginTop: 2 },
  challengeLine: { fontSize: 12, fontWeight: "700", marginTop: 10, textAlign: "center" },
  best: { fontSize: 11, textAlign: "center", marginTop: 4 },
  question: { fontSize: 17, fontWeight: "800", lineHeight: 23 },
  hint: { fontSize: 12, marginTop: 4, marginBottom: 12 },
  moodRow: { flexDirection: "row", justifyContent: "space-between", gap: 6 },
  moodBtn: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1.5,
  },
  moodEmoji: { fontSize: 26 },
  done: { marginTop: 12, fontSize: 14, fontWeight: "700", textAlign: "center" },
  hook: { marginTop: 6, fontSize: 12, textAlign: "center", lineHeight: 17 },
  shareBtn: { marginTop: 12, borderRadius: 12, paddingVertical: 12, alignItems: "center" },
  shareText: { color: "#fff", fontWeight: "800", fontSize: 14 },
  risk: { marginTop: 10, fontSize: 13, fontWeight: "600", textAlign: "center" },
});
