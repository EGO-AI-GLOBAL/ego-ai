"""Catálogo de avatares e vozes — fase 1 (12 avatares)."""

from __future__ import annotations

from ego_api.avatar_catalog import (
    AVATAR_CATALOG,
    CATALOG_AVATAR_IDS,
    CATALOG_VOICE_IDS,
    find_avatar,
    is_avatar_unlocked,
    plan_label_for_avatar,
    validate_avatar_choice,
)
from ego_api.plans import PLAN_ESSENTIAL

FEMALE_AVATAR_ID = "f1"
FEMALE_VOICE_ID = "vf1"
MALE_AVATAR_ID = "m1"
MALE_VOICE_ID = "vm1"

FREE_AVATAR_IDS = frozenset({FEMALE_AVATAR_ID, MALE_AVATAR_ID})
FREE_VOICE_IDS = frozenset({FEMALE_VOICE_ID, MALE_VOICE_ID})

PERSONA_PRESETS: list[dict] = [
    {
        "id": "female",
        "label": "Assistente feminina",
        "description": "Luna · voz Ana (PT-BR)",
        "avatar_id": FEMALE_AVATAR_ID,
        "voice_id": FEMALE_VOICE_ID,
    },
    {
        "id": "male",
        "label": "Assistente masculino",
        "description": "Leo · voz Bruno (PT-BR)",
        "avatar_id": MALE_AVATAR_ID,
        "voice_id": MALE_VOICE_ID,
    },
]

EDGE_TTS_FEMALE_IDS = frozenset({f"vf{i}" for i in range(1, 11)} | {"pvf1", "vg1", "vg2"})
EDGE_TTS_MALE_IDS = frozenset({f"vm{i}" for i in range(1, 11)} | {"pvm1"})


def is_male_avatar(avatar_id: str | None) -> bool:
    aid = (avatar_id or "").strip().lower()
    return aid.startswith("m") or aid.startswith("pm")


def is_neutral_avatar(avatar_id: str | None) -> bool:
    return (avatar_id or "").strip().lower().startswith("g")


def default_voice_for_avatar(avatar_id: str | None) -> str:
    entry = find_avatar(avatar_id)
    if entry:
        return entry["voice_id"]
    if is_male_avatar(avatar_id):
        return MALE_VOICE_ID
    return FEMALE_VOICE_ID


def normalize_persona_pair(avatar_id: str, voice_id: str | None = None) -> tuple[str, str]:
    """Par coerente; aceita os 12 ids do catálogo."""
    entry = find_avatar(avatar_id)
    if not entry:
        return FEMALE_AVATAR_ID, FEMALE_VOICE_ID

    aid = entry["avatar_id"]
    expected = entry["voice_id"]
    vid = (voice_id or "").strip().lower()[:32]

    if not vid:
        return aid, expected

    if is_neutral_avatar(aid):
        if vid.startswith("vg") and vid in CATALOG_VOICE_IDS:
            return aid, vid
        return aid, expected

    male_avatar = is_male_avatar(aid)
    male_voice = vid.startswith("vm") or vid.startswith("pvm")
    if male_avatar != male_voice:
        return aid, expected

    if vid in CATALOG_VOICE_IDS:
        return aid, vid
    return aid, expected


def resolve_tts_voice(voice_id: str | None = None, avatar_id: str | None = None) -> str:
    """Resolve voz TTS; sem avatar_id, voice_id do catálogo é aceite (ex.: vm1)."""
    vid = (voice_id or "").strip().lower()[:32]
    aid = (avatar_id or "").strip().lower()[:32]
    if aid:
        _, resolved = normalize_persona_pair(aid, vid or None)
        return resolved
    if vid in CATALOG_VOICE_IDS:
        return vid
    _, resolved = normalize_persona_pair(FEMALE_AVATAR_ID, vid or None)
    return resolved


def assistant_display_name_for_avatar(avatar_id: str | None) -> str:
    """Nome exibido e usado pela IA (Leo, Luna, Aisha, …)."""
    entry = find_avatar(avatar_id)
    if entry:
        return str(entry.get("short_name") or "EGO-AI").strip() or "EGO-AI"
    if is_male_avatar(avatar_id):
        return "Leo"
    if is_neutral_avatar(avatar_id):
        return "Alex"
    return "Luna"


def apply_assistant_name_from_avatar(avatar_id: str | None) -> str:
    """Atualiza a sessão Flask com o nome do avatar ativo."""
    from ego_api.request_ctx import get_session

    name = assistant_display_name_for_avatar(avatar_id)
    sess = get_session()
    if sess:
        sess.assistant_name = name
    return name


def persona_options_payload() -> dict:
    return {
        "presets": PERSONA_PRESETS,
        "avatars": [
            {
                "id": a["avatar_id"],
                "name": a["short_name"],
                "category": a["category"],
                "collection": a["collection"],
                "min_plan": a["min_plan"],
                "voice_id": a["voice_id"],
            }
            for a in AVATAR_CATALOG
        ],
        "catalog": AVATAR_CATALOG,
        "free_avatar_ids": sorted(FREE_AVATAR_IDS),
        "free_voice_ids": sorted(FREE_VOICE_IDS),
        "all_avatar_ids": sorted(CATALOG_AVATAR_IDS),
    }


__all__ = [
    "validate_avatar_choice",
    "is_avatar_unlocked",
    "plan_label_for_avatar",
    "find_avatar",
    "persona_options_payload",
    "normalize_persona_pair",
    "resolve_tts_voice",
    "assistant_display_name_for_avatar",
    "apply_assistant_name_from_avatar",
]
