import React from "react";
import {
  Alert,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAppUpdate } from "@/context/AppUpdateContext";
import { useColors } from "@/theme/ThemeContext";

const PLAY_TESTING = "https://play.google.com/apps/testing/com.egoai.app";
const PLAY_STORE = "https://play.google.com/store/apps/details?id=com.egoai.app";
const PLAY_MARKET = "market://details?id=com.egoai.app";
const TESTFLIGHT_JOIN = "https://testflight.apple.com/join/eNDKdFWF";

async function openFirstUrl(urls: string[]): Promise<boolean> {
  for (const url of urls) {
    if (!url?.trim()) continue;
    try {
      if (url.startsWith("http://") || url.startsWith("https://")) {
        await Linking.openURL(url);
        return true;
      }
      const can = await Linking.canOpenURL(url);
      if (!can) continue;
      await Linking.openURL(url);
      return true;
    } catch {
      /* tenta próximo */
    }
  }
  return false;
}

function iosUpdateUrls(iosUpdateUrl: string): string[] {
  const join = TESTFLIGHT_JOIN;
  const fromApi = iosUpdateUrl?.trim();
  const list: string[] = [];
  if (fromApi?.startsWith("http")) list.push(fromApi);
  if (!list.includes(join)) list.push(join);
  return list;
}

export function AppUpdateBanner() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const {
    showBanner,
    latestVersion,
    currentVersion,
    playStoreUrl,
    iosUpdateUrl,
    message,
    dismissBanner,
  } = useAppUpdate();

  if (!showBanner) return null;

  const onUpdate = async () => {
    const urls =
      Platform.OS === "ios"
        ? iosUpdateUrls(iosUpdateUrl)
        : [playStoreUrl, PLAY_TESTING, PLAY_STORE, PLAY_MARKET].filter(Boolean);

    const opened = await openFirstUrl(urls);
    if (!opened) {
      const fallback = Platform.OS === "ios" ? TESTFLIGHT_JOIN : PLAY_TESTING;
      Alert.alert(
        "Atualizar",
        Platform.OS === "ios"
          ? `Abra no Safari:\n${fallback}\n\nDepois toque em Atualizar no TestFlight.`
          : `Abra no navegador:\n${PLAY_TESTING}`,
        [
          { text: "Cancelar", style: "cancel" },
          {
            text: "Abrir link",
            onPress: () => void Linking.openURL(fallback).catch(() => undefined),
          },
        ]
      );
    }
  };

  const summary =
    message?.trim() ||
    (latestVersion && currentVersion
      ? `Você está na v${currentVersion}. A v${latestVersion} já está na loja.`
      : "Há uma versão nova na loja. Toque no botão abaixo para instalar.");

  return (
    <View
      style={[
        styles.shell,
        {
          backgroundColor: colors.primary,
          borderBottomColor: colors.primaryLight,
          paddingTop: Math.max(insets.top, 10),
        },
      ]}
    >
      <View style={styles.headerRow}>
        <Text style={styles.title}>
          Nova versão{latestVersion ? ` · v${latestVersion}` : ""}
        </Text>
        <Pressable
          onPress={() => void dismissBanner()}
          hitSlop={12}
          style={styles.closeBtn}
          accessibilityRole="button"
          accessibilityLabel="Fechar aviso de atualização"
        >
          <Text style={styles.closeText}>✕</Text>
        </Pressable>
      </View>

      <Text style={styles.body}>{summary}</Text>

      <Pressable
        onPress={() => void onUpdate()}
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
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
  },
  closeText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
    lineHeight: 18,
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
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: "center",
  },
  btnText: {
    color: "#1a2a5c",
    fontSize: 15,
    fontWeight: "800",
  },
});
