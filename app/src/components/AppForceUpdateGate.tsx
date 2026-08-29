import React, { useCallback } from "react";
import { Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAppUpdate } from "@/context/AppUpdateContext";
import { useColors } from "@/theme/ThemeContext";
import { openAppUpdate } from "@/utils/openAppUpdate";

/**
 * Bloqueio total até atualizar (force_update / min_version da API).
 * Apple/Google não permitem install silencioso — isto é o máximo legal.
 */
export function AppForceUpdateGate() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const {
    forceUpdate,
    forceMessage,
    latestVersion,
    currentVersion,
    playStoreUrl,
    iosUpdateUrl,
  } = useAppUpdate();

  const onUpdate = useCallback(() => {
    void openAppUpdate({ playStoreUrl, iosUpdateUrl });
  }, [iosUpdateUrl, playStoreUrl]);

  if (!forceUpdate) return null;

  const body =
    forceMessage?.trim() ||
    `A v${latestVersion || "nova"} é obrigatória. Atualize para continuar com o check-in de 1 minuto.`;

  return (
    <Modal visible animationType="fade" presentationStyle="fullScreen">
      <View
        style={[
          styles.fill,
          {
            backgroundColor: colors.bg,
            paddingTop: insets.top + 24,
            paddingBottom: insets.bottom + 24,
          },
        ]}
      >
        <Text style={[styles.emoji]}>🌱</Text>
        <Text style={[styles.title, { color: colors.text }]}>Atualização obrigatória</Text>
        <Text style={[styles.body, { color: colors.textMuted }]}>{body}</Text>
        {currentVersion || latestVersion ? (
          <Text style={[styles.meta, { color: colors.textMuted }]}>
            {currentVersion ? `Sua versão: ${currentVersion}` : ""}
            {currentVersion && latestVersion ? " → " : ""}
            {latestVersion ? `Loja: ${latestVersion}` : ""}
          </Text>
        ) : null}
        <Pressable
          onPress={onUpdate}
          style={({ pressed }) => [
            styles.btn,
            { backgroundColor: colors.primary, opacity: pressed ? 0.9 : 1 },
          ]}
          accessibilityRole="button"
          accessibilityLabel="Atualizar agora"
        >
          <Text style={styles.btnText}>Atualizar agora</Text>
        </Pressable>
        <Text style={[styles.hint, { color: colors.textMuted }]}>
          Não dá para continuar nesta versão. Depois de atualizar, o monstrinho e o
          check-in de 1 minuto ficam disponíveis.
        </Text>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  fill: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: "center",
    alignItems: "center",
  },
  emoji: { fontSize: 48, marginBottom: 16 },
  title: {
    fontSize: 22,
    fontWeight: "800",
    textAlign: "center",
    letterSpacing: -0.3,
  },
  body: {
    fontSize: 15,
    lineHeight: 22,
    textAlign: "center",
    marginTop: 12,
    maxWidth: 340,
  },
  meta: { fontSize: 12, marginTop: 10, fontWeight: "600" },
  btn: {
    marginTop: 28,
    alignSelf: "stretch",
    maxWidth: 340,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontSize: 17, fontWeight: "800" },
  hint: {
    fontSize: 12,
    lineHeight: 18,
    textAlign: "center",
    marginTop: 20,
    maxWidth: 320,
  },
});
