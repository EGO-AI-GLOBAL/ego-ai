import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { AppColors } from "@/theme/colors";

type Props = {
  colors: AppColors;
  onOpenChat: () => void;
};

export function ManualOrChatHint({ colors, onOpenChat }: Props) {
  return (
    <View
      style={[
        styles.wrap,
        { borderColor: colors.border, backgroundColor: colors.bgCard },
      ]}
    >
      <Text style={[styles.title, { color: colors.text }]}>
        Marque aqui — 3 toques e pronto
      </Text>
      <Text style={[styles.body, { color: colors.textMuted }]}>
        1) + Novo compromisso · 2) nome e data/hora (use Hoje ou Amanhã) · 3) Marcar compromisso.
        {"\n"}
        Dúvida? Pergunte ao avatar no chat — ele explica qualquer função do app.
      </Text>
      <Pressable onPress={onOpenChat} hitSlop={8}>
        <Text style={[styles.link, { color: colors.primary }]}>
          Tirar dúvida no chat →
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
  },
  title: { fontSize: 14, fontWeight: "800", marginBottom: 6 },
  body: { fontSize: 13, lineHeight: 18 },
  link: { fontSize: 13, fontWeight: "700", marginTop: 10 },
});
