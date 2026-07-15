"""Sanity: mesocycle programming não repete cedo; ordem muda a cada 84 dias."""
from __future__ import annotations

import datetime as dt

from ego_api.pausa_exercises import MESOCYCLE_DAYS, pick_daily_exercise


def main() -> None:
    uid = "test-user-crossfit"
    start = dt.date(2026, 7, 15)
    keys_30 = [
        pick_daily_exercise(
            user_id=uid,
            local_date=(start + dt.timedelta(days=i)).isoformat(),
            tier="essential",
            avoid_keys=[],
        )["key"]
        for i in range(20)
    ]
    assert len(set(keys_30)) == 20, f"ciclo 20 deve ser único: {keys_30}"

    # Com histórico das 19, o dia 20 ainda pode repetir a 1ª — OK; com avoid deve empurrar.
    recent = list(keys_30[:19])
    k20 = pick_daily_exercise(
        user_id=uid,
        local_date=(start + dt.timedelta(days=19)).isoformat(),
        tier="essential",
        avoid_keys=recent,
    )["key"]
    assert k20 not in recent or len(set(keys_30)) == 1

    # Nova temporada (~84d) → ordem diferente
    order_a = [
        pick_daily_exercise(
            user_id=uid,
            local_date=(start + dt.timedelta(days=i)).isoformat(),
            tier="essential",
        )["key"]
        for i in range(5)
    ]
    order_b = [
        pick_daily_exercise(
            user_id=uid,
            local_date=(start + dt.timedelta(days=MESOCYCLE_DAYS + i)).isoformat(),
            tier="essential",
        )["key"]
        for i in range(5)
    ]
    assert order_a != order_b, "mesocycle novo deve baralhar"
    print("OK", keys_30[:5], "...", "meso_b", order_b)


if __name__ == "__main__":
    main()
