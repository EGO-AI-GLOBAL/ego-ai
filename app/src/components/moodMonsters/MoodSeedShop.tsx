import React, { useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import * as Haptics from "expo-haptics";
import { purchaseDailyCareShopItem } from "@/api/client";
import type { DailyCareInfo } from "@/api/types";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  care: DailyCareInfo;
  onUpdate: (care: DailyCareInfo) => void;
};

export function MoodSeedShop({ colors, care, onUpdate }: Props) {
  const items = care.shop_items ?? [];
  const [busyId, setBusyId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  if (!items.length) return null;

  const onBuy = async (itemId: string, label: string) => {
    if (busyId) return;
    setBusyId(itemId);
    try {
      const res = await purchaseDailyCareShopItem(itemId);
      if (!res?.daily_care) {
        Alert.alert("Loja do jardim", "Não foi possível comprar. Tente de novo.");
        return;
      }
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => undefined);
      onUpdate(res.daily_care);
      Alert.alert("Loja do jardim", `${label} plantado no jardim! 🌱`);
    } finally {
      setBusyId(null);
    }
  };

  const seeds = care.seeds ?? 0;
  const ownedCount = items.filter((i) => i.owned).length;
  const buyableCount = items.filter((i) => !i.owned).length;
  const weekLabel = care.shop_week_label?.trim();
  const resetDate = care.shop_rotation_reset?.trim();
  const baseComplete = care.shop_base_complete;

  return (
    <View style={styles.wrap}>
      <Pressable
        onPress={() => setOpen((v) => !v)}
        style={[styles.headBtn, { borderColor: colors.primary, backgroundColor: colors.primaryTint }]}
      >
        <Text style={[styles.headTitle, { color: colors.text }]}>🛒 Loja do jardim</Text>
        <Text style={[styles.headMeta, { color: colors.textMuted }]}>
          🌰 {seeds} · {ownedCount} decor · {buyableCount} à venda
        </Text>
      </Pressable>

      {open && weekLabel ? (
        <Text style={[styles.rotationHint, { color: colors.textMuted }]}>
          {baseComplete ? "Catálogo base completo — " : ""}
          Novidades da {weekLabel}
          {resetDate ? ` · renova ${resetDate.slice(5).replace("-", "/")}` : ""}
        </Text>
      ) : null}

      {open ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.row}>
          {items.map((item) => {
            const disabled = item.owned || !item.can_afford || busyId === item.id;
            return (
              <Pressable
                key={item.id}
                onPress={() => void onBuy(item.id, item.label)}
                disabled={disabled}
                style={[
                  styles.item,
                  {
                    borderColor: item.owned ? colors.success : item.can_afford ? colors.primary : colors.border,
                    backgroundColor: item.owned ? "rgba(34,197,94,0.08)" : colors.bg,
                    opacity: disabled && !item.owned ? 0.55 : 1,
                  },
                ]}
              >
                <Text style={styles.itemEmoji}>{item.owned ? "✓" : item.emoji}</Text>
                {item.rotating && !item.owned ? (
                  <Text style={[styles.rotBadge, { color: colors.primary }]}>Semana</Text>
                ) : null}
                <Text style={[styles.itemLabel, { color: colors.text }]} numberOfLines={1}>
                  {item.label}
                </Text>
                <Text style={[styles.itemPrice, { color: colors.textMuted }]}>
                  {item.owned ? "Seu" : `🌰 ${item.price}`}
                </Text>
                {busyId === item.id ? (
                  <ActivityIndicator color={colors.primary} size="small" style={{ marginTop: 4 }} />
                ) : null}
              </Pressable>
            );
          })}
        </ScrollView>
      ) : null}

      {(care.seed_history ?? []).length > 0 && open ? (
        <View style={[styles.hist, { borderColor: colors.border }]}>
          <Text style={[styles.histTitle, { color: colors.textMuted }]}>Últimas sementes</Text>
          {(care.seed_history ?? []).slice(0, 4).map((h, i) => (
            <Text key={`h-${i}-${h.date}`} style={[styles.histLine, { color: colors.text }]}>
              {h.action === "spend" ? "−" : "+"}
              {h.amount} · {h.label}
            </Text>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 12 },
  headBtn: {
    borderWidth: 1.5,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headTitle: { fontSize: 13, fontWeight: "800" },
  headMeta: { fontSize: 11, fontWeight: "600" },
  rotationHint: { fontSize: 10, fontWeight: "600", marginTop: 6, lineHeight: 14 },
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
  rotBadge: { fontSize: 8, fontWeight: "800", marginTop: 2 },
  itemLabel: { fontSize: 10, fontWeight: "700", marginTop: 4 },
  itemPrice: { fontSize: 10, fontWeight: "600", marginTop: 2 },
  hist: {
    marginTop: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingTop: 8,
  },
  histTitle: { fontSize: 10, fontWeight: "800", marginBottom: 4 },
  histLine: { fontSize: 10, fontWeight: "600", lineHeight: 14 },
});
