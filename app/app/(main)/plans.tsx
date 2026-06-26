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
  DISPLAY_PRICE_BRL,
  DISPLAY_PRICE_USD,
  isLaunchCampaignActive,
  LAUNCH_OFFER_INTRO_MONTHS,
  LAUNCH_PLAN_OFFER_BR,
  MONTHLY_PLAN_OFFERS,
  fallbackLimitsForTier,
  sortIndividualOffersByPrice,
  type MonthlyMarket,
} from "@/constants/stripeMonthly";
import { TEAM_PLAN_OFFERS } from "@/constants/teamStripeCheckout";
import { formatMonthlyPrice, subscribeLabelForTier } from "@/constants/plans";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";
import {
  checkoutUrlForTier,
  LAUNCH_CHECKOUT_FALLBACK,
  launchCheckoutUrl,
  teamCheckoutUrl,
  withCheckoutUserRef,
} from "@/utils/planCheckout";

const MARKET_TITLE: Record<MonthlyMarket, string> = {
  br: "Brasil (R$) — mensal",
  int: "Internacional (USD) — mensal",
};

export default function PlansScreen() {
  const colors = useColors();
  const { data, loading, refreshing, error, refresh } = useDashboard();
  const [catalog, setCatalog] = useState<PlanCatalogItem[]>([]);
  const [launchOffer, setLaunchOffer] = useState<LaunchPlanOffer | null>(null);
  const [referralOffer, setReferralOffer] = useState<ReferralPlanOffer | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [openingKey, setOpeningKey] = useState<string | null>(null);

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

  const onSubscribe = async (busyKey: string, url: string) => {
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

  const referralActive =
    referralOffer?.active === true ||
    data.access?.referral_offer?.active === true ||
    data.access?.referral_benefit?.active === true;

  /** Cupom parceiro: esconde EGO Lançamento e mostra benefício 10% na 1ª compra. */
  const showLaunchCard =
    !referralActive &&
    (launchOffer != null || isLaunchCampaignActive()) &&
    Boolean(
      launchCheckoutUrl(checkout) ||
        launchOffer?.checkout_url?.trim() ||
        (!referralActive && LAUNCH_CHECKOUT_FALLBACK)
    );
  const launchUrl = showLaunchCard
    ? launchCheckoutUrl(checkout) ||
      launchOffer?.checkout_url?.trim() ||
      LAUNCH_CHECKOUT_FALLBACK
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
        MONTHLY_PLAN_OFFERS.filter((o) => o.market === "br")
      ),
    []
  );

  const intIndividualSorted = useMemo(
    () =>
      sortIndividualOffersByPrice(
        MONTHLY_PLAN_OFFERS.filter((o) => o.market === "int")
      ),
    []
  );

  const teamSorted = (market: MonthlyMarket) =>
    [...TEAM_PLAN_OFFERS.filter((o) => o.market === market)].sort(
      (a, b) => a.priceNum - b.priceNum
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
            ? "Assinatura mensal: cancele no Stripe para voltar ao grátis."
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
          Escolha Conexão, Premium ou Total abaixo. O desconto aplica uma vez no checkout.
          Plano EGO Lançamento não aparece para cupom de parceiro.
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
          `Oferta de lançamento: R$ 10,94/mês (inclui impostos e taxas) por ${launchIntroMonths} meses. Depois R$ 19,90/mês por ${launchIntroMonths} meses. Depois R$ 29,90/mês (EGO Conexão). Cancele quando quiser. Sem cupons adicionais.`
        }
      />
    );
  };

  const renderIndividual = (market: MonthlyMarket) => {
    const offers = market === "br" ? brIndividualSorted : intIndividualSorted;
    const displayPrices = market === "br" ? DISPLAY_PRICE_BRL : DISPLAY_PRICE_USD;
    return offers.map((offer) => {
      const url = checkoutUrlForTier(offer.tier, checkout, market);
      const priceNum = displayPrices[offer.tier];
      const key = `ind-${market}-${offer.tier}`;
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
          priceOverride={market === "int" ? offer.displayPrice : undefined}
          subscribeLabel={subscribeLabelForTier(offer.tier, currentTier)}
        />
      );
    });
  };

  const renderTeam = (market: MonthlyMarket) => {
    return teamSorted(market).map((offer) => {
      const url = teamCheckoutUrl(offer.tier, offer.seats, checkout, market);
      const key = `team-${market}-${offer.tier}-${offer.seats}`;
      return (
        <PlanCard
          key={key}
          colors={colors}
          plan={{
            tier: offer.tier,
            label: offer.label,
            price_brl: offer.priceNum,
            limits:
              limitsByTier.get(offer.tier) ?? fallbackLimitsForTier(offer.tier),
          }}
          isCurrent={false}
          highlighted={offer.seats === 30}
          checkoutUrl={url}
          onSubscribe={(_, u) => onSubscribe(key, u)}
          busy={openingKey === key}
          priceOverride={offer.displayPrice}
          subscribeLabel="Assinar equipe"
        />
      );
    });
  };

  return (
    <ScreenShell title="Planos" subtitle="Mensal · todos os planos · pode mudar quando quiser">
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
                  : "Assinatura mensal · você pode mudar de plano abaixo a qualquer momento"}
              </Text>
            </View>

            {renderReferralOffer()}

            {showLaunchCard && launchUrl ? (
              <>
                <Text style={[styles.sectionTitle, { color: colors.text }]}>
                  EGO Lançamento — R$ 10,94
                </Text>
                <Text style={[styles.sectionHint, { color: colors.textMuted }]}>
                  Oferta promocional para todos (mesmo no plano Total ou Premium). Limites do
                  EGO Conexão · válida por {launchIntroMonths} meses.
                </Text>
                {renderLaunchOffer()}
              </>
            ) : null}

            <Text style={[styles.sectionTitle, { color: colors.text }]}>
              {MARKET_TITLE.br} — individual
            </Text>
            <Text style={[styles.sectionHint, { color: colors.textMuted }]}>
              Todos os planos aparecem para todos. Ordem: do mais barato ao mais caro.
              Pagamento mensal — pode mudar de plano quando quiser.
            </Text>
            {renderEssentialBr()}
            {renderIndividual("br")}

            <Text style={[styles.sectionTitle, { color: colors.text }]}>
              {MARKET_TITLE.br} — equipes (agenda compartilhada)
            </Text>
            <Text style={[styles.sectionHint, { color: colors.textMuted }]}>
              Planos para várias pessoas · ordenados por preço.
            </Text>
            {renderTeam("br")}

            <Text style={[styles.sectionTitle, { color: colors.text }]}>
              {MARKET_TITLE.int} — individual
            </Text>
            {renderIndividual("int")}

            <Text style={[styles.sectionTitle, { color: colors.text }]}>
              {MARKET_TITLE.int} — teams
            </Text>
            {renderTeam("int")}
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
  errorBanner: { marginBottom: 16 },
  error: { fontSize: 14 },
  link: { fontSize: 14, marginTop: 8, fontWeight: "600" },
});
