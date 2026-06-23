import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useAppUpdate } from "@/context/AppUpdateContext";
import { useColors } from "@/theme/ThemeContext";
import { openAppUpdate } from "@/utils/openAppUpdate";

/** Cartão fixo na Conta — funciona mesmo se o banner do topo for fechado. */
export function AccountUpdateCard() {
  const colors = useColors();
  const { needsUpdate, latestVersion, currentVersion, playStoreUrl, iosUpdateUrl } =
    useAppUpdate();

  if (!needsUpdate) return null;

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.primaryTint, borderColor: colors.primary },
      ]}
    >
      <Text style={[styles.title, { color: colors.text }]}>
        Atualização disponível · v{latestVersion}
      </Text>
      <Text style={[styles.body, { color: colors.textMuted }]}>
        Você está na v{currentVersion}. Toque abaixo para abrir a loja e instalar a versão
        nova (Desabafo, compras e correções).
      </Text>
      <Pressable
        onPress={() => void openAppUpdate({ playStoreUrl, iosUpdateUrl })}
        style={({ pressed }) => [
          styles.btn,
          { backgroundColor: colors.primary, opacity: pressed ? 0.88 : 1 },
        ]}
        accessibilityRole="button"
        accessibilityLabel="Atualizar aplicativo"
      >
        <Text style={styles.btnText}>Atualizar agora</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    gap: 8,
  },
  title: { fontSize: 16, fontWeight: "800" },
  body: { fontSize: 14, lineHeight: 20 },
  btn: {
    marginTop: 4,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "800" },
});
