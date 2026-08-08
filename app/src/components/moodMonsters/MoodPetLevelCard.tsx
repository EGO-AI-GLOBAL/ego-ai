import React, { useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import * as Haptics from "expo-haptics";
import { purchaseDailyCareConsumable } from "@/api/client";
import type { DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import type { MoodReward } from "./MoodRewardBurst";

type Props = {
  colors: AppColors;
  care: DailyCareInfo;
  onUpdate: (care: DailyCareInfo) => void;
  /** Compra ok → reação do pet (clip distinto). */
  onFeed?: () => void;
  /** Festa na tela em vez de Alert (subir de nível, caixa surpresa). */
  onReward?: (reward: MoodReward) => void;
  /** Toque no nome → baptizar o monstrinho. */
  onPressName?: () => void;
};

/** Nível do monstrinho (XP sem fim) + petiscos/caixa surpresa — gasto infinito de sementes. */
export function MoodPetLevelCard({
  colors,
  care,
  onUpdate,
  onFeed,
  onReward,
  onPressName,
}: Props) {
  const [busyId, setBusyId] = useState<string | null>(null);
  const pet = care.pet;
  const consumables = care.consumables ?? [];

  if (!pet) return null;

  const emitReward = (reward: MoodReward) => {
    if (onReward) {
      onReward(reward);
      return;
    }
    Alert.alert(reward.title, reward.sub ?? "");
  };

  const onBuy = async (itemId: string, label: string, kind: string) => {
    if (busyId) return;
    setBusyId(itemId);
    try {
      const res = await purchaseDailyCareConsumable(itemId);
      if (!res?.daily_care) {
        Alert.alert("Cuidar do monstrinho", "Não foi possível agora. Tente de novo.");
        return;
      }
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(
        () => undefined
      );
      onFeed?.();
      onUpdate(res.daily_care);

      const petName = res.daily_care.pet?.name?.trim();
      const who = petName || "O monstrinho";
      const box = res.daily_care.last_box_reward;
      const levelUp = res.daily_care.pet_level_up;

      if (kind === "box" && box?.label) {
        emitReward({
          kind: "bonus",
          emoji: box.emoji || "🎁",
          title: box.kind === "seeds" ? `+${box.amount} amêndoas!` : `${box.label} — novo!`,
          sub: box.kind === "seeds" ? box.label : "já está no seu jardim",
        });
      } else {
        emitReward({
          kind: "bonus",
          emoji: "💜",
          title: `${who} adorou!`,
          sub: label,
        });
      }

      if (levelUp) {
        // Subir de nível vem depois do mimo — duas festas, não uma só.
        setTimeout(() => {
          emitReward({
            kind: "level",
            emoji: levelUp.stage_emoji || "✨",
            title: `${who} subiu para o nível ${levelUp.to}!`,
            sub: levelUp.stage_label ? `Agora é ${levelUp.stage_label}` : undefined,
          });
        }, 1900);
      }
    } finally {
      setBusyId(null);
    }
  };

  const pct = Math.max(0, Math.min(100, pet.progress_pct ?? 0));
  const seeds = care.seeds ?? 0;
  const shields = care.shields ?? 0;

  return (
    <View style={[styles.wrap, { borderColor: colors.glassBorder, backgroundColor: colors.bgCard }]}>
      <View style={styles.head}>
        <Text style={styles.stageEmoji}>{pet.stage_emoji}</Text>
        <Pressable style={styles.headBody} onPress={onPressName} disabled={!onPressName}>
          <Text style={[styles.title, { color: colors.text }]}>
            {pet.name ? `${pet.name} · ` : ""}Nível {pet.level} · {pet.stage_label}
          </Text>
          <Text style={[styles.meta, { color: colors.textMuted }]}>
            {pet.xp_into_level}/{pet.xp_for_next} XP para o próximo nível
          </Text>
          {onPressName && !pet.name ? (
            <Text style={[styles.nameCta, { color: colors.primary }]}>
              Toque para dar um nome a ele ✨
            </Text>
          ) : null}
        </Pressable>
        {shields > 0 ? (
          <Text style={[styles.shield, { color: colors.primary }]}>🛡️ {shields}</Text>
        ) : null}
      </View>

      <View style={[styles.barBg, { backgroundColor: colors.border }]}>
        <View style={[styles.barFill, { width: `${pct}%`, backgroundColor: colors.primary }]} />
      </View>

      {care.streak_message ? (
        <Text style={[styles.streakMsg, { color: colors.textMuted }]}>{care.streak_message}</Text>
      ) : null}

      {consumables.length ? (
        <>
          <Text style={[styles.shopTitle, { color: colors.textMuted }]}>
            Cuidar do monstrinho · 🌰 {seeds}
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.row}>
            {consumables.map((item) => {
              const disabled = !item.can_afford || busyId === item.id;
              return (
                <Pressable
                  key={item.id}
                  onPress={() => void onBuy(item.id, item.label, item.kind)}
                  disabled={disabled}
                  style={[
                    styles.item,
                    {
                      borderColor: item.can_afford ? colors.primary : colors.border,
                      backgroundColor: colors.bg,
                      opacity: disabled ? 0.55 : 1,
                    },
                  ]}
                >
                  <Text style={styles.itemEmoji}>{item.emoji}</Text>
                  <Text style={[styles.itemLabel, { color: colors.text }]} numberOfLines={1}>
                    {item.label}
                  </Text>
                  <Text style={[styles.itemPrice, { color: colors.textMuted }]}>🌰 {item.price}</Text>
                  {busyId === item.id ? (
                    <ActivityIndicator color={colors.primary} size="small" style={{ marginTop: 4 }} />
                  ) : null}
                </Pressable>
              );
            })}
          </ScrollView>
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 12,
    marginBottom: 12,
  },
  head: { flexDirection: "row", alignItems: "center", gap: 10 },
  stageEmoji: { fontSize: 30 },
  headBody: { flex: 1 },
  title: { fontSize: 13, fontWeight: "800" },
  meta: { fontSize: 11, fontWeight: "600", marginTop: 2 },
  nameCta: { fontSize: 11, fontWeight: "800", marginTop: 4 },
  shield: { fontSize: 12, fontWeight: "800" },
  barBg: { height: 8, borderRadius: 6, marginTop: 10, overflow: "hidden" },
  barFill: { height: 8, borderRadius: 6 },
  streakMsg: { fontSize: 11, fontWeight: "600", marginTop: 8, lineHeight: 16 },
  shopTitle: { fontSize: 10, fontWeight: "800", marginTop: 12 },
  row: { marginTop: 8 },
  item: {
    width: 92,
    marginRight: 8,
    borderWidth: 1.5,
    borderRadius: 12,
    padding: 10,
    alignItems: "center",
  },
  itemEmoji: { fontSize: 26 },
  itemLabel: { fontSize: 10, fontWeight: "700", marginTop: 4 },
  itemPrice: { fontSize: 10, fontWeight: "600", marginTop: 2 },
});
