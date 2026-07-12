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
import { fetchPlansCatalog } from "@/api/client";
import type { LaunchPlanOffer, PlanCatalogItem, PlanTier, ReferralPlanOffer } from "@/api/types";
import { PlanCard } from "@/components/PlanCard";
import { ScreenShell } from "@/components/ScreenShell";
import {
  BR_STRIPE_LAUNCH_INDIVIDUAL_TIERS,
  DISPLAY_PRICE_BRL,
  isLaunchCampaignActive,
  LAUNCH_OFFER_INTRO_MONTHS,
  LAUNCH_PLAN_OFFER_BR,
  MONTHLY_PLAN_OFFERS,
  PRICE_INCLUDES_TAXES_NOTE,
  fallbackLimitsForTier,
  sortIndividualOffersByPrice,
} from "@/constants/stripeMonthly";
import { formatMonthlyPrice, subscribeLabelForTier } from "@/constants/plans";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";
import {
  checkoutUrlForTier,
  launchCheckoutUrl,
  withCheckoutUserRef,
} from "@/utils/planCheckout";
import { allowsInAppPlanPurchase, IOS_SUBSCRIPTION_LEGAL, usesAppleIap, usesStripeCheckout } from "@/utils/iosAppStoreBilling";
import { iosIapCatalog, useIosIap } from "@/hooks/useIosIap";
import { IOS_APP_STORE_PRICE_NOTE } from "@/constants/iapProducts";

export default function PlansScreen() {
  const colors = useColors();
  const { data, loading, refreshing, error, refresh } = useDashboard();
  const [catalog, setCatalog] = useState<PlanCatalogItem[]>([]);
  const [launchOffer, setLaunchOffer] = useState<LaunchPlanOffer | null>(null);
  const [referralOffer, setReferralOffer] = useState<ReferralPlanOffer | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [openingKey, setOpeningKey] = useState<string | null>(null);

  const referralActive =
    referralOffer?.active === true ||
    data.access?.referral_offer?.active === true ||
    data.access?.referral_benefit?.active === true;

  const showIosLaunchOffer =
    usesAppleIap() &&
    !referralActive &&
    isLaunchCampaignActive() &&
    (data.access?.plan_tier || "essential") === "essential";

  const iap = useIosIap(() => {
    void refresh();
  }, { showLaunchOffer: showIosLaunchOffer });

  const currentTier = (data.access?.plan_tier || "essential") as PlanTier;
  const checkout = data.me?.stripe_checkout;
  const userId = data.me?.user_id?.trim() ?? "";

  const loadCatalog = useCallback(async () => {
    setCatalogLoading(true);
    try {
      const { plans, launchOffer: launch, referralOffer: referral } = await fetchPlansCatalog();
      setCatalog(plans);
      setLaunchOffer(launch);
      setReferralOffer(referral);
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

  const essentialPlan = catalog.find((p) => p.tier === "essential");

  const onIapSubscribe = async (
    tier: Exclude<PlanTier, "essential" | "enterprise">,
    busyKey: string
  ) => {
    setOpeningKey(busyKey);
    try {
      await iap.purchaseTier(tier);
    } finally {
      setOpeningKey(null);
    }
  };

  const renderIosIapPlans = () =>
    iosIapCatalog().map((offer) => {
      const key = `iap-${offer.tier}`;
      const display = iap.productDisplay[offer.tier];
      return (
        <PlanCard
          key={key}
          colors={colors}
          plan={{
            tier: offer.tier,
            label: offer.label,
            price_brl: offer.priceBrl,
            limits: limitsByTier.get(offer.tier) ?? fallbackLimitsForTier(offer.tier),
          }}
          isCurrent={currentTier === offer.tier}
          highlighted={
            offer.tier === "connection"
              ? Boolean(display?.highlighted)
              : offer.tier === "premium"
          }
          badgeLabel={display?.badgeLabel}
          checkoutUrl={null}
          onSubscribe={() => {}}
          purchaseViaIap
          onIapPurchase={(tier) => {
            if (tier === "essential" || tier === "enterprise") return;
            void onIapSubscribe(tier, key);
          }}
          busy={iap.busy || openingKey === key}
          priceOverride={display?.priceLine ?? formatMonthlyPrice(offer.priceBrl)}
          priceNote={IOS_APP_STORE_PRICE_NOTE}
          subscribeLabel={subscribeLabelForTier(offer.tier, currentTier)}
          footnote={display?.footnote}
        />
      );
    });

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
          "Não foi possível abrir o link. Verifique STRIPE_CHECKOUT_* no .env do servidor."
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

  const showLaunchCard =
    usesStripeCheckout() &&
    !referralActive &&
    (launchOffer != null || isLaunchCampaignActive()) &&
    Boolean(
      launchCheckoutUrl(checkout) ||
        launchOffer?.checkout_url?.trim()
    );
  const launchUrl = showLaunchCard
    ? launchCheckoutUrl(checkout) ||
      launchOffer?.checkout_url?.trim() ||
      null
    : null;
  const launchIntroMonths =
    launchOffer?.intro_months ?? LAUNCH_OFFER_INTRO_MONTHS;
  const launchPriceNum = launchOffer?.price_brl ?? LAUNCH_PLAN_OFFER_BR.priceNum;
  const launchTier = (launchOffer?.tier || LAUNCH_PLAN_OFFER_BR.tier) as PlanTier;

  const activeReferralOffer =
    referralOffer?.active === true
      ? referralOffer
      : data.access?.referral_offer?.active === true
        ? data.access.referral_offer
        : null;

  const referralDiscount =
    activeReferralOffer?.discount_percent ??
    data.access?.referral_benefit?.discount_percent ??
    10;

  const brIndividualSorted = useMemo(
    () =>
      sortIndividualOffersByPrice(
        MONTHLY_PLAN_OFFERS.filter(
          (o) =>
            o.market === "br" &&
            (BR_STRIPE_LAUNCH_INDIVIDUAL_TIERS as readonly string[]).includes(o.tier)
        )
      ),
    []
  );

  const renderEssentialBr = () => {
    const key = "essential-br";
    return (
      <PlanCard
        key={key}
        colors={colors}
        plan={{
          tier: "essential",
          label: essentialPlan?.label || "EGO Essencial",
          price_brl: 0,
          limits:
            essentialPlan?.limits ??
            limitsByTier.get("essential") ??
            fallbackLimitsForTier("essential"),
        }}
        isCurrent={currentTier === "essential"}
        checkoutUrl={null}
        onSubscribe={() => {}}
        busy={false}
        priceOverride="Grátis"
        footnote={
          currentTier !== "essential"
            ? usesAppleIap()
              ? "Para voltar ao grátis, cancele em Ajustes → Apple ID → Assinaturas."
              : allowsInAppPlanPurchase()
                ? "Assinatura mensal: cancele no Stripe para voltar ao grátis."
                : "Plano ativo nesta conta."
            : undefined
        }
      />
    );
  };

  const renderReferralOffer = () => {
    if (!referralActive) return null;
    const tagline =
      activeReferralOffer?.tagline?.trim() ||
      (activeReferralOffer?.partner_code
        ? `Cupom ${activeReferralOffer.partner_code}${
            activeReferralOffer.partner_name
              ? ` · ${activeReferralOffer.partner_name}`
              : ""
          }`
        : "Cupom parceiro ativo");
    return (
      <View
        style={[
          styles.referralBox,
          { backgroundColor: colors.primaryTint, borderColor: colors.primary },
        ]}
      >
        <Text style={[styles.referralTitle, { color: colors.primary }]}>
          🎁 Plano parceiro · {referralDiscount}% na 1ª assinatura
        </Text>
        <Text style={[styles.sectionHint, { color: colors.textMuted, marginBottom: 0 }]}>
          {tagline}
        </Text>
        <Text style={[styles.referralFoot, { color: colors.textMuted }]}>
          {allowsInAppPlanPurchase()
            ? "Escolha Conexão, Premium ou Total abaixo. O desconto aplica uma vez no checkout. Plano EGO Lançamento não aparece para cupom de parceiro."
            : "Cupom parceiro válido na sua conta. Compra de planos não está disponível neste app iOS."}
        </Text>
      </View>
    );
  };

  const renderLaunchOffer = () => {
    if (!launchUrl) return null;
    const key = "launch-br";
    return (
      <PlanCard
        key={key}
        colors={colors}
        plan={{
          tier: launchTier,
          label: launchOffer?.label || LAUNCH_PLAN_OFFER_BR.label,
          price_brl: launchPriceNum,
          limits:
            launchOffer?.limits ??
            limitsByTier.get(launchTier) ??
            fallbackLimitsForTier(launchTier),
        }}
        isCurrent={false}
        highlighted
        badgeLabel={`Lançamento · ${launchIntroMonths} meses`}
        checkoutUrl={launchUrl}
        onSubscribe={(_, u) => onSubscribe(key, u)}
        busy={openingKey === key}
        priceOverride={
          launchOffer?.price_label || LAUNCH_PLAN_OFFER_BR.displayPrice
        }
        subscribeLabel={subscribeLabelForTier(launchTier, currentTier, {
          isLaunch: true,
        })}
        footnote={
          launchOffer?.tagline ||
          `Oferta de lançamento: R$ 10,94/mês (inclui impostos e taxas) por ${launchIntroMonths} meses. Depois R$ 19,90/mês por ${launchIntroMonths} meses. Depois R$ 32,74/mês (EGO Conexão). Cancele quando quiser. Sem cupons adicionais.`
        }
        priceNote={PRICE_INCLUDES_TAXES_NOTE}
      />
    );
  };

  const renderIndividualBr = () => {
    return brIndividualSorted.map((offer) => {
      const url = checkoutUrlForTier(offer.tier, checkout, "br");
      const priceNum = DISPLAY_PRICE_BRL[offer.tier];
      const key = `ind-br-${offer.tier}`;
      return (
        <PlanCard
          key={key}
          colors={colors}
          plan={{
            tier: offer.tier,
            label: offer.label,
            price_brl: priceNum,
            limits:
              limitsByTier.get(offer.tier) ?? fallbackLimitsForTier(offer.tier),
          }}
          isCurrent={currentTier === offer.tier}
          highlighted={offer.highlighted}
          checkoutUrl={url}
          onSubscribe={(_, u) => onSubscribe(key, u)}
          busy={openingKey === key}
          priceNote={PRICE_INCLUDES_TAXES_NOTE}
          subscribeLabel={subscribeLabelForTier(offer.tier, currentTier)}
        />
      );
    });
  };

  return (
    <ScreenShell
      title="Planos"
      subtitle={
        usesAppleIap()
          ? "Assinatura mensal · compra na App Store"
          : "Lançamento, Conexão, Premium e Total · mensal"
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
              Tentar de novo (os planos abaixo continuam disponíveis)
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
                Seu plano
              </Text>
              <Text style={[styles.currentName, { color: colors.text }]}>
                {data.access?.plan_label || "EGO Essencial"}
              </Text>
              <Text style={[styles.currentHint, { color: colors.textMuted }]}>
                {currentTier === "essential"
                  ? `Grátis · ${formatMonthlyPrice(0)}`
                  : usesAppleIap()
                    ? "Assinatura mensal · App Store"
                    : "Assinatura mensal · você pode mudar de plano abaixo a qualquer momento"}
              </Text>
            </View>

            {usesAppleIap() ? (
              <>
                <Text style={[styles.sectionTitle, { color: colors.text }]}>
                  Assinaturas mensais
                </Text>
                <Text style={[styles.sectionHint, { color: colors.textMuted }]}>
                  {showIosLaunchOffer
                    ? `EGO Conexão com oferta de lançamento na App Store: R$ 19,90/mês por ${LAUNCH_OFFER_INTRO_MONTHS} meses (quem nunca assinou), depois R$ 39,90/mês. Renovação automática até cancelar.`
                    : "Pagamento via App Store. Conexão R$ 39,90 · Premium R$ 69,90 · Total R$ 129,90/mês. Pode mudar de plano quando quiser."}
                </Text>
                {renderEssentialBr()}
                {renderIosIapPlans()}
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
                  {IOS_SUBSCRIPTION_LEGAL}
                </Text>
              </>
            ) : null}

            {usesStripeCheckout() ? (
              <>
                {renderReferralOffer()}

                {showLaunchCard && launchUrl ? (
                  <>
                    <Text style={[styles.sectionTitle, { color: colors.text }]}>
                      EGO Lançamento — R$ 10,94
                    </Text>
                    <Text style={[styles.sectionHint, { color: colors.textMuted }]}>
                      Oferta promocional · limites do EGO Conexão · válida por{" "}
                      {launchIntroMonths} meses.
                    </Text>
                    {renderLaunchOffer()}
                  </>
                ) : null}

                <Text style={[styles.sectionTitle, { color: colors.text }]}>
                  Planos mensais (Brasil)
                </Text>
                <Text style={[styles.sectionHint, { color: colors.textMuted }]}>
                  Essencial grátis · Lançamento R$ 10,94 · Conexão R$ 32,74 · Premium R$ 54,64 ·
                  Total R$ 109,39. Preços incluem impostos e taxas. Sem Equipe nem Empresa neste
                  lançamento.
                </Text>
                {renderEssentialBr()}
                {renderIndividualBr()}
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
  referralBox: {
    borderRadius: 16,
    borderWidth: 1.5,
    padding: 14,
    marginBottom: 16,
  },
  referralTitle: { fontSize: 15, fontWeight: "800", marginBottom: 6 },
  referralFoot: { fontSize: 12, lineHeight: 17, marginTop: 8 },
  restoreBtn: {
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
    paddingVertical: 14,
    alignItems: "center",
    marginBottom: 12,
  },
  restoreText: { fontSize: 15, fontWeight: "700" },
  legalFoot: { fontSize: 11, lineHeight: 16, marginBottom: 8 },
  errorBanner: { marginBottom: 16 },
  error: { fontSize: 14 },
  link: { fontSize: 14, marginTop: 8, fontWeight: "600" },
});
