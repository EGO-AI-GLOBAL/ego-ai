"""Ativação de plano no perfil Supabase (Stripe, Apple IAP, scripts admin)."""

from __future__ import annotations

import json

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

from ego_api.plans import PLAN_ESSENTIAL, normalize_plan_tier


def apply_plan_to_profile(
    supabase: Client,
    user_id: str,
    tier: str,
    *,
    team_seats: int | None = None,
) -> dict:
    tier = normalize_plan_tier(tier)
    paid = tier != PLAN_ESSENTIAL
    payload: dict = {"plan_tier": tier, "is_pro": paid}
    if team_seats:
        row = (
            supabase.table("profiles")
            .select("ui_state")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        ui: dict = {}
        if row.data:
            raw = row.data[0].get("ui_state")
            if isinstance(raw, dict):
                ui = dict(raw)
            elif isinstance(raw, str) and raw.strip():
                try:
                    ui = json.loads(raw)
                except json.JSONDecodeError:
                    ui = {}
        ui["team_seats"] = int(team_seats)
        ui["plan_type"] = "team"
        payload["ui_state"] = ui
    supabase.table("profiles").update(payload).eq("id", user_id).execute()
    return {"plan_tier": tier, "is_pro": paid, "team_seats": team_seats}
