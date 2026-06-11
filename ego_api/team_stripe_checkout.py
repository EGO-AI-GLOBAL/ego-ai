"""Links Stripe — planos Equipe (BR + internacional)."""

from __future__ import annotations

from typing import Literal

TeamMarket = Literal["br", "int"]
TeamTier = Literal["connection", "premium", "total"]
TeamSeats = Literal[10, 20, 30, 40, 50, 100]

TEAM_SEAT_VALUES: tuple[int, ...] = (10, 20, 30, 40, 50, 100)

# Brasil (R$)
TEAM_STRIPE_URLS_BR: dict[str, dict[int, str]] = {
    "connection": {
        10: "https://buy.stripe.com/dRmfZj6I6cXwdm05h84ow0T",
        20: "https://buy.stripe.com/aFa14peay6z8a9O3904ow0U",
        30: "https://buy.stripe.com/00w3cx2rQ0aK0ze3904ow0V",
        40: "https://buy.stripe.com/14A5kFeay4r081G6lc4ow0W",
        50: "https://buy.stripe.com/5kQaEZ7Ma6z81Di5h84ow0X",
        100: "https://buy.stripe.com/bJe4gB3vUbTs0ze8tk4ow0Y",
    },
    "premium": {
        10: "https://buy.stripe.com/14A8wRc2qf5Ea9O4d44ow0Z",
        20: "https://buy.stripe.com/7sY5kF4zY3mWgyceRI4ow10",
        30: "https://buy.stripe.com/14AbJ3aYm6z80zecJA4ow13",
        40: "https://buy.stripe.com/6oU9AVd6ucXw2Hm8tk4ow14",
        50: "https://buy.stripe.com/9B6dRb8Qe1eOchWgZQ4ow15",
        100: "https://buy.stripe.com/5kQ7sN1nMaPo1Di4d44ow16",
    },
    "total": {
        10: "https://buy.stripe.com/6oU5kF3vU0aK81GcJA4ow17",
        20: "https://buy.stripe.com/5kQaEZgiG8Hggyc4d44ow18",
        30: "https://buy.stripe.com/eVq5kFfeC7Dc3LqgZQ4ow19",
        40: "https://buy.stripe.com/cNibJ3feC6z85TydNE4ow1a",
        50: "https://buy.stripe.com/eVq7sNc2q6z84Pu5h84ow1b",
        100: "https://buy.stripe.com/28E00l3vU0aKdm05h84ow1c",
    },
}

# Internacional (USD)
TEAM_STRIPE_URLS_INT: dict[str, dict[int, str]] = {
    "connection": {
        10: "https://buy.stripe.com/6oU8wR8Qe2iSdm0fVM4ow0s",
        20: "https://buy.stripe.com/28E6oJeay9Lk1DicJA4ow0t",
        30: "https://buy.stripe.com/eVq4gB7Ma6z8eq4gZQ4ow0u",
        40: "https://buy.stripe.com/6oU00l2rQ7Dcgyc4d44ow0v",
        50: "https://buy.stripe.com/4gMdRb8Qe1eO95K24W4ow0w",
        100: "https://buy.stripe.com/eVq00leayf5E3Lq4d44ow0x",
    },
    "premium": {
        10: "https://buy.stripe.com/9B6bJ3feC1eOfu8eRI4ow0y",
        20: "https://buy.stripe.com/00wcN71nMg9IgycdNE4ow0z",
        30: "https://buy.stripe.com/9B6bJ3c2q8Hgeq4gZQ4ow0A",
        40: "https://buy.stripe.com/6oUcN7giGf5Eeq424W4ow0B",
        50: "https://buy.stripe.com/4gM28t7Ma3mW81GaBs4ow0C",
        100: "https://buy.stripe.com/28E28t9Uig9I0ze9xo4ow0D",
    },
    "total": {
        10: "https://buy.stripe.com/aFabJ3d6u0aK81G24W4ow0E",
        20: "https://buy.stripe.com/6oU8wR8QebTsa9O3904ow0F",
        30: "https://buy.stripe.com/bJe3cx3vUf5E4PuaBs4ow0G",
        40: "https://buy.stripe.com/bJe3cxd6uaPo3LqcJA4ow0H",
        50: "https://buy.stripe.com/eVqeVf2rQf5Eeq4bFw4ow0I",
        100: "https://buy.stripe.com/eVq3cx4zY0aK95K4d44ow0J",
    },
}


def team_checkout_url(market: str, tier: str, seats: int) -> str | None:
    m = (market or "br").strip().lower()
    t = (tier or "").strip().lower()
    try:
        n = int(seats)
    except (TypeError, ValueError):
        return None
    table = TEAM_STRIPE_URLS_BR if m == "br" else TEAM_STRIPE_URLS_INT
    return (table.get(t) or {}).get(n)


def team_checkout_nested() -> dict[str, dict[str, dict[str, str]]]:
    """Para API: { br: { connection: { '10': url } } }."""
    out: dict[str, dict[str, dict[str, str]]] = {"br": {}, "int": {}}
    for tier in ("connection", "premium", "total"):
        out["br"][tier] = {str(k): v for k, v in TEAM_STRIPE_URLS_BR[tier].items()}
        out["int"][tier] = {str(k): v for k, v in TEAM_STRIPE_URLS_INT[tier].items()}
    return out


def parse_team_seats(raw: object) -> int | None:
    if raw is None:
        return None
    try:
        n = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return n if n in TEAM_SEAT_VALUES else None
