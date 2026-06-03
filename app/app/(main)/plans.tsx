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
import { TEAM_PLAN_OFFERS } from "@/constants/teamStripeCheckout";
import { formatMonthlyPrice } from "@/constants/plans";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";
import { checkoutUrlForTier, teamCheckoutUrl } from "@/utils/planCheckout";

const MARKET_TITLE: Record<MonthlyMarket, string> = {
  br: "Brasil (R$) — mensal",
  int: "Internacional (USD) — mensal",
};

export default function PlansScreen() {
  const colors = useColors();
  const { data, loading, refreshing, error, refresh } = useDashboard();
  const [catalog, setCatalog] = useState<PlanCatalogItem[]>([]);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [openingKey, setOpeningKey] = useState<string | null>(null);

  const currentTier = (data.access?.plan_tier || "essential") as PlanTier;
  const checkout = data.me?.stripe_checkout;

  const loadCatalog = useCallback(async () => {
    setCatalogLoading(true);
    setCatalogError(null);
    try {
      const plans = await fetchPlansCatalog();
      setCatalog(plans);
    } catch {
      // Se a API /plans não existir neste backend, seguimos com os limites fallback.
      setCatalog([]);
      setCatalogError(null);
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
    try {
      const canOpen = await Linking.canOpenURL(url);
      if (!canOpen) {
        Alert.alert(
          "Checkout",
          "Não foi possível abrir o link. Verifique STRIPE_CHECKOUT_* no .env do servidor."
        );
        return;
      }
      await Linking.openURL(url);
      Alert.alert(
        "Pagamento",
        "Após pagar no Stripe, volte ao app e puxe para atualizar em Conta ou aqui."
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
  const showError = error;

  const renderIndividual = (market: MonthlyMarket) => {
    const offers = MONTHLY_PLAN_OFFERS.filter(
      (o) => o.market === market && o.tier !== "enterprise"
    );
    return offers.map((offer) => {
      const url = checkoutUrlForTier(offer.tier, checkout, market);
      const priceNum =
        market === "br"
          ? DISPLAY_PRICE_BRL[offer.tier]
          : DISPLAY_PRICE_USD[offer.tier];
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
        />
      );
    });
  };

  const renderTeam = (market: MonthlyMarket) => {
    const offers = TEAM_PLAN_OFFERS.filter((o) => o.market === market);
    return offers.map((offer) => {
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
        />
      );
    });
  };

  return (
    <ScreenShell title="Planos" subtitle="Individual e equipes · Stripe">
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

        {showError ? (
          <Pressable onPress={onRefresh}>
            <Text style={[styles.error, { color: colors.danger }]}>{showError}</Text>
            <Text style={[styles.link, { color: colors.primary }]}>Tentar de novo</Text>
          </Pressable>
        ) : null}

        {!busy && !showError ? (
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
              {currentTier === "essential" && essentialPlan ? (
                <Text style={[styles.currentHint, { color: colors.textMuted }]}>
                  Grátis · {formatMonthlyPrice(0)}
                </Text>
              ) : null}
            </View>

            <Text style={[styles.sectionTitle, { color: colors.text }]}>
              {MARKET_TITLE.br} — individual
            </Text>
            {renderIndividual("br")}

            <Text style={[styles.sectionTitle, { color: colors.text }]}>
              {MARKET_TITLE.br} — equipes (agenda compartilhada)
            </Text>
            <Text style={[styles.sectionHint, { color: colors.textMuted }]}>
              Após pagar, convide até N e-mails em Agenda → Compartilhadas.
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
  intro: { fontSize: 15, lineHeight: 22, marginBottom: 16 },
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
  error: { fontSize: 14 },
  link: { fontSize: 14, marginTop: 8, fontWeight: "600" },
});
