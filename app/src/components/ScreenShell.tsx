import type { AccessInfo } from "@/api/types";
import { FreeFooterBanner } from "@/components/FreeFooterBanner";
import { useDrawer } from "@/context/DrawerContext";
import { useColors } from "@/theme/ThemeContext";
import { shouldShowChatAds } from "@/utils/shouldShowChatAds";
import React from "react";
import { Pressable, StyleSheet, Text, View, type ViewProps } from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";

type Props = ViewProps & {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  /** Sem barra superior (ex.: chat imersivo). */
  immersive?: boolean;
  /**
   * FREE: banner AdMob / ShapeScan no rodapé (listas / home / perfil).
   * Não usar em paywall, onboarding, chat (já tem o seu) nem durante respiração.
   */
  adsAccess?: AccessInfo | null;
};

export function MenuButton() {
  const { openDrawer } = useDrawer();
  const colors = useColors();

  return (
    <Pressable
      onPress={openDrawer}
      hitSlop={12}
      style={({ pressed }) => [
        styles.menuHit,
        { backgroundColor: colors.bgCard, borderColor: colors.border },
        pressed && { opacity: 0.7 },
      ]}
      accessibilityRole="button"
      accessibilityLabel="Abrir menu"
    >
      <View style={[styles.bar, { backgroundColor: colors.text }]} />
      <View style={[styles.bar, styles.barMid, { backgroundColor: colors.text }]} />
      <View style={[styles.bar, { backgroundColor: colors.text }]} />
    </Pressable>
  );
}

export function ScreenShell({
  title,
  subtitle,
  children,
  immersive,
  adsAccess,
  style,
  ...rest
}: Props) {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const showFooterAds =
    !immersive && adsAccess !== undefined && shouldShowChatAds(adsAccess);

  return (
    <SafeAreaView
      style={[styles.fill, { backgroundColor: colors.bg }]}
      edges={immersive ? ["top", "bottom"] : ["top"]}
    >
      {!immersive ? (
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <MenuButton />
          <View style={styles.headerText}>
            {title ? (
              <Text style={[styles.title, { color: colors.text }]}>{title}</Text>
            ) : null}
            {subtitle ? (
              <Text style={[styles.sub, { color: colors.textMuted }]}>{subtitle}</Text>
            ) : null}
          </View>
        </View>
      ) : null}

      <View style={[styles.body, style]} {...rest}>
        {children}
      </View>

      {showFooterAds ? (
        <View
          style={[
            styles.adFooter,
            {
              paddingBottom: Math.max(insets.bottom, 4),
              borderTopColor: colors.border,
            },
          ]}
        >
          <FreeFooterBanner access={adsAccess} />
        </View>
      ) : null}

      {immersive ? (
        <View
          style={[styles.floatingMenu, { top: insets.top + 8 }]}
          pointerEvents="box-none"
        >
          <MenuButton />
        </View>
      ) : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    gap: 8,
    zIndex: 10,
  },
  headerText: { flex: 1 },
  title: { fontSize: 22, fontWeight: "700", letterSpacing: -0.3 },
  sub: { fontSize: 13, marginTop: 2 },
  body: { flex: 1 },
  adFooter: {
    width: "100%",
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  floatingMenu: {
    position: "absolute",
    left: 16,
    zIndex: 100,
    elevation: 100,
  },
  menuHit: {
    width: 48,
    height: 48,
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 12,
    paddingVertical: 14,
    justifyContent: "space-between",
  },
  bar: { height: 2.5, borderRadius: 2, width: "100%" },
  barMid: { width: "72%", alignSelf: "flex-start" },
});
