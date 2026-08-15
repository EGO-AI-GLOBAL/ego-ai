import React, { useEffect } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { trackRewardedOptIn } from "@/analytics/egoAnalytics";
import { useRewardedOptIn } from "@/ads/useRewardedOptIn";
import { queueMonsterChatNotice } from "@/utils/monsterChatNotice";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  /** false = Premium / sem ads. */
  enabled: boolean;
  /** Já fez check-in hoje — mostra opt-in de dica. */
  visible: boolean;
};

const TIPS = [
  "Respira 4 segundos · segura 4 · solta 4. Uma vez já conta.",
  "Bebe um gole de água agora — corpo calmo ajuda a mente.",
  "Escreve numa linha: o que pesa menos se eu fizer só isto hoje?",
  "Pousa o telemóvel 60s e olha pela janela. Depois voltas.",
  "Manda um «oi, tô aqui» a alguém de confiança — sem explicar tudo.",
];

/**
 * Rewarded opt-in — nunca auto-play.
 * Benefício: dica do dia no chat (após ver o anúncio).
 */
export function RewardedDailyTipCard({ colors, enabled, visible }: Props) {
  const { ready, showOptIn } = useRewardedOptIn({ enabled });

  useEffect(() => {
    if (visible && enabled) trackRewardedOptIn("offer_shown");
  }, [visible, enabled]);

  if (!visible || !enabled) return null;

  const onPress = () => {
    if (!ready) {
      Alert.alert(
        "Anúncio",
        "Ainda a carregar. Tenta de novo em instantes — ou segue sem anúncio."
      );
      return;
    }
    Alert.alert(
      "Dica do dia",
      "Queres ver um anúncio curto e receber uma dica extra no chat?",
      [
        { text: "Agora não", style: "cancel" },
        {
          text: "Ver anúncio",
          onPress: () => {
            const ok = showOptIn({
              onEarned: () => {
                const tip = TIPS[Math.floor(Math.random() * TIPS.length)];
                void queueMonsterChatNotice(`💡 Dica do dia: ${tip}`);
                Alert.alert("Dica desbloqueada", "Olha a mensagem no chat com a Luna/Leo.");
              },
              onFail: () => {
                Alert.alert(
                  "Sem anúncio",
                  "Não houve fill agora. A dica fica para a próxima — sem problema."
                );
              },
            });
            if (!ok) {
              Alert.alert(
                "Sem anúncio",
                "Não foi possível abrir o anúncio agora. Tenta mais tarde."
              );
            }
          },
        },
      ]
    );
  };

  return (
    <View
      style={[
        styles.wrap,
        { borderColor: colors.border, backgroundColor: colors.bgCard },
      ]}
    >
      <Text style={[styles.title, { color: colors.text }]}>💡 Dica extra do dia</Text>
      <Text style={[styles.sub, { color: colors.textMuted }]}>
        Opcional: vê um anúncio curto e recebe uma dica no chat. Nunca abre sozinho.
      </Text>
      <Pressable
        onPress={onPress}
        style={[styles.btn, { backgroundColor: colors.primary }]}
        accessibilityRole="button"
        accessibilityLabel="Ver anúncio e ganhar dica"
      >
        <Text style={styles.btnText}>{ready ? "Ver anúncio e ganhar dica" : "A carregar…"}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    marginTop: 12,
    gap: 8,
  },
  title: { fontSize: 15, fontWeight: "700" },
  sub: { fontSize: 13, lineHeight: 18 },
  btn: {
    marginTop: 4,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
});
