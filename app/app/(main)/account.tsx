import * as Application from "expo-application";
import { router } from "expo-router";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { deleteMyAccount } from "@/api/client";
import { PersonaPicker } from "@/components/PersonaPicker";
import { AccountUpdateCard } from "@/components/AccountUpdateCard";
import { ProfilePhoneCard } from "@/components/ProfilePhoneCard";
import { FriendReferralCard } from "@/components/FriendReferralCard";
import { GymCodeLinkPanel } from "@/components/GymCodeLinkPanel";
import { SocialFollowBar } from "@/components/SocialFollowBar";
import { ScreenShell } from "@/components/ScreenShell";
import { UsageDashboard } from "@/components/UsageDashboard";
import { accountPersona } from "@/constants/personas";
import { isProductionApiOk } from "@/constants/config";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { allowsInAppPlanPurchase, usesAppleIap, usesGooglePlayIap } from "@/utils/iosAppStoreBilling";
import { useColors } from "@/theme/ThemeContext";
import { getInstalledAppVersion } from "@/utils/appVersion";

export default function AccountScreen() {
  const colors = useColors();
  const { signOut } = useAuth();
  const { data, loading, refreshing, error, refresh, setPersona } = useDashboard();
  const [deleting, setDeleting] = useState(false);
  const persona = accountPersona(data.me?.persona);
  const apiOk = isProductionApiOk();
  const hasPaidPlan = Boolean(data.access?.is_pro);

  const runDeleteAccount = async () => {
    setDeleting(true);
    try {
      await deleteMyAccount();
      await signOut();
      router.replace("/login");
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "Não foi possível excluir a conta.";
      Alert.alert("Não foi possível excluir", msg);
    } finally {
      setDeleting(false);
    }
  };

  const onDeleteAccountPress = () => {
    const subHint = hasPaidPlan
      ? usesAppleIap()
        ? "\n\nTem plano pago: cancele a assinatura em Ajustes → Apple ID → Assinaturas antes de excluir."
        : usesGooglePlayIap()
          ? "\n\nTem plano pago: cancele a assinatura na Google Play → Assinaturas antes de excluir."
          : allowsInAppPlanPurchase()
            ? "\n\nTem plano pago: cancele a assinatura em Planos ou no portal Stripe antes de excluir."
            : "\n\nTem plano pago: cancele a assinatura onde assinou antes de excluir a conta."
      : "";
    Alert.alert(
      "Excluir minha conta?",
      `Esta ação é permanente. Apagamos o seu perfil, conversas, agenda, monstrinhos e demais dados do EGO-AI.${subHint}\n\nDeseja continuar?`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Excluir conta",
          style: "destructive",
          onPress: () => {
            Alert.alert(
              "Confirmar exclusão",
              "Não há como recuperar os dados depois. A conta será apagada de imediato.",
              [
                { text: "Voltar", style: "cancel" },
                {
                  text: "Excluir permanentemente",
                  style: "destructive",
                  onPress: () => void runDeleteAccount(),
                },
              ]
            );
          },
        },
      ]
    );
  };

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
  const name = !nameLooksLikeEmailAlias && profileName ? profileName : "Utilizador";
  const profilePhone =
    (typeof profile?.phone === "string" && profile.phone.trim()) || "";
  const accessStatus = data.access?.access_status || data.me?.access?.status || "—";

  return (
    <ScreenShell title="Conta" subtitle={name}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={refresh}
            tintColor={colors.primary}
          />
        }
      >
        {loading && !refreshing ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
        ) : null}

        {error ? (
          <Pressable onPress={refresh}>
            <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
            <Text style={[styles.link, { color: colors.primary }]}>Tentar de novo</Text>
          </Pressable>
        ) : null}

        {!loading && !error ? (
          <>
            <Text style={[styles.name, { color: colors.text }]}>{name}</Text>
            <Text style={[styles.badge, { color: colors.textMuted }]}>{accessStatus}</Text>
            <Text style={[styles.version, { color: colors.textMuted }]}>
              Versão {getInstalledAppVersion()}
              {Application.nativeBuildVersion
                ? ` · build ${Application.nativeBuildVersion}`
                : ""}
            </Text>

            <AccountUpdateCard />

            <SocialFollowBar colors={colors} />

            <ProfilePhoneCard colors={colors} phone={profilePhone} onSaved={refresh} />

            <FriendReferralCard colors={colors} />

            <GymCodeLinkPanel colors={colors} />

            <UsageDashboard colors={colors} access={data.access} />

            <Pressable
              onPress={() => router.push("/(main)/usage")}
              style={({ pressed }) => [
                styles.usageLink,
                { borderColor: colors.border, opacity: pressed ? 0.7 : 1 },
              ]}
            >
              <Text style={[styles.usageLinkText, { color: colors.primary }]}>
                Ver painel completo de uso
              </Text>
            </Pressable>

            <PersonaPicker
              colors={colors}
              variant="settings"
              planTier={data.access?.plan_tier || "essential"}
              persona={persona}
              onPersonaChange={(p) => setPersona(p.avatar_id, p.voice_id)}
              onSaved={refresh}
            />

            {allowsInAppPlanPurchase() ? (
              <Pressable
                onPress={() => router.push("/(main)/plans")}
                style={({ pressed }) => [
                  styles.upgradeBtn,
                  {
                    backgroundColor: colors.primary,
                    opacity: pressed ? 0.9 : 1,
                  },
                ]}
              >
                <Text style={styles.upgradeBtnText}>
                  {data.access?.is_pro ? "Ver planos" : "Fazer upgrade"}
                </Text>
              </Pressable>
            ) : null}

            <View style={[styles.row, { borderColor: colors.border }]}>
              <Text style={[styles.rowLabel, { color: colors.textMuted }]}>Lembretes</Text>
              <Text style={[styles.rowValue, { color: colors.text }]}>
                {data.reminders.length}
              </Text>
            </View>

            <View style={[styles.row, { borderColor: colors.border }]}>
              <Text style={[styles.rowLabel, { color: colors.textMuted }]}>Hábitos</Text>
              <Text style={[styles.rowValue, { color: colors.text }]}>
                {data.agenda.length}
              </Text>
            </View>

            {!apiOk ? (
              <Text style={[styles.hint, { color: colors.warning }]}>
                API em HTTP — só para desenvolvimento.
              </Text>
            ) : null}

            <Pressable
              style={[styles.signOut, { borderColor: colors.border }]}
              onPress={() => {
                void (async () => {
                  await signOut();
                  router.replace("/login");
                })();
              }}
              accessibilityRole="button"
              accessibilityLabel="Sair da conta"
              disabled={deleting}
            >
              <Text style={[styles.signOutText, { color: colors.text }]}>Sair</Text>
            </Pressable>

            <View style={[styles.dangerZone, { borderColor: colors.border }]}>
              <Text style={[styles.dangerTitle, { color: colors.text }]}>
                Exclusão de conta
              </Text>
              <Text style={[styles.dangerHint, { color: colors.textMuted }]}>
                Apaga permanentemente a sua conta e dados no EGO-AI. Também pode pedir por e-mail
                em contato@egoai.com.br.
              </Text>
              <Pressable
                style={({ pressed }) => [
                  styles.deleteBtn,
                  { opacity: deleting ? 0.6 : pressed ? 0.85 : 1 },
                ]}
                onPress={onDeleteAccountPress}
                disabled={deleting}
                accessibilityRole="button"
                accessibilityLabel="Excluir minha conta"
              >
                {deleting ? (
                  <ActivityIndicator color={colors.danger} />
                ) : (
                  <Text style={[styles.deleteBtnText, { color: colors.danger }]}>
                    Excluir minha conta
                  </Text>
                )}
              </Pressable>
            </View>
          </>
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 20, paddingBottom: 32 },
  name: { fontSize: 24, fontWeight: "700", letterSpacing: -0.3 },
  badge: { fontSize: 14, marginTop: 4, marginBottom: 8 },
  version: { fontSize: 12, marginBottom: 20 },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  rowLabel: { fontSize: 15 },
  rowValue: { fontSize: 15, fontWeight: "600" },
  hint: { fontSize: 13, marginTop: 20, lineHeight: 18 },
  error: { fontSize: 14 },
  link: { fontSize: 14, marginTop: 8, fontWeight: "600" },
  usageLink: {
    alignItems: "center",
    paddingVertical: 10,
    marginBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  usageLinkText: { fontSize: 14, fontWeight: "600" },
  upgradeBtn: {
    marginTop: 16,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  upgradeBtnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  signOut: {
    marginTop: 28,
    alignSelf: "stretch",
    paddingVertical: 14,
    paddingHorizontal: 18,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: "center",
  },
  signOutText: { fontSize: 16, fontWeight: "700" },
  dangerZone: {
    marginTop: 28,
    paddingTop: 20,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  dangerTitle: { fontSize: 15, fontWeight: "700", marginBottom: 8 },
  dangerHint: { fontSize: 13, lineHeight: 19, marginBottom: 14 },
  deleteBtn: {
    alignSelf: "stretch",
    paddingVertical: 14,
    alignItems: "center",
  },
  deleteBtnText: { fontSize: 16, fontWeight: "700" },
});
