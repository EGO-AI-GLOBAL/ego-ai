import React, { useRef, useState } from "react";
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from "react-native";
import * as Haptics from "expo-haptics";
import { submitDailyCareCheckin } from "@/api/client";
import type { DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { resolveMoodLabel } from "@/constants/moodMonsters";
import { queueMonsterChatNotice } from "@/utils/monsterChatNotice";
import { DailyCareShareModal } from "./DailyCareShareModal";
import { MoodAdventureBanner } from "./moodMonsters/MoodAdventureBanner";
import { MoodCrisisBridgeCard } from "./moodMonsters/MoodCrisisBridgeCard";
import { MoodDailyGoals } from "./moodMonsters/MoodDailyGoals";
import { MoodGentlenessRibbon } from "./moodMonsters/MoodGentlenessRibbon";
import { MoodGoalsCompleteBurst } from "./moodMonsters/MoodGoalsCompleteBurst";
import { MoodJournalTodayNote } from "./moodMonsters/MoodJournalTodayNote";
import { MoodJournalWeek } from "./moodMonsters/MoodJournalWeek";
import { MoodMonsterScene } from "./moodMonsters/MoodMonsterScene";
import {
  requestGoalClip,
  requestMoodReact,
  type MonsterPetPlayRequest,
} from "./moodMonsters/MoodMonsterStickyPet";
import { MoodSeedShop } from "./moodMonsters/MoodSeedShop";
import { MoodSocialInviteCard } from "./moodMonsters/MoodSocialInviteCard";
import { MoodWeeklyQuizCard } from "./moodMonsters/MoodWeeklyQuizCard";
import { SeasonalEventBanner } from "./moodMonsters/SeasonalEventBanner";
import { SocialFollowBar } from "./SocialFollowBar";

type Props = {
  colors: AppColors;
  care?: DailyCareInfo;
  userId?: string;
  onUpdate: (care: DailyCareInfo, journey?: import("@/api/types").WellnessJourney) => void;
  /** Preview de humor (PressIn) → muda cor do idle sticky. */
  onPetMoodPreview?: (moodKey: string | undefined) => void;
  /** One-shot no pet sticky. */
  onPetPlay?: (req: MonsterPetPlayRequest) => void;
  /** Conteúdo após o humor (banner/lead) — humor fica 1º sob o pet. */
  afterMood?: React.ReactNode;
};

function RankingLadder({ colors, care }: { colors: AppColors; care: DailyCareInfo }) {
  const rank = care.ranking;
  if (!rank?.ladder?.length) return null;
  return (
    <View style={styles.ladderWrap}>
      <View style={styles.ladderHead}>
        <Text style={[styles.ladderTitle, { color: colors.text }]}>
          🏆 {rank.tier_emoji} {rank.tier_label}
        </Text>
        <Text style={[styles.ladderSub, { color: colors.textMuted }]}>
          Nível {rank.tier_index}/{rank.tier_total} · top {rank.community_top_days}d
        </Text>
      </View>
      <View style={styles.ladderRow}>
        {rank.ladder.map((step) => (
          <View key={`tier-${step.min_days}`} style={styles.ladderStep}>
            <View
              style={[
                styles.ladderDot,
                {
                  backgroundColor: step.reached ? colors.primary : colors.border,
                  opacity: step.reached ? 1 : 0.45,
                },
              ]}
            />
            <Text style={[styles.ladderEmoji, { opacity: step.reached ? 1 : 0.5 }]}>{step.emoji}</Text>
            <Text
              style={[styles.ladderLabel, { color: step.reached ? colors.text : colors.textMuted }]}
              numberOfLines={1}
            >
              {step.min_days}d
            </Text>
          </View>
        ))}
      </View>
      <Text style={[styles.challengeLine, { color: colors.primary }]}>{rank.challenge_line}</Text>
    </View>
  );
}

/** Monstrinhos do Humor — jardim + pet vídeo sticky (idle loop + reações). */
export function DailyCareChallenge({
  colors,
  care,
  userId,
  onUpdate,
  onPetMoodPreview,
  onPetPlay,
  afterMood,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [celebrate, setCelebrate] = useState(false);
  const [goalsBurst, setGoalsBurst] = useState(false);
  const [burstCongrats, setBurstCongrats] = useState<string | undefined>();
  const [hoverMood, setHoverMood] = useState<string | undefined>();
  const playNonce = useRef(0);
  const pickingMood = useRef(false);

  const setPreview = (key: string | undefined) => {
    setHoverMood(key);
    onPetMoodPreview?.(key);
  };

  const playPet = (req: MonsterPetPlayRequest) => {
    onPetPlay?.(req);
  };
  if (!care?.question) {
    return (
      <View style={[styles.wrap, { borderColor: colors.border, backgroundColor: colors.bgCard, opacity: 0.92 }]}>
        <Text style={[styles.badge, { color: colors.primary }]}>MONSTRINHOS DO HUMOR 💜</Text>
        <Text style={[styles.hint, { color: colors.textMuted, marginTop: 8 }]}>
          Jardim a sincronizar… puxe para baixo para atualizar.
        </Text>
        <Text style={[styles.hint, { color: colors.textMuted, marginTop: 6, fontSize: 11 }]}>
          Se continuar vazio após 2 min, saia da conta e entre de novo.
        </Text>
      </View>
    );
  }

  const onPickMood = async (key: string) => {
    if (busy) return;
    setBusy(true);
    pickingMood.current = true;
    // Reação imediata (Short ~230 humor/monstrinho — Finch PT <10s, sem esperar API).
    setPreview(key);
    setCelebrate(true);
    playNonce.current += 1;
    playPet(requestMoodReact(playNonce.current));
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => undefined);
    try {
      const res = await submitDailyCareCheckin(key);
      if (!res?.daily_care) {
        setCelebrate(false);
        setPreview(undefined);
        Alert.alert("Monstrinhos", "Não foi possível guardar. Tente de novo.");
        return;
      }
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => undefined);
      setTimeout(() => setCelebrate(false), 1200);
      onUpdate(res.daily_care, res.wellness_journey);
      setPreview(undefined);
      // Sem Alert no 1º humor — métricas Finch: <2 toques, sem modal.
      if (!care.checked_today) {
        const line = res.daily_care.monster_line?.trim();
        if (line) void queueMonsterChatNotice(line);
      }
    } finally {
      pickingMood.current = false;
      setBusy(false);
    }
  };

  const days = care.current ?? 0;
  const borderColor = care.at_risk ? colors.warning : colors.primary;
  const todayLabel = resolveMoodLabel(care.moods, care.last_mood, care.last_mood_label);
  const needsCheckin = !care.checked_today;
  const gentleBadge =
    care.gentleness?.gentle_mode ||
    care.gentleness?.night_garden ||
    care.gentleness?.sunday_garden;

  const moodCheckIn = (
    <View
      style={[
        styles.moodFirst,
        {
          borderColor: needsCheckin ? colors.primary : colors.border,
          backgroundColor: needsCheckin ? colors.primaryTint : "transparent",
        },
      ]}
    >
      {needsCheckin ? (
        <Text style={[styles.stepBadge, { color: colors.primary }]}>1º PASSO — MARQUE O HUMOR</Text>
      ) : null}
      <Text style={[styles.question, { color: colors.text }]}>{care.question.text}</Text>
      <Text style={[styles.hint, { color: colors.textMuted }]}>
        {needsCheckin
          ? "1 toque — o monstrinho reage agora · missões abrem a seguir"
          : "Toque para mudar o humor de hoje"}
      </Text>

      <View style={styles.moodRow}>
        {(care.moods ?? []).map((m) => {
          const selected = care.checked_today && care.last_mood === m.key;
          const preview = hoverMood === m.key;
          return (
            <Pressable
              key={m.key}
              onPressIn={() => setPreview(m.key)}
              onPressOut={() => {
                if (!pickingMood.current) setPreview(undefined);
              }}
              onPress={() => void onPickMood(m.key)}
              disabled={busy}
              style={[
                styles.moodBtn,
                {
                  borderColor: selected || preview ? colors.primary : colors.border,
                  backgroundColor: selected || preview ? colors.primaryTint : colors.bg,
                  transform: [{ scale: preview ? 1.06 : 1 }],
                },
              ]}
              accessibilityLabel={m.label}
            >
              <Text style={styles.moodEmoji}>{m.emoji}</Text>
              <Text style={[styles.moodLabel, { color: colors.textMuted }]} numberOfLines={1}>
                {m.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {busy ? <ActivityIndicator color={colors.primary} style={{ marginTop: 8 }} /> : null}

      {care.checked_today ? (
        <>
          <Text style={[styles.done, { color: colors.success }]}>
            ✓ Hoje: {todayLabel} no jardim
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
          ⚠️ Sequência em risco — salve o jardim com 1 toque!
        </Text>
      ) : null}
    </View>
  );

  return (
    <>
      {/* 1º no scroll sob o pet sticky — define a cor do monstrinho. */}
      {moodCheckIn}

      <View style={[styles.wrap, { borderColor, backgroundColor: colors.bgCard }]}>
        <MoodGoalsCompleteBurst
          colors={colors}
          visible={goalsBurst}
          bonus={care.all_goals_bonus ?? 3}
          totalGoals={care.daily_goals?.length ?? 5}
          congratsLine={burstCongrats ?? care.avatar_congrats}
          onDone={() => {
            setGoalsBurst(false);
            setBurstCongrats(undefined);
          }}
        />
        <View style={styles.head}>
          <Text style={[styles.badge, { color: colors.primary }]}>
            {gentleBadge ? "JARDIM DA GENTILEZA 💜" : "MONSTRINHOS DO HUMOR 💜"}
          </Text>
          {days > 0 ? (
            <Text style={[styles.streak, { color: colors.textMuted }]}>
              💜 {days} {days === 1 ? "dia" : "dias"}
            </Text>
          ) : null}
        </View>

        <SeasonalEventBanner colors={colors} event={care.seasonal_event} />

        <MoodGentlenessRibbon colors={colors} gentleness={care.gentleness} />

        {afterMood}

        <MoodMonsterScene
          colors={colors}
          care={care}
          celebrate={celebrate}
          previewMood={hoverMood}
          hidePet
        />

        <MoodCrisisBridgeCard colors={colors} care={care} onUpdate={(next) => onUpdate(next)} />

        <MoodJournalWeek colors={colors} entries={care.mood_journal} moods={care.moods} />

        <MoodJournalTodayNote colors={colors} care={care} onUpdate={(next) => onUpdate(next)} />

        {care.adventure?.active || care.adventure?.collected ? (
          <MoodAdventureBanner colors={colors} adventure={care.adventure} />
        ) : null}

        {needsCheckin ? (
          <Text style={[styles.missionsLocked, { color: colors.textMuted }]}>
            {care.gentleness?.crisis_bridge?.show
              ? "3º passo — missões gentis depois da Calma 1 min"
              : "2º passo — complete as missões depois de marcar o humor"}
          </Text>
        ) : null}

        <MoodDailyGoals
          colors={colors}
          care={care}
          userId={userId}
          onUpdate={(next) => onUpdate(next)}
          onGoalCompleted={(goal, allGoalsBonus) => {
            playNonce.current += 1;
            playPet(requestGoalClip(goal.key, goal.surprise, playNonce.current, allGoalsBonus));
          }}
          onGoalsBonus={(line) => {
            setBurstCongrats(line);
            setGoalsBurst(true);
            const msg =
              line?.trim() ||
              "Dia completo no Jardim! Volte ao chat para celebrar com seu avatar.";
            void queueMonsterChatNotice(msg);
          }}
        />

        <MoodWeeklyQuizCard
          colors={colors}
          quiz={care.weekly_quiz}
          onUpdate={(next) => onUpdate(next)}
        />

        <MoodSocialInviteCard colors={colors} invite={care.social_invite} />

        <MoodSeedShop colors={colors} care={care} onUpdate={(next) => onUpdate(next)} />

        <RankingLadder colors={colors} care={care} />

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
  wrap: { borderRadius: 16, borderWidth: 2, padding: 14, marginBottom: 12, overflow: "hidden" },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
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
  ladderRow: { flexDirection: "row", justifyContent: "space-between", marginTop: 10, paddingHorizontal: 2 },
  ladderStep: { alignItems: "center", flex: 1 },
  ladderDot: { width: 8, height: 8, borderRadius: 4, marginBottom: 4 },
  ladderEmoji: { fontSize: 16 },
  ladderLabel: { fontSize: 9, fontWeight: "700", marginTop: 2 },
  challengeLine: { fontSize: 12, fontWeight: "700", marginTop: 10, textAlign: "center" },
  moodFirst: {
    marginBottom: 12,
    padding: 12,
    borderRadius: 14,
    borderWidth: 1.5,
    backgroundColor: "rgba(255,255,255,0.04)",
  },
  stepBadge: { fontSize: 10, fontWeight: "900", letterSpacing: 0.5, marginBottom: 6 },
  missionsLocked: { fontSize: 11, fontWeight: "700", marginBottom: 6, marginTop: 4 },
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
  moodEmoji: { fontSize: 24 },
  moodLabel: { fontSize: 9, fontWeight: "700", marginTop: 2 },
  done: { marginTop: 12, fontSize: 14, fontWeight: "700", textAlign: "center" },
  hook: { marginTop: 6, fontSize: 12, textAlign: "center", lineHeight: 17 },
  shareBtn: { marginTop: 12, borderRadius: 12, paddingVertical: 12, alignItems: "center" },
  shareText: { color: "#fff", fontWeight: "800", fontSize: 14 },
  risk: { marginTop: 10, fontSize: 13, fontWeight: "600", textAlign: "center" },
});
