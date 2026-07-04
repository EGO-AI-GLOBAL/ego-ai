"""Monstrinhos Fase 10 — eventos sazonais (banner + bónus de sementes)."""

from __future__ import annotations

import datetime
from typing import Any

# (month,) → evento activo naquele mês (BR)
_MONTH_EVENTS: dict[tuple[int, ...], dict[str, Any]] = {
    (7, 8): {
        "key": "winter_calm",
        "emoji": "❄️",
        "title": "Festival Inverno Calma",
        "tagline": "Check-in + PAUSA = dobro de autocuidado",
        "bonus_seeds": 3,
        "decor_emoji": "🕯️",
    },
    (12, 1): {
        "key": "end_year_glow",
        "emoji": "✨",
        "title": "Brilho de Fim de Ano",
        "tagline": "Feche o ano cuidando do humor",
        "bonus_seeds": 5,
        "decor_emoji": "🎄",
    },
    (3, 4, 5): {
        "key": "spring_bloom",
        "emoji": "🌸",
        "title": "Primavera no Jardim",
        "tagline": "Novas decorações especiais na loja",
        "bonus_seeds": 3,
        "decor_emoji": "🌷",
    },
}


def get_active_event(*, month: int | None = None) -> dict[str, Any] | None:
    m = month if month is not None else datetime.datetime.now().month
    for months, event in _MONTH_EVENTS.items():
        if m in months:
            today = datetime.date.today()
            if m == 12:
                ends = datetime.date(today.year, 12, 31)
            elif m == 1 and 1 in months:
                ends = datetime.date(today.year, 1, 31)
            else:
                import calendar

                last = calendar.monthrange(today.year, m)[1]
                ends = datetime.date(today.year, m, last)
            return {
                **event,
                "ends_at": ends.isoformat(),
                "active": True,
            }
    return None
