import type { PlanTier } from "@/api/types";
import type { MonthlyMarket } from "@/constants/stripeMonthly";

export const TEAM_SEATS = [10, 20, 30, 40, 50, 100] as const;
export type TeamSeatCount = (typeof TEAM_SEATS)[number];

export type TeamPlanTier = Extract<PlanTier, "connection" | "premium" | "total">;

/** Fallback (espelha ego_api/team_stripe_checkout.py). */
export const TEAM_CHECKOUT_FALLBACK: Record<
  MonthlyMarket,
  Record<TeamPlanTier, Record<TeamSeatCount, string>>
> = {
  br: {
    connection: {
      10: "https://buy.stripe.com/dRmfZj6I6cXwdm05h84ow0T",
      20: "https://buy.stripe.com/aFa14peay6z8a9O3904ow0U",
      30: "https://buy.stripe.com/00w3cx2rQ0aK0ze3904ow0V",
      40: "https://buy.stripe.com/14A5kFeay4r081G6lc4ow0W",
      50: "https://buy.stripe.com/5kQaEZ7Ma6z81Di5h84ow0X",
      100: "https://buy.stripe.com/bJe4gB3vUbTs0ze8tk4ow0Y",
    },
    premium: {
      10: "https://buy.stripe.com/8x26oJ5E2bTs6XCcJA4ow0g",
      20: "https://buy.stripe.com/fZu00lgiGg9I6XC3904ow0h",
      30: "https://buy.stripe.com/fZu8wRd6u9Lk2Hm5h84ow0i",
      40: "https://buy.stripe.com/3cI6oJ8Qe1eO6XC3904ow0j",
      50: "https://buy.stripe.com/8x28wRgiG2iSfu88tk4ow0k",
      100: "https://buy.stripe.com/6oUdRb7Mae1A95K7pg4ow0l",
    },
    total: {
      10: "https://buy.stripe.com/3cI4gB9Ui6z84Pu4d44ow0m",
      20: "https://buy.stripe.com/bJe00l5E21eO6XCaBs4ow0n",
      30: "https://buy.stripe.com/fZueVf6I6g9Ieq44d44ow0o",
      40: "https://buy.stripe.com/28EcN75E25v43LqeRI4ow0p",
      50: "https://buy.stripe.com/bJebJ3giG4r04Pu3904ow0q",
      100: "https://buy.stripe.com/3cIdRb5E2f5E0ze10S4ow0r",
    },
  },
  int: {
    connection: {
      10: "https://buy.stripe.com/6oU8wR8Qe2iSdm0fVM4ow0s",
      20: "https://buy.stripe.com/28E6oJeay9Lk1DicJA4ow0t",
      30: "https://buy.stripe.com/eVq4gB7Ma6z8eq4gZQ4ow0u",
      40: "https://buy.stripe.com/6oU00l2rQ7Dcgyc4d44ow0v",
      50: "https://buy.stripe.com/4gMdRb8Qe1eO95K24W4ow0w",
      100: "https://buy.stripe.com/eVq00leayf5E3Lq4d44ow0x",
    },
    premium: {
      10: "https://buy.stripe.com/9B6bJ3feC1eOfu8eRI4ow0y",
      20: "https://buy.stripe.com/00wcN71nMg9IgycdNE4ow0z",
      30: "https://buy.stripe.com/9B6bJ3c2q8Hgeq4gZQ4ow0A",
      40: "https://buy.stripe.com/6oUcN7giGf5Eeq424W4ow0B",
      50: "https://buy.stripe.com/4gM28t7Ma3mW81GaBs4ow0C",
      100: "https://buy.stripe.com/28E28t9Uig9I0ze9xo4ow0D",
    },
    total: {
      10: "https://buy.stripe.com/aFabJ3d6u0aK81G24W4ow0E",
      20: "https://buy.stripe.com/6oU8wR8QebTsa9O3904ow0F",
      30: "https://buy.stripe.com/bJe3cx3vUf5E4PuaBs4ow0G",
      40: "https://buy.stripe.com/bJe3cxd6uaPo3LqcJA4ow0H",
      50: "https://buy.stripe.com/eVqeVf2rQf5Eeq4bFw4ow0I",
      100: "https://buy.stripe.com/eVq3cx4zY0aK95K4d44ow0J",
    },
  },
};

export const TEAM_PRICE_BRL: Record<TeamPlanTier, Record<TeamSeatCount, number>> = {
  connection: {
    10: 239.2,
    20: 478.4,
    30: 717.6,
    40: 956.8,
    50: 1196.0,
    100: 2392.0,
  },
  premium: {
    10: 399.2,
    20: 798.4,
    30: 1197.6,
    40: 1596.8,
    50: 1996.0,
    100: 3992.0,
  },
  total: {
    10: 799.2,
    20: 1598.4,
    30: 2397.6,
    40: 3196.8,
    50: 3996.0,
    100: 7992.0,
  },
};

export const TEAM_PRICE_USD: Record<TeamPlanTier, Record<TeamSeatCount, number>> = {
  connection: {
    10: 63.92,
    20: 127.84,
    30: 191.76,
    40: 255.68,
    50: 319.6,
    100: 639.2,
  },
  premium: {
    10: 119.92,
    20: 239.84,
    30: 359.76,
    40: 479.68,
    50: 599.6,
    100: 1199.2,
  },
  total: {
    10: 239.92,
    20: 479.84,
    30: 719.76,
    40: 959.68,
    50: 1199.6,
    100: 2399.2,
  },
};

const BR_NAMES: Record<TeamPlanTier, string> = {
  connection: "EGO Conexão Equipe",
  premium: "EGO Premium Equipe",
  total: "EGO Total Equipe",
};

const INT_NAMES: Record<TeamPlanTier, string> = {
  connection: "EGO AI Pro Team",
  premium: "EGO AI Premium Team",
  total: "EGO AI Complete Team",
};

function formatBrlTeam(price: number): string {
  const whole = Math.floor(price);
  const cents = Math.round((price - whole) * 100);
  const intStr = whole.toLocaleString("pt-BR");
  return `R$ ${intStr},${String(cents).padStart(2, "0")}/mês`;
}

function formatUsdTeam(price: number): string {
  return `US$ ${price.toFixed(2)}/month`;
}

export type TeamPlanOffer = {
  market: MonthlyMarket;
  tier: TeamPlanTier;
  seats: TeamSeatCount;
  label: string;
  tagline: string;
  displayPrice: string;
  priceNum: number;
};

export function buildTeamPlanOffers(): TeamPlanOffer[] {
  const tiers: TeamPlanTier[] = ["connection", "premium", "total"];
  const out: TeamPlanOffer[] = [];
  for (const market of ["br", "int"] as MonthlyMarket[]) {
    for (const tier of tiers) {
      for (const seats of TEAM_SEATS) {
        const priceNum =
          market === "br" ? TEAM_PRICE_BRL[tier][seats] : TEAM_PRICE_USD[tier][seats];
        const base = market === "br" ? BR_NAMES[tier] : INT_NAMES[tier];
        const people = market === "br" ? "pessoas" : "people";
        out.push({
          market,
          tier,
          seats,
          label: `${base} · ${seats} ${people}`,
          tagline:
            market === "br"
              ? "Agendas compartilhadas · 20% vs contas individuais"
              : "Shared calendars · save 20% vs individual",
          displayPrice:
            market === "br" ? formatBrlTeam(priceNum) : formatUsdTeam(priceNum),
          priceNum,
        });
      }
    }
  }
  return out;
}

export const TEAM_PLAN_OFFERS = buildTeamPlanOffers();
