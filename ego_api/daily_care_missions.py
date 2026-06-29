"""Monstrinhos — missões diárias (pool 20+ + 1 surpresa/dia)."""

from __future__ import annotations

import datetime
import hashlib
from typing import Any

MISSION_POOL: list[dict[str, str | int | bool]] = [
    {"key": "breathe", "label": "Respirar fundo 3 vezes", "emoji": "🌬️", "seeds_reward": 2, "kind": "breathe"},
    {"key": "water", "label": "Regar o jardim", "emoji": "💧", "seeds_reward": 2, "kind": "tap"},
    {"key": "gratitude", "label": "Agradecer algo bom hoje", "emoji": "🙏", "seeds_reward": 2, "kind": "tap"},
    {"key": "adventure", "label": "Buscar o monstrinho na aventura", "emoji": "🎒", "seeds_reward": 3, "kind": "adventure"},
    {"key": "stretch", "label": "Alongar o corpo 1 minuto", "emoji": "🤸", "seeds_reward": 2, "kind": "tap"},
    {"key": "smile", "label": "Sorrir de propósito", "emoji": "😊", "seeds_reward": 2, "kind": "tap"},
    {"key": "hydrate", "label": "Beber um copo d'água", "emoji": "🥤", "seeds_reward": 2, "kind": "tap"},
    {"key": "walk", "label": "Caminhar 2 minutos", "emoji": "🚶", "seeds_reward": 2, "kind": "tap"},
    {"key": "tidy", "label": "Arrumar um cantinho", "emoji": "🧹", "seeds_reward": 2, "kind": "tap"},
    {"key": "sun", "label": "Tomar um pouco de sol", "emoji": "☀️", "seeds_reward": 2, "kind": "tap"},
    {"key": "music", "label": "Ouvir uma música calma", "emoji": "🎵", "seeds_reward": 2, "kind": "tap"},
    {"key": "note", "label": "Anotar um pensamento", "emoji": "📝", "seeds_reward": 2, "kind": "tap"},
    {"key": "kind_self", "label": "Fazer algo gentil por você", "emoji": "💜", "seeds_reward": 2, "kind": "tap"},
    {"key": "pause", "label": "Pausar 1 minuto sem tela", "emoji": "⏸️", "seeds_reward": 2, "kind": "tap"},
    {"key": "plant", "label": "Cuidar de uma planta", "emoji": "🌿", "seeds_reward": 2, "kind": "tap"},
    {"key": "window", "label": "Abrir a janela", "emoji": "🪟", "seeds_reward": 2, "kind": "tap"},
    {"key": "snack", "label": "Lanche saudável", "emoji": "🍎", "seeds_reward": 2, "kind": "tap"},
    {"key": "calm_breath", "label": "Respiração calma", "emoji": "🧘", "seeds_reward": 2, "kind": "breathe"},
]

SURPRISE_POOL: list[dict[str, str | int | bool]] = [
    {"key": "surprise_wish", "label": "Surpresa: desejar bem a alguém", "emoji": "✨", "seeds_reward": 4, "kind": "tap", "surprise": True},
    {"key": "surprise_dance", "label": "Surpresa: dançar 30 segundos", "emoji": "💃", "seeds_reward": 4, "kind": "tap", "surprise": True},
    {"key": "surprise_photo", "label": "Surpresa: foto de algo bonito", "emoji": "📷", "seeds_reward": 4, "kind": "tap", "surprise": True},
    {"key": "surprise_hug", "label": "Surpresa: abraço em você mesmo", "emoji": "🤗", "seeds_reward": 4, "kind": "tap", "surprise": True},
    {"key": "surprise_joke", "label": "Surpresa: piada leve", "emoji": "😄", "seeds_reward": 4, "kind": "tap", "surprise": True},
    {"key": "surprise_sky", "label": "Surpresa: olhar o céu", "emoji": "☁️", "seeds_reward": 4, "kind": "tap", "surprise": True},
    {"key": "surprise_msg", "label": "Surpresa: mensagem gentil", "emoji": "💌", "seeds_reward": 4, "kind": "tap", "surprise": True},
    {"key": "surprise_eyes", "label": "Surpresa: descansar os olhos", "emoji": "👀", "seeds_reward": 4, "kind": "tap", "surprise": True},
]

REGULAR_PICK_COUNT = 3
_CATALOG = {str(m["key"]): m for m in MISSION_POOL + SURPRISE_POOL}
_BREATHE_KEYS = {str(m["key"]) for m in MISSION_POOL if str(m.get("kind")) == "breathe"}


def validate_mission_pool_size() -> None:
    total = len(MISSION_POOL) + len(SURPRISE_POOL)
    if len(MISSION_POOL) < 18:
        raise ValueError(f"pool missões precisa de 18+ regulares, tem {len(MISSION_POOL)}")
    if len(SURPRISE_POOL) < 1:
        raise ValueError("pool surpresa vazio")
    if total < 20:
        raise ValueError(f"pool total precisa de 20+, tem {total}")
    keys = [str(m["key"]) for m in MISSION_POOL + SURPRISE_POOL]
    if len(keys) != len(set(keys)):
        raise ValueError("ids duplicados no pool de missões")


def mission_by_key(key: str) -> dict[str, Any] | None:
    return _CATALOG.get((key or "").strip().lower()[:24])


def _ordinal(today: str) -> int:
    try:
        return datetime.datetime.strptime(today, "%Y-%m-%d").date().toordinal()
    except ValueError:
        return 0


def _rank_pool(pool: list[dict], today: str, salt: str) -> list[dict]:
    ordinal = _ordinal(today)
    return sorted(
        pool,
        key=lambda m: int(
            hashlib.md5(f"{salt}:{ordinal}:{m['key']}".encode()).hexdigest(),
            16,
        ),
    )


def _ensure_breathe_with_adventure(picked: list[dict]) -> list[dict]:
    keys = {str(m["key"]) for m in picked}
    if "adventure" not in keys:
        return picked
    if keys & _BREATHE_KEYS:
        return picked
    breathe = mission_by_key("breathe")
    if not breathe:
        return picked
    out = [m for m in picked if str(m["key"]) != "adventure"]
    out.append(dict(breathe))
    out.append(next(m for m in picked if str(m["key"]) == "adventure"))
    return out[:REGULAR_PICK_COUNT]


def daily_mission_defs(today: str) -> list[dict]:
    """3 regulares + 1 surpresa (determinístico por data)."""
    ranked = _rank_pool(MISSION_POOL, today, "reg")
    picked = ranked[:REGULAR_PICK_COUNT]
    picked = _ensure_breathe_with_adventure(picked)
    surprise_ranked = _rank_pool(SURPRISE_POOL, today, "surp")
    surprise = surprise_ranked[0] if surprise_ranked else None
    out = list(picked)
    if surprise:
        out.append(dict(surprise))
    return out


def daily_mission_keys(today: str) -> list[str]:
    return [str(m["key"]) for m in daily_mission_defs(today)]


def missions_differ_within_days(day_a: str, day_b: str) -> bool:
    return daily_mission_keys(day_a) != daily_mission_keys(day_b)


def _goals_done_map(raw: dict) -> dict[str, str]:
    gd = raw.get("goals_done")
    if not isinstance(gd, dict):
        gd = {}
    return {str(k): str(v) for k, v in gd.items() if str(k).strip()}


def sync_legacy_goal_flags(raw: dict, today: str) -> None:
    """Retrocompat com breathe_date / water_date / gratitude_date / adventure_collected."""
    gd = _goals_done_map(raw)
    if str(raw.get("breathe_date") or "") == today:
        gd.setdefault("breathe", today)
    if str(raw.get("water_date") or "") == today:
        gd.setdefault("water", today)
    if str(raw.get("gratitude_date") or "") == today:
        gd.setdefault("gratitude", today)
    if bool(raw.get("adventure_collected")) and str(raw.get("last_date") or "") == today:
        gd.setdefault("adventure", today)
    raw["goals_done"] = gd


def is_goal_done(raw: dict, today: str, key: str) -> bool:
    sync_legacy_goal_flags(raw, today)
    return _goals_done_map(raw).get(key) == today


def breathe_done_today(raw: dict, today: str) -> bool:
    sync_legacy_goal_flags(raw, today)
    if str(raw.get("breathe_date") or "") == today:
        return True
    gd = _goals_done_map(raw)
    return any(gd.get(k) == today for k in _BREATHE_KEYS)


def is_mission_allowed_today(raw: dict, today: str, key: str) -> bool:
    if key == "checkin":
        return False
    allowed = set(daily_mission_keys(today))
    return key in allowed


def apply_mission_complete(raw: dict, today: str, mission: dict) -> int:
    """Marca missão feita; devolve sementes ganhas."""
    key = str(mission["key"])
    gd = _goals_done_map(raw)
    if gd.get(key) == today:
        return 0
    reward = int(mission.get("seeds_reward") or 0)
    gd[key] = today
    raw["goals_done"] = gd
    kind = str(mission.get("kind") or "tap")
    if kind == "breathe":
        raw["breathe_date"] = today
    elif kind == "adventure":
        raw["adventure_collected"] = True
    elif key == "water":
        raw["water_date"] = today
    elif key == "gratitude":
        raw["gratitude_date"] = today
    return reward


def reset_daily_goals(raw: dict) -> None:
    raw["goals_done"] = {}
    raw["breathe_date"] = ""
    raw["water_date"] = ""
    raw["gratitude_date"] = ""
    raw["adventure_collected"] = False


def build_daily_goals(
    raw: dict,
    today: str,
    checked_today: bool,
    *,
    checkin_seeds: int,
) -> list[dict]:
    sync_legacy_goal_flags(raw, today)
    goals: list[dict] = [
        {
            "key": "checkin",
            "label": "Registrar seu humor",
            "emoji": "💜",
            "done": checked_today,
            "seeds_reward": checkin_seeds,
            "locked": False,
            "kind": "checkin",
            "surprise": False,
        }
    ]
    for mission in daily_mission_defs(today):
        key = str(mission["key"])
        kind = str(mission.get("kind") or "tap")
        done = is_goal_done(raw, today, key)
        goals.append(
            {
                "key": key,
                "label": str(mission["label"]),
                "emoji": str(mission["emoji"]),
                "done": done,
                "seeds_reward": int(mission.get("seeds_reward") or 0),
                "locked": not checked_today,
                "kind": kind,
                "surprise": bool(mission.get("surprise")),
            }
        )
    return goals


def has_adventure_today(today: str) -> bool:
    return "adventure" in daily_mission_keys(today)
