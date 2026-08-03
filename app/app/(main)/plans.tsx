import { useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { createPartnerPremiumCheckout, fetchPlansCatalog } from "@/api/client";
import type { PlanCatalogItem, PlanTier } from "@/api/types";
import { PlanCard } from "@/components/PlanCard";
import { ScreenShell } from "@/components/ScreenShell";
import {
  DISPLAY_PRICE_BRL,
  DISPLAY_PRICE_USD,
  MONTHLY_PLAN_OFFERS,
  fallbackLimitsForTier,
  type MonthlyMarket,
} from "@/constants/stripeMonthly";
import { formatMonthlyPrice } from "@/constants/plans";
import { IOS_APP_STORE_PRICE_NOTE } from "@/constants/iapProducts";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";
import { checkoutUrlForTier, withCheckoutUserRef } from "@/utils/planCheckout";
import { gymCheckoutPageUrl } from "@/constants/gymCheckout";
import { useGymPartner } from "@/context/GymPartnerContext";
import {
  IOS_PRIVACY_POLICY_URL,
  IOS_TERMS_OF_USE_URL,
  storeCancelHint,
  storeSubscriptionLegal,
  usesGooglePlayIap,
  usesStoreIap,
  usesStripeCheckout,
} from "@/utils/iosAppStoreBilling";
import { iosIapCatalog, useIosIap } from "@/hooks/useIosIap";

export default function PlansScreen() {
  const colors = useColors();
  const { data, loading, refreshing, error, refresh } = useDashboard();
  const { gymCode, partner, usesGymStripe } = useGymPartner();
  const [catalog, setCatalog] = useState<PlanCatalogItem[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [openingKey, setOpeningKey] = useState<string | null>(null);

  const iap = useIosIap(() => {
    void refresh();
  }, { showLaunchOffer: false });

  const currentTier = (data.access?.plan_tier || "essential") as PlanTier;
  const checkout = data.me?.stripe_checkout;
  const userId = data.me?.user_id?.trim() ?? "";
  const isPaid = currentTier !== "essential";
  const storeName = usesGooglePlayIap() ? "Google Play" : "App Store";
  const showIap = usesStoreIap() && !usesGymStripe;
  const showWebStripe = usesStripeCheckout() && !usesGymStripe;

  const loadCatalog = useCallback(async () => {
    setCatalogLoading(true);
    try {
      const { plans } = await fetchPlansCatalog();
      setCatalog(plans);
    } catch {
      setCatalog([]);
    } finally {
      setCatalogLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void refresh();
      void loadCatalog();
    }, [refresh, loadCatalog])
  );

  const limitsByTier = useMemo(() => {
    const map = new Map<PlanTier, PlanCatalogItem["limits"]>();
    for (const p of catalog) {
      map.set(p.tier, p.limits);
    }
    return map;
  }, [catalog]);

  const premiumLimits =
    limitsByTier.get("premium") ??
    (isPaid ? limitsByTier.get(currentTier) : undefined) ??
    fallbackLimitsForTier("premium");

  const onIapSubscribe = async (busyKey: string) => {
    setOpeningKey(busyKey);
    try {
      await iap.purchaseTier("premium");
    } finally {
      setOpeningKey(null);
    }
  };

  const onGymStripeSubscribe = async () => {
    if (!gymCode?.trim()) return;
    const gymName = partner?.name || "teu parceiro";
    setOpeningKey("gym-stripe");
    try {
      Alert.alert(
        "EGO Premium",
        `Canal parceiro: só Stripe Connect (sem loja).\n\nPremium Voz R$ 49,90/mês.\n≈30% (${gymName}) · ≈70% EGO — split automático no Stripe.\n\nAbrir checkout?`,
        [
          { text: "Cancelar", style: "cancel", onPress: () => setOpeningKey(null) },
          {
            text: "Pagar no Stripe",
            onPress: async () => {
              try {
                let url = "";
                try {
                  const session = await createPartnerPremiumCheckout();
                  url = session.url;
                } catch {
                  url = gymCheckoutPageUrl(gymCode);
                }
                await Linking.openURL(url);
                Alert.alert(
                  "Pagamento",
                  "Se já concluíste no Stripe, volta ao app e puxa para atualizar (pode demorar alguns segundos)."
                );
              } catch (e) {
                Alert.alert(
                  "Erro",
                  e instanceof Error ? e.message : "Não foi possível abrir o checkout."
                );
              } finally {
                setOpeningKey(null);
              }
            },
          },
        ]
      );
    } catch {
      setOpeningKey(null);
    }
  };

  const onSubscribe = async (busyKey: string, url: string) => {
    if (!usesStripeCheckout()) return;
    setOpeningKey(busyKey);
    const checkoutUrl = withCheckoutUserRef(url, userId);
    if (!checkoutUrl) {
      Alert.alert("Assinar", "Link de pagamento indisponível. Tente de novo em instantes.");
      setOpeningKey(null);
      return;
    }
    try {
      const canOpen = await Linking.canOpenURL(checkoutUrl);
      if (!canOpen) {
        Alert.alert(
          "Checkout",
          "Não foi possível abrir o link. Verifique STRIPE_CHECKOUT_PREMIUM_URL no servidor."
        );
        return;
      }
      await Linking.openURL(checkoutUrl);
      Alert.alert(
        "Pagamento",
        "Assinatura mensal no Stripe. Após pagar, volte ao app e puxe para atualizar. " +
          "Para mudar ou cancelar depois, use o mesmo e-mail no portal Stripe."
      );
    } catch (e) {
      Alert.alert(
        "Erro",
        e instanceof Error ? e.message : "Não foi possível abrir o checkout."
      );
    } finally {
      setOpeningKey(null);
    }
  };

  const onRefresh = () => {
    void refresh();
    void loadCatalog();
  };

  const busy = loading || catalogLoading;
  const showErrorBanner = Boolean(error);

  const renderPremiumIap = () => {
    const offer = iosIapCatalog().find((o) => o.tier === "premium");
    if (!offer) return null;
    const key = "iap-premium";
    const display = iap.productDisplay.premium;
    return (
      <PlanCard
        key={key}
        colors={colors}
        plan={{
          tier: "premium",
          label: "EGO Premium",
          price_brl: offer.priceBrl,
          limits: premiumLimits,
        }}
        isCurrent={isPaid}
        highlighted
        badgeLabel={isPaid ? "Seu plano" : "Recomendado"}
        checkoutUrl={null}
        onSubscribe={() => {}}
        purchaseViaIap
        onIapPurchase={() => {
          if (isPaid) return;
          void onIapSubscribe(key);
        }}
        busy={iap.busy || openingKey === key}
        priceOverride={display?.priceLine ?? formatMonthlyPrice(offer.priceBrl)}
        priceNote={IOS_APP_STORE_PRICE_NOTE}
        subscribeLabel={isPaid ? "Plano atual" : "Assinar Premium"}
        footnote={
          isPaid
            ? `Para cancelar: ${storeCancelHint()}`
            : "3 dias grátis no teste · depois renovação automática até cancelar."
        }
      />
    );
  };

  const renderPremiumStripe = (market: MonthlyMarket) => {
    const offer = MONTHLY_PLAN_OFFERS.find((o) => o.market === market);
    if (!offer) return null;
    const url = checkoutUrlForTier("premium", checkout, market);
    const priceNum =
      market === "br" ? DISPLAY_PRICE_BRL.premium : DISPLAY_PRICE_USD.premium;
    const key = `premium-${market}`;
    return (
      <PlanCard
        key={key}
        colors={colors}
        plan={{
          tier: "premium",
          label: "EGO Premium",
          price_brl: priceNum,
          limits: premiumLimits,
        }}
        isCurrent={isPaid}
        highlighted
        badgeLabel={isPaid ? "Seu plano" : "Recomendado"}
        checkoutUrl={url}
        onSubscribe={(_, u) => onSubscribe(key, u)}
        busy={openingKey === key}
        priceOverride={market === "int" ? offer.displayPrice : undefined}
        subscribeLabel={isPaid ? "Plano atual" : "Assinar Premium"}
        footnote={
          isPaid
            ? "Para cancelar, use o portal Stripe com o mesmo e-mail da conta."
            : offer.tagline
        }
      />
    );
  };

  const renderPremiumGymStripe = () => {
    const key = "gym-stripe";
    return (
      <PlanCard
        key={key}
        colors={colors}
        plan={{
          tier: "premium",
          label: "EGO Premium",
          price_brl: 49.9,
          limits: premiumLimits,
        }}
        isCurrent={isPaid}
        highlighted
        badgeLabel={isPaid ? "Seu plano" : "Parceiro"}
        checkoutUrl={null}
        onSubscribe={() => {}}
        purchaseViaIap
        onIapPurchase={() => {
          if (isPaid) return;
          void onGymStripeSubscribe();
        }}
        busy={openingKey === key}
        priceOverride={formatMonthlyPrice(49.9)}
        priceNote="Canal parceiro · só Stripe Connect · 30%"
        subscribeLabel={isPaid ? "Plano atual" : "Assinar EGO Premium →"}
        footnote={
          isPaid
            ? "EGO Premium activo · Stripe Connect (parceiro)"
            : partner?.name
              ? `${partner.name}: sem IAP/lojas nesta conta. Outros produtos do parceiro pagam-se à parte.`
              : "Canal parceiro = Stripe só. Sem App Store / Play nesta conta."
        }
      />
    );
  };

  return (
    <ScreenShell
      title="EGO Premium"
      subtitle={
        usesGymStripe
          ? `Stripe parceiro${partner?.name ? ` · ${partner.name}` : ""}`
          : showIap
            ? `Assinatura mensal · ${storeName}`
            : "3 dias grátis · depois R$ 49,90/mês"
      }
    >
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primary}
          />
        }
      >
        {busy && !refreshing ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
        ) : null}

        {showErrorBanner ? (
          <Pressable onPress={onRefresh} style={styles.errorBanner}>
            <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
            <Text style={[styles.link, { color: colors.primary }]}>
              Tentar de novo
            </Text>
          </Pressable>
        ) : null}

        {!busy ? (
          <>
            <View
              style={[
                styles.currentBox,
                { backgroundColor: colors.bgCard, borderColor: colors.border },
              ]}
            >
              <Text style={[styles.currentLabel, { color: colors.textMuted }]}>
                Seu acesso
              </Text>
              <Text style={[styles.currentName, { color: colors.text }]}>
                {isPaid ? "EGO Premium" : data.access?.access_status || "Teste 3 dias"}
              </Text>
              <Text style={[styles.currentHint, { color: colors.textMuted }]}>
                {isPaid
                  ? usesGymStripe
                    ? "Assinatura activa · Stripe (parceiro)"
                    : showIap
                      ? `Assinatura activa · ${storeName}`
                      : "Assinatura activa · Stripe"
                  : usesGymStripe
                    ? "Com código de parceiro: Premium só via Stripe Connect (≈30% ao parceiro)."
                    : "Depois do teste, assine o EGO Premium para continuar."}
              </Text>
              {!isPaid ? (
                <Text style={[styles.currentHint, { color: colors.textMuted }]}>
                  {formatMonthlyPrice(0)} no teste · depois {formatMonthlyPrice(49.9)}
                </Text>
              ) : null}
            </View>

            {usesGymStripe ? (
              <>
                <Text style={[styles.sectionTitle, { color: colors.text }]}>
                  Plano parceiro
                </Text>
                <Text style={[styles.sectionHint, { color: colors.textMuted }]}>
                  Conta ligada a parceiro — pagamento só no Stripe Connect. IAP da{" "}
                  {storeName} está escondido nesta conta.
                </Text>
                {renderPremiumGymStripe()}
              </>
            ) : null}

            {showIap ? (
              <>
                <Text style={[styles.sectionTitle, { color: colors.text }]}>
                  Plano mensal
                </Text>
                <Text style={[styles.sectionHint, { color: colors.textMuted }]}>
                  Um plano só: EGO Premium. Pagamento via {storeName}. Renovação
                  automática até cancelar.
                </Text>
                {renderPremiumIap()}
                <Pressable
                  disabled={iap.busy}
                  onPress={() => void iap.restorePurchases()}
                  style={({ pressed }) => [
                    styles.restoreBtn,
                    {
                      borderColor: colors.border,
                      backgroundColor: colors.bgCard,
                      opacity: pressed ? 0.88 : 1,
                    },
                  ]}
                >
                  <Text style={[styles.restoreText, { color: colors.primary }]}>
                    Restaurar compras
                  </Text>
                </Pressable>
                <Text style={[styles.legalFoot, { color: colors.textMuted }]}>
                  {storeSubscriptionLegal()}
                </Text>
                <View style={styles.legalLinksRow}>
                  <Pressable
                    onPress={() => void Linking.openURL(IOS_TERMS_OF_USE_URL)}
                    hitSlop={8}
                  >
                    <Text style={[styles.legalLink, { color: colors.primary }]}>
                      Termos de Uso (EULA)
                    </Text>
                  </Pressable>
                  <Text style={{ color: colors.textMuted }}> · </Text>
                  <Pressable
                    onPress={() => void Linking.openURL(IOS_PRIVACY_POLICY_URL)}
                    hitSlop={8}
                  >
                    <Text style={[styles.legalLink, { color: colors.primary }]}>
                      Privacidade
                    </Text>
                  </Pressable>
                </View>
              </>
            ) : null}

            {showWebStripe ? (
              <>
                <Text style={[styles.sectionTitle, { color: colors.text }]}>
                  Brasil — R$ 49,90/mês
                </Text>
                {renderPremiumStripe("br")}

                <Text style={[styles.sectionTitle, { color: colors.text }]}>
                  Internacional — US$ 14,99/mês
                </Text>
                {renderPremiumStripe("int")}

                <Text style={[styles.footer, { color: colors.textMuted }]}>
                  Um plano só: EGO Premium. Cancele quando quiser.
                </Text>
              </>
            ) : null}
          </>
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 20, paddingBottom: 40 },
  currentBox: {
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 16,
    marginBottom: 20,
  },
  currentLabel: { fontSize: 12, fontWeight: "700", textTransform: "uppercase" },
  currentName: { fontSize: 22, fontWeight: "800", marginTop: 4 },
  currentHint: { fontSize: 14, marginTop: 6 },
  sectionTitle: {
    fontSize: 17,
    fontWeight: "800",
    marginBottom: 12,
    marginTop: 8,
  },
  sectionHint: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 12,
    marginTop: -4,
  },
  footer: { fontSize: 13, lineHeight: 19, marginTop: 16 },
  restoreBtn: {
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
    paddingVertical: 14,
    alignItems: "center",
    marginBottom: 12,
  },
  restoreText: { fontSize: 15, fontWeight: "700" },
  legalFoot: { fontSize: 11, lineHeight: 16, marginBottom: 8 },
  legalLinksRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    marginBottom: 16,
  },
  legalLink: { fontSize: 12, fontWeight: "700", textDecorationLine: "underline" },
  errorBanner: { marginBottom: 16 },
  error: { fontSize: 14 },
  link: { fontSize: 14, marginTop: 8, fontWeight: "600" },
});
