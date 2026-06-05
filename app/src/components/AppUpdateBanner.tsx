import React from "react";
import { Linking, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { useAppUpdate } from "@/context/AppUpdateContext";
import { useColors } from "@/theme/ThemeContext";

const PLAY_FALLBACK = "market://details?id=com.egoai.app";

export function AppUpdateBanner() {
  const colors = useColors();
  const { showBanner, message, latestVersion, playStoreUrl } = useAppUpdate();

  if (!showBanner) return null;

  const onOpenPlay = async () => {
    const candidates = [
      playStoreUrl,
      PLAY_FALLBACK,
      "https://play.google.com/store/apps/details?id=com.egoai.app",
    ].filter(Boolean);
    for (const url of candidates) {
      try {
        const can = await Linking.canOpenURL(url);
        if (can) {
          await Linking.openURL(url);
          return;
        }
      } catch {
        /* tenta próximo */
      }
    }
    if (Platform.OS === "android") {
      await Linking.openURL(PLAY_FALLBACK);
    }
  };

  return (
    <View
      style={[
        styles.wrap,
        { backgroundColor: colors.primary, borderBottomColor: colors.primaryLight },
      ]}
      accessibilityRole="alert"
    >
      <View style={styles.textCol}>
        <Text style={styles.title}>
          Atualização disponível{latestVersion ? ` · v${latestVersion}` : ""}
        </Text>
        <Text style={styles.body}>{message}</Text>
      </View>
      <Pressable
        onPress={() => void onOpenPlay()}
        style={({ pressed }) => [styles.btn, pressed && { opacity: 0.88 }]}
        accessibilityRole="button"
        accessibilityLabel="Ir para a Play Store"
      >
        <Text style={styles.btnText}>Ir para a Play</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  textCol: { flex: 1 },
  title: { color: "#fff", fontSize: 14, fontWeight: "800" },
  body: { color: "rgba(255,255,255,0.92)", fontSize: 12, lineHeight: 16, marginTop: 2 },
  btn: {
    backgroundColor: "#fff",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  btnText: { color: "#1a2a5c", fontSize: 13, fontWeight: "800" },
});
