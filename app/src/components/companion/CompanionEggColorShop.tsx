import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import * as Haptics from "expo-haptics";
import { purchaseCompanionEggColor } from "@/api/client";
import type { WellnessJourney } from "@/api/types";
import type { AppColors } from "@/theme/colors";
import { EGG_COLOR_PALETTES } from "@/utils/companionEggPalettes";

type Props = {
  colors: AppColors;
  journey: WellnessJourney;
  onUpdate: (j: WellnessJourney) => void;
};

export function CompanionEggColorShop({ colors, journey, onUpdate }: Props) {
  const items = journey.egg_color_shop ?? [];
  const [busyId, setBusyId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  if (!items.length) return null;

  const stars = journey.stars ?? 0;
  const ownedCount = items.filter((i) => i.owned).length;

  const onSelect = async (colorId: string, label: string, price: number, owned: boolean) => {
    if (busyId) return;
    setBusyId(colorId);
    try {
      const next = await purchaseCompanionEggColor(colorId);
      if (!next) {
        Alert.alert("Loja do bolso", "Não foi possível trocar a cor. Tente de novo.");
        return;
      }
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(
        () => undefined
      );
      onUpdate(next);
      if (!owned && price > 0) {
        Alert.alert("Loja do bolso", `Cor ${label} desbloqueada no ovo! 🥚`);
      }
    } finally {
      setBusyId(null);
    }
  };

  return (
    <View style={styles.wrap}>
      <Pressable
        onPress={() => setOpen((v) => !v)}
        style={[styles.headBtn, { borderColor: colors.primary, backgroundColor: colors.primaryTint }]}
      >
        <Text style={[styles.headTitle, { color: colors.text }]}>🎨 Cores do ovo</Text>
        <Text style={[styles.headMeta, { color: colors.textMuted }]}>
          ⭐ {stars} · {ownedCount}/{items.length} cores
        </Text>
      </Pressable>

      {open ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.row}>
          {items.map((item) => {
            const palette = EGG_COLOR_PALETTES[item.id];
            const disabled =
              busyId === item.id || (!item.owned && !item.can_afford && item.price > 0);
            return (
              <Pressable
                key={item.id}
                onPress={() => void onSelect(item.id, item.label, item.price, item.owned)}
                disabled={disabled}
                style={[
                  styles.item,
                  {
                    borderColor: item.active
                      ? colors.primary
                      : item.owned
                        ? colors.success
                        : item.can_afford
                          ? colors.border
                          : colors.border,
                    backgroundColor: item.active ? colors.primaryTint : colors.bg,
                    opacity: disabled && !item.active ? 0.55 : 1,
                  },
                ]}
              >
                <LinearGradient
                  colors={palette?.body ?? ["#1E0A3C", "#5B21B6", "#22D3EE"]}
                  style={styles.swatch}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                />
                <Text style={styles.itemEmoji}>{item.active ? "✓" : item.emoji}</Text>
                <Text style={[styles.itemLabel, { color: colors.text }]} numberOfLines={1}>
                  {item.label}
                </Text>
                <Text style={[styles.itemPrice, { color: colors.textMuted }]}>
                  {item.active ? "Ativa" : item.owned ? "Usar" : item.price === 0 ? "Grátis" : `⭐ ${item.price}`}
                </Text>
                {busyId === item.id ? (
                  <ActivityIndicator color={colors.primary} size="small" style={{ marginTop: 4 }} />
                ) : null}
              </Pressable>
            );
          })}
        </ScrollView>
      ) : null}

      {open ? (
        <Text style={[styles.hint, { color: colors.textMuted }]}>
          +1 ⭐ por missão · +3 ⭐ ao completar 5/5 hoje
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 10 },
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
  row: { marginTop: 8 },
  item: {
    width: 96,
    marginRight: 8,
    borderWidth: 1.5,
    borderRadius: 12,
    padding: 10,
    alignItems: "center",
  },
  swatch: {
    width: 36,
    height: 36,
    borderRadius: 18,
    marginBottom: 4,
  },
  itemEmoji: { fontSize: 18 },
  itemLabel: { fontSize: 10, fontWeight: "700", marginTop: 2 },
  itemPrice: { fontSize: 10, fontWeight: "600", marginTop: 2 },
  hint: { fontSize: 10, fontWeight: "600", marginTop: 8, lineHeight: 14 },
});
