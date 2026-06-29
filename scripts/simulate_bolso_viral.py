#!/usr/bin/env python3
"""Simulador viral EGO de Bolso — cenários de partilha e crescimento.

  python scripts/simulate_bolso_viral.py
  python scripts/simulate_bolso_viral.py --users 200 --weeks 8
"""
from __future__ import annotations

import argparse


SCENARIOS: dict[str, dict[str, float]] = {
    "pessimista": {
        "share_rate": 0.08,
        "invite_click": 0.12,
        "install_rate": 0.35,
        "retention_d7": 0.18,
    },
    "base": {
        "share_rate": 0.18,
        "invite_click": 0.22,
        "install_rate": 0.45,
        "retention_d7": 0.28,
    },
    "otimista": {
        "share_rate": 0.32,
        "invite_click": 0.35,
        "install_rate": 0.55,
        "retention_d7": 0.38,
    },
}


def simulate_week(
    active_users: int,
    *,
    share_rate: float,
    invite_click: float,
    install_rate: float,
    retention_d7: float,
) -> tuple[int, int, int]:
    shares = int(active_users * share_rate)
    clicks = int(shares * invite_click * 3)  # ~3 contactos por partilha
    installs = int(clicks * install_rate)
    retained = int(installs * retention_d7)
    return shares, installs, retained


def run_scenario(name: str, params: dict[str, float], users: int, weeks: int) -> None:
    print(f"\n=== {name.upper()} ===")
    print(
        f"share={params['share_rate']:.0%} · click={params['invite_click']:.0%} · "
        f"install={params['install_rate']:.0%} · D7={params['retention_d7']:.0%}"
    )
    active = users
    total_installs = 0
    total_retained = 0
    for w in range(1, weeks + 1):
        shares, installs, retained = simulate_week(active, **params)
        total_installs += installs
        total_retained += retained
        active = max(users, active + retained)
        print(
            f"  Semana {w}: activos={active:4d} · partilhas={shares:3d} · "
            f"instalações={installs:3d} · retidos D7={retained:3d}"
        )
    k_factor = (total_installs / max(1, users * weeks)) * (
        params["retention_d7"] / max(params["share_rate"], 0.01)
    )
    print(
        f"  TOTAL: +{total_installs} instalacoes · +{total_retained} retidos D7 · K~{k_factor:.2f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulador viral EGO de Bolso")
    parser.add_argument("--users", type=int, default=120, help="Utilizadores activos iniciais")
    parser.add_argument("--weeks", type=int, default=6, help="Semanas a simular")
    args = parser.parse_args()

    print("EGO de Bolso — simulador viral (partilha + links WA/IG)")
    print(f"Base: {args.users} utilizadores · {args.weeks} semanas")
    print("Ver cenários: marketing/BOLSO-VIRAL-CENARIOS.md")

    for name, params in SCENARIOS.items():
        run_scenario(name, params, args.users, args.weeks)

    print("\nOK — use o cenário BASE para metas internas; OTIMISTA só com Reels + testadores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
