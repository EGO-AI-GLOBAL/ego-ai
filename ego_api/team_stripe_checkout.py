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
        10: "https://buy.stripe.com/bJeaEZ4zYcXw95K3904ow0a",
        20: "https://buy.stripe.com/dRmcN7d6ucXwgyc8tk4ow0b",
        30: "https://buy.stripe.com/00w7sNd6ue1A5TybFw4ow0c",
        40: "https://buy.stripe.com/dRm9AVeaycXw4Pu8tk4ow0d",
        50: "https://buy.stripe.com/fZu3cx3vUcXweq4aBs4ow0e",
        100: "https://buy.stripe.com/fZu00l0jI3mWdm0cJA4ow0f",
    },
    "premium": {
        10: "https://buy.stripe.com/8x26oJ5E2bTs6XCcJA4ow0g",
        20: "https://buy.stripe.com/fZu00lgiGg9I6XC3904ow0h",
        30: "https://buy.stripe.com/fZu8wRd6u9Lk2Hm5h84ow0i",
        40: "https://buy.stripe.com/3cI6oJ8Qe1eO6XC3904ow0j",
        50: "https://buy.stripe.com/8x28wRgiG2iSfu88tk4ow0k",
        100: "https://buy.stripe.com/6oUdRb7Mae1A95K7pg4ow0l",
    },
    "total": {
        10: "https://buy.stripe.com/3cI4gB9Ui6z84Pu4d44ow0m",
        20: "https://buy.stripe.com/bJe00l5E21eO6XCaBs4ow0n",
        30: "https://buy.stripe.com/fZueVf6I6g9Ieq44d44ow0o",
        40: "https://buy.stripe.com/28EcN75E25v43LqeRI4ow0p",
        50: "https://buy.stripe.com/bJebJ3giG4r04Pu3904ow0q",
        100: "https://buy.stripe.com/3cIdRb5E2f5E0ze10S4ow0r",
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
