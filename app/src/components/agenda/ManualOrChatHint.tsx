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
        Manual ou com avatar — as duas formas
      </Text>
      <Text style={[styles.body, { color: colors.textMuted }]}>
        Prefere sem chat: use os botões + nesta tela (marcar, remover, convidar). Quem quiser
        pode falar ou escrever no avatar — o resultado é o mesmo.
      </Text>
      <Pressable onPress={onOpenChat} hitSlop={8}>
        <Text style={[styles.link, { color: colors.primary }]}>
          Opcional: abrir o chat →
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
