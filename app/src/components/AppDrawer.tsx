import { router, type Href } from "expo-router";
import React, { useEffect, useRef } from "react";
import {
  Animated,
  Dimensions,
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import {
  avatarImageSource,
  isMaleAvatar,
} from "@/constants/personas";
import { findAvatarInCatalog } from "@/constants/avatarCatalog";
import { useDashboard } from "@/hooks/useDashboard";
import { useAuth } from "@/context/AuthContext";
import { useDrawer } from "@/context/DrawerContext";
import { EgoLogo } from "@/components/EgoLogo";
import { useColors } from "@/theme/ThemeContext";

const DRAWER_WIDTH = Math.min(Dimensions.get("window").width * 0.82, 300);

type NavItem = {
  label: string;
  href: Href;
  caption?: string;
};

const NAV: NavItem[] = [
  { label: "Chat", href: "/(main)/chat", caption: "Conversa com a assistente" },
  { label: "Uso", href: "/(main)/usage", caption: "Limite do plano (%)" },
  { label: "Agenda", href: "/(main)/agenda", caption: "Lembretes e hábitos" },
  { label: "Planos", href: "/(main)/plans", caption: "Conexão, Premium, Total ou Empresa" },
  { label: "Conta", href: "/(main)/account", caption: "Perfil" },
];

const LEGAL: { label: string; href: Href }[] = [
  { label: "Privacidade", href: "/legal/privacy" },
  { label: "Termos", href: "/legal/terms" },
  { label: "Reembolso", href: "/legal/refund" },
];

export function AppDrawer() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const { open, closeDrawer } = useDrawer();
  const { signOut } = useAuth();
  const { data } = useDashboard();
  const persona = data.me?.persona;
  const avatarId = persona?.avatar_id || "f1";
  const assistantName =
    findAvatarInCatalog(avatarId)?.shortName ??
    (isMaleAvatar(avatarId) ? "Leo" : "Luna");
  const profile = data.me?.profile as Record<string, unknown> | undefined;
  const profileName =
    (typeof profile?.full_name === "string" && profile.full_name.trim()) ||
    (typeof profile?.name === "string" && profile.name.trim()) ||
    (typeof profile?.first_name === "string" && profile.first_name.trim()) ||
    "";
  const emailAlias =
    typeof data.me?.email === "string" && data.me.email.includes("@")
      ? data.me.email.split("@")[0].trim().toLowerCase()
      : "";
  const nameLooksLikeEmailAlias =
    Boolean(profileName) &&
    Boolean(emailAlias) &&
    profileName.trim().toLowerCase() === emailAlias;
  const displayName =
    !nameLooksLikeEmailAlias && profileName ? profileName : "Utilizador";
  const slide = useRef(new Animated.Value(-DRAWER_WIDTH)).current;
  const fade = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!open) return;
    slide.setValue(-DRAWER_WIDTH);
    fade.setValue(0);
    Animated.parallel([
      Animated.timing(slide, {
        toValue: 0,
        duration: 260,
        useNativeDriver: true,
      }),
      Animated.timing(fade, {
        toValue: 1,
        duration: 260,
        useNativeDriver: true,
      }),
    ]).start();
  }, [open, slide, fade]);

  const go = (href: Href) => {
    closeDrawer();
    router.push(href);
  };

  const onSignOut = async () => {
    closeDrawer();
    await signOut();
    router.replace("/login");
  };

  return (
    <Modal
      visible={open}
      transparent
      animationType="none"
      onRequestClose={closeDrawer}
      statusBarTranslucent
    >
      <View style={styles.root}>
        <Pressable style={StyleSheet.absoluteFill} onPress={closeDrawer}>
          <Animated.View style={[styles.backdrop, { opacity: fade }]} />
        </Pressable>

        <Animated.View
          style={[
            styles.panel,
            {
              width: DRAWER_WIDTH,
              paddingTop: insets.top + 12,
              paddingBottom: insets.bottom + 12,
              backgroundColor: colors.drawerBg,
              borderRightColor: colors.border,
              transform: [{ translateX: slide }],
            },
          ]}
        >
          <View style={styles.brandRow}>
            <EgoLogo variant="icon" width={44} />
            <View style={styles.brandText}>
              <Text style={[styles.brand, { color: colors.text }]}>Ego-IA</Text>
              <Text style={[styles.brandSub, { color: colors.textMuted }]}>
                {assistantName}
              </Text>
            </View>
            <Image
              source={avatarImageSource(avatarId)}
              style={styles.avatar}
            />
          </View>

          <View style={[styles.divider, { backgroundColor: colors.border }]} />

          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
            bounces={false}
            keyboardShouldPersistTaps="handled"
          >
            {NAV.map((item) => (
              <Pressable
                key={item.label}
                style={({ pressed }) => [
                  styles.navItem,
                  pressed && { backgroundColor: colors.drawerHover },
                ]}
                onPress={() => go(item.href)}
              >
                <Text style={[styles.navLabel, { color: colors.text }]}>{item.label}</Text>
                {item.caption ? (
                  <Text
                    style={[styles.navCap, { color: colors.textMuted }]}
                    numberOfLines={1}
                  >
                    {item.caption}
                  </Text>
                ) : null}
              </Pressable>
            ))}

            <View style={[styles.divider, { backgroundColor: colors.border }]} />

            <Text style={[styles.section, { color: colors.textMuted }]}>Legal</Text>
            {LEGAL.map((item) => (
              <Pressable
                key={item.label}
                style={({ pressed }) => [styles.legalItem, pressed && { opacity: 0.7 }]}
                onPress={() => go(item.href)}
              >
                <Text style={[styles.legalLabel, { color: colors.primary }]}>{item.label}</Text>
              </Pressable>
            ))}
          </ScrollView>

          <View style={[styles.footer, { borderTopColor: colors.border }]}>
            {displayName ? (
              <Text style={[styles.email, { color: colors.textMuted }]} numberOfLines={1}>
                {displayName}
              </Text>
            ) : null}
            <Pressable
              style={[styles.signOut, { borderColor: colors.border }]}
              onPress={() => void onSignOut()}
              accessibilityRole="button"
              accessibilityLabel="Sair da conta"
            >
              <Text style={[styles.signOutText, { color: colors.text }]}>Sair</Text>
            </Pressable>
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(15, 15, 18, 0.45)",
  },
  panel: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    flexDirection: "column",
    borderRightWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 16,
    shadowColor: "#000",
    shadowOffset: { width: 4, height: 0 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 8,
  },
  scroll: { flex: 1, minHeight: 0 },
  scrollContent: { paddingBottom: 8 },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 4 },
  avatar: { width: 44, height: 44, borderRadius: 22 },
  brandText: { flex: 1 },
  brand: { fontSize: 19, fontWeight: "800", letterSpacing: -0.5 },
  brandSub: { fontSize: 12, marginTop: 2 },
  divider: { height: StyleSheet.hairlineWidth, marginVertical: 10 },
  navItem: {
    borderRadius: 10,
    paddingVertical: 9,
    paddingHorizontal: 10,
    marginBottom: 2,
  },
  navLabel: { fontSize: 16, fontWeight: "700" },
  navCap: { fontSize: 11, marginTop: 1 },
  section: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: 6,
    paddingHorizontal: 4,
  },
  legalItem: { paddingVertical: 6, paddingHorizontal: 4 },
  legalLabel: { fontSize: 14, fontWeight: "600" },
  footer: {
    flexShrink: 0,
    paddingTop: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  email: { fontSize: 12, marginBottom: 8 },
  signOut: {
    alignSelf: "flex-start",
    paddingVertical: 10,
    paddingHorizontal: 18,
    borderRadius: 10,
    borderWidth: 1,
  },
  signOutText: { fontSize: 14, fontWeight: "600" },
});
