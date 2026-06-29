"""EGO de Bolso — estrelas e loja de cores do ovo."""

from __future__ import annotations

from typing import Any

from ego_api import db

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

DEFAULT_EGG_COLOR = "cosmic"
STARS_PER_MISSION = 1
STARS_DAILY_BONUS = 3

EGG_COLOR_ITEMS: list[dict[str, str | int]] = [
    {"id": "cosmic", "label": "Cósmico", "emoji": "🌌", "price": 0},
    {"id": "rose", "label": "Rosa", "emoji": "🌸", "price": 5},
    {"id": "emerald", "label": "Esmeralda", "emoji": "💚", "price": 8},
    {"id": "gold", "label": "Dourado", "emoji": "✨", "price": 10},
    {"id": "sunset", "label": "Pôr do sol", "emoji": "🌅", "price": 12},
]

_CATALOG = {str(i["id"]): i for i in EGG_COLOR_ITEMS}


def _safe_int(raw: object, default: int = 0) -> int:
    try:
        return int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def normalize_egg_color(raw: object) -> str:
    cid = str(raw or DEFAULT_EGG_COLOR).strip().lower()[:24]
    return cid if cid in _CATALOG else DEFAULT_EGG_COLOR


def normalize_owned(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return [DEFAULT_EGG_COLOR]
    owned = [normalize_egg_color(x) for x in raw if str(x or "").strip()]
    if DEFAULT_EGG_COLOR not in owned:
        owned.insert(0, DEFAULT_EGG_COLOR)
    out: list[str] = []
    for cid in owned:
        if cid not in out:
            out.append(cid)
    return out or [DEFAULT_EGG_COLOR]


def read_shop_fields(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "stars": max(0, _safe_int(raw.get("stars"), 0)),
        "egg_color": normalize_egg_color(raw.get("egg_color")),
        "egg_colors_owned": normalize_owned(raw.get("egg_colors_owned")),
        "stars_bonus_date": str(raw.get("stars_bonus_date") or "").strip()[:10],
    }


def write_shop_fields(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "stars": max(0, int(state.get("stars") or 0)),
        "egg_color": normalize_egg_color(state.get("egg_color")),
        "egg_colors_owned": normalize_owned(state.get("egg_colors_owned")),
        "stars_bonus_date": str(state.get("stars_bonus_date") or "").strip()[:10],
    }


def merge_shop_into_state(state: dict[str, Any], raw: dict[str, Any]) -> None:
    shop = read_shop_fields(raw)
    state.update(shop)


def shop_catalog(state: dict[str, Any]) -> list[dict[str, Any]]:
    stars = max(0, int(state.get("stars") or 0))
    owned = normalize_owned(state.get("egg_colors_owned"))
    active = normalize_egg_color(state.get("egg_color"))
    out: list[dict[str, Any]] = []
    for item in EGG_COLOR_ITEMS:
        iid = str(item["id"])
        price = int(item["price"])
        is_owned = iid in owned
        out.append(
            {
                "id": iid,
                "label": str(item["label"]),
                "emoji": str(item["emoji"]),
                "price": price,
                "owned": is_owned,
                "active": iid == active,
                "can_afford": is_owned or stars >= price,
            }
        )
    return out


def award_mission_stars(state: dict[str, Any], *, missions_per_day: int) -> None:
    """+1 por missão; bónus ao completar o dia."""
    from ego_api.streaks import _local_date_str

    today = _local_date_str()
    state["stars"] = max(0, int(state.get("stars") or 0)) + STARS_PER_MISSION
    count = int(state.get("missions_today_count") or 0)
    if count >= missions_per_day and str(state.get("stars_bonus_date") or "") != today:
        state["stars"] = int(state.get("stars") or 0) + STARS_DAILY_BONUS
        state["stars_bonus_date"] = today


def purchase_egg_color(
    supabase: Client | None,
    user_id: str,
    color_id: str,
    *,
    plan_tier: str = "essential",
) -> dict[str, Any]:
    from ego_api import wellness_journey

    if not supabase or not user_id:
        return wellness_journey.get_journey(supabase, user_id, plan_tier=plan_tier)

    cid = normalize_egg_color(color_id)
    item = _CATALOG.get(cid)
    if not item:
        return wellness_journey.get_journey(supabase, user_id, plan_tier=plan_tier)

    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = ui.get("wellness_journey")
    if not isinstance(raw, dict):
        raw = {}

    shop = read_shop_fields(raw)
    owned = list(shop["egg_colors_owned"])
    stars = int(shop["stars"])
    price = int(item["price"])

    if cid in owned:
        shop["egg_color"] = cid
    elif stars >= price:
        shop["stars"] = stars - price
        if cid not in owned:
            owned.append(cid)
        shop["egg_colors_owned"] = owned
        shop["egg_color"] = cid
    else:
        return wellness_journey.get_journey(supabase, user_id, plan_tier=plan_tier)

    raw.update(write_shop_fields(shop))
    ui["wellness_journey"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})
    return wellness_journey.get_journey(supabase, user_id, plan_tier=plan_tier)
