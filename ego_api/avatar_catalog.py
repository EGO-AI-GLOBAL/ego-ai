"""Catálogo fase 1: 12 avatares com desbloqueio por plano."""

from __future__ import annotations

from ego_api.plans import (
    PLAN_CONNECTION,
    PLAN_ESSENTIAL,
    PLAN_PREMIUM,
    PLAN_TOTAL,
    normalize_plan_tier,
)

TIER_RANK = {
    PLAN_ESSENTIAL: 0,
    PLAN_CONNECTION: 1,
    PLAN_PREMIUM: 2,
    PLAN_TOTAL: 3,
}

PLAN_LABELS_PT = {
    PLAN_ESSENTIAL: "Grátis",
    PLAN_CONNECTION: "Plano Conexão",
    PLAN_PREMIUM: "Plano Premium",
    PLAN_TOTAL: "Plano Total",
}

AVATAR_CATALOG: list[dict] = [
    {"id": "f1", "short_name": "Luna", "avatar_id": "f1", "voice_id": "vf1", "category": "female", "collection": "calm", "min_plan": PLAN_ESSENTIAL},
    {"id": "m1", "short_name": "Leo", "avatar_id": "m1", "voice_id": "vm1", "category": "male", "collection": "professional", "min_plan": PLAN_ESSENTIAL},
    {"id": "f2", "short_name": "Aisha", "avatar_id": "f2", "voice_id": "vf2", "category": "female", "collection": "professional", "min_plan": PLAN_CONNECTION},
    {"id": "f3", "short_name": "Hana", "avatar_id": "f3", "voice_id": "vf3", "category": "female", "collection": "young", "min_plan": PLAN_CONNECTION},
    {"id": "m2", "short_name": "Kai", "avatar_id": "m2", "voice_id": "vm2", "category": "male", "collection": "energetic", "min_plan": PLAN_CONNECTION},
    {"id": "m3", "short_name": "Omar", "avatar_id": "m3", "voice_id": "vm3", "category": "male", "collection": "calm", "min_plan": PLAN_CONNECTION},
    {"id": "f4", "short_name": "Amara", "avatar_id": "f4", "voice_id": "vf4", "category": "female", "collection": "calm", "min_plan": PLAN_PREMIUM},
    {"id": "m4", "short_name": "Ravi", "avatar_id": "m4", "voice_id": "vm4", "category": "male", "collection": "professional", "min_plan": PLAN_PREMIUM},
    {"id": "g1", "short_name": "Alex", "avatar_id": "g1", "voice_id": "vg1", "category": "neutral", "collection": "young", "min_plan": PLAN_PREMIUM},
    {"id": "f5", "short_name": "Sara", "avatar_id": "f5", "voice_id": "vf5", "category": "female", "collection": "professional", "min_plan": PLAN_TOTAL},
    {"id": "m5", "short_name": "Malik", "avatar_id": "m5", "voice_id": "vm5", "category": "male", "collection": "energetic", "min_plan": PLAN_TOTAL},
    {"id": "g2", "short_name": "Jordan", "avatar_id": "g2", "voice_id": "vg2", "category": "neutral", "collection": "calm", "min_plan": PLAN_TOTAL},
]

CATALOG_AVATAR_IDS = frozenset(a["avatar_id"] for a in AVATAR_CATALOG)
CATALOG_VOICE_IDS = frozenset(a["voice_id"] for a in AVATAR_CATALOG)


def find_avatar(avatar_id: str | None) -> dict | None:
    aid = (avatar_id or "").strip().lower()[:32]
    return next((a for a in AVATAR_CATALOG if a["avatar_id"] == aid), None)


def plan_label_for_avatar(min_plan: str) -> str:
    return PLAN_LABELS_PT.get(normalize_plan_tier(min_plan), "Assinar")


def is_avatar_unlocked(user_tier: str | None, entry: dict) -> bool:
    u = normalize_plan_tier(user_tier)
    need = normalize_plan_tier(entry.get("min_plan"))
    return TIER_RANK.get(u, 0) >= TIER_RANK.get(need, 0)


def validate_avatar_choice(
    user_tier: str | None, avatar_id: str, voice_id: str | None = None
) -> tuple[str, str, str | None]:
    """
    Retorna (avatar_id, voice_id, erro).
    erro != None se avatar bloqueado ou id desconhecido.
    """
    entry = find_avatar(avatar_id)
    if not entry:
        return "f1", "vf1", "Avatar desconhecido."

    if not is_avatar_unlocked(user_tier, entry):
        label = plan_label_for_avatar(entry["min_plan"])
        return entry["avatar_id"], entry["voice_id"], f"Disponível no {label}."

    aid = entry["avatar_id"]
    vid = (voice_id or "").strip().lower()[:32] or entry["voice_id"]
    if vid not in CATALOG_VOICE_IDS:
        vid = entry["voice_id"]
    return aid, vid, None
