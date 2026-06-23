import React, { useCallback } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useAppUpdate } from "@/context/AppUpdateContext";
import { useColors } from "@/theme/ThemeContext";
import { openAppUpdate } from "@/utils/openAppUpdate";

export function AppUpdateBanner() {
  const colors = useColors();
  const {
    showBanner,
    latestVersion,
    currentVersion,
    playStoreUrl,
    iosUpdateUrl,
    message,
    dismissBanner,
  } = useAppUpdate();

  const onUpdate = useCallback(() => {
    void openAppUpdate({ playStoreUrl, iosUpdateUrl });
  }, [iosUpdateUrl, playStoreUrl]);

  if (!showBanner) return null;

  const summary =
    message?.trim() ||
    (latestVersion && currentVersion
      ? `Você está na v${currentVersion}. A v${latestVersion} já está disponível.`
      : "Há uma versão nova. Toque abaixo para atualizar.");

  return (
    <View
      style={[
        styles.shell,
        { backgroundColor: colors.primary, borderBottomColor: colors.primaryLight },
      ]}
    >
      <View style={styles.headerRow}>
        <Text style={styles.title}>
          Nova versão{latestVersion ? ` · v${latestVersion}` : ""}
        </Text>
        <Pressable
          onPress={() => void dismissBanner()}
          hitSlop={16}
          style={styles.closeBtn}
          accessibilityRole="button"
          accessibilityLabel="Fechar aviso de atualização"
        >
          <Text style={styles.closeText}>✕</Text>
        </Pressable>
      </View>

      <Text style={styles.body}>{summary}</Text>

      <Pressable
        onPress={onUpdate}
        style={({ pressed }) => [styles.btn, pressed && { opacity: 0.88 }]}
        accessibilityRole="button"
        accessibilityLabel="Atualizar agora"
      >
        <Text style={styles.btnText}>Atualizar agora</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  shell: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 14,
    borderBottomWidth: 1,
    gap: 10,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  title: {
    flex: 1,
    color: "#fff",
    fontSize: 16,
    fontWeight: "800",
    lineHeight: 22,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
  },
  closeText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },
  body: {
    color: "#fff",
    fontSize: 14,
    lineHeight: 20,
    fontWeight: "500",
  },
  btn: {
    backgroundColor: "#fff",
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 16,
    alignItems: "center",
  },
  btnText: {
    color: "#1a2a5c",
    fontSize: 16,
    fontWeight: "800",
  },
});
