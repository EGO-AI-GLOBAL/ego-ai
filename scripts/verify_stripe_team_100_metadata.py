#!/usr/bin/env python3
"""Verifica metadados team_seats=100 nos Payment Links Stripe (planos equipe)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ego_api.team_stripe_checkout import (  # noqa: E402
    TEAM_STRIPE_URLS_BR,
    TEAM_STRIPE_URLS_INT,
)

EXPECTED_100 = {
    ("br", "connection"): TEAM_STRIPE_URLS_BR["connection"][100],
    ("br", "premium"): TEAM_STRIPE_URLS_BR["premium"][100],
    ("br", "total"): TEAM_STRIPE_URLS_BR["total"][100],
    ("int", "connection"): TEAM_STRIPE_URLS_INT["connection"][100],
    ("int", "premium"): TEAM_STRIPE_URLS_INT["premium"][100],
    ("int", "total"): TEAM_STRIPE_URLS_INT["total"][100],
}


def _load_stripe_key() -> str:
    key = (os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY") or "").strip()
    if key:
        return key
    candidates = (
        ROOT / ".env",
        ROOT / "app" / ".env",
        ROOT / ".streamlit" / "secrets.toml",
    )
    for path in candidates:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if path.suffix == ".toml":
                if line.startswith("STRIPE_SECRET_KEY"):
                    _, _, v = line.partition("=")
                    return v.strip().strip('"').strip("'")
                continue
            if line.startswith("STRIPE_SECRET_KEY=") or line.startswith("STRIPE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    key = _load_stripe_key()
    if not key:
        print("STRIPE_SECRET_KEY nao encontrada (.env ou variavel de ambiente).")
        print("\nLinks de 100 lugares no codigo (confira manualmente no Stripe Dashboard):")
        for (market, tier), url in EXPECTED_100.items():
            print(f"  [{market}/{tier}] {url}")
        print(
            "\nEm cada link: Settings -> Metadata -> team_seats=100, plan_tier=..., plan_type=team"
        )
        return 2

    try:
        import stripe
    except ImportError:
        print("Instale: pip install stripe")
        return 1

    stripe.api_key = key
    print("A listar Payment Links Stripe...\n")

    url_to_link: dict[str, dict] = {}
    starting_after = None
    while True:
        params: dict = {"limit": 100, "active": True}
        if starting_after:
            params["starting_after"] = starting_after
        page = stripe.PaymentLink.list(**params)
        for pl in page.data:
            pl_url = str(getattr(pl, "url", "") or "")
            if pl_url:
                url_to_link[pl_url.rstrip("/")] = {
                    "id": pl.id,
                    "metadata": dict(getattr(pl, "metadata", None) or {}),
                    "active": bool(getattr(pl, "active", False)),
                }
        if not page.has_more:
            break
        starting_after = page.data[-1].id

    ok = 0
    missing = 0
    not_found = 0

    for (market, tier), expected_url in EXPECTED_100.items():
        norm = expected_url.rstrip("/")
        label = f"{market}/{tier} (100 lugares)"
        row = url_to_link.get(norm)
        if not row:
            print(f"  ? {label}: link nao encontrado na conta Stripe")
            print(f"      URL esperada: {expected_url}")
            not_found += 1
            continue
        meta = row["metadata"]
        seats = meta.get("team_seats") or meta.get("seats") or meta.get("seat_count")
        tier_meta = meta.get("plan_tier") or meta.get("tier") or meta.get("plan")
        plan_type = meta.get("plan_type")
        seats_ok = str(seats).strip() == "100"
        tier_ok = (tier_meta or "").strip().lower() == tier
        type_ok = (plan_type or "").strip().lower() == "team"
        if seats_ok and tier_ok and type_ok:
            print(f"  OK {label}: team_seats=100, plan_tier={tier}, plan_type=team")
            ok += 1
        else:
            print(f"  !! {label}: metadados incompletos")
            print(f"      id={row['id']}")
            print(f"      metadata={meta}")
            print(f"      esperado: team_seats=100, plan_tier={tier}, plan_type=team")
            missing += 1

    print(f"\nResumo: {ok} OK, {missing} incompletos, {not_found} nao encontrados.")
    return 0 if missing == 0 and not_found == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
