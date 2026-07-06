"""PAUSA EGO — técnicas anti-stress/ansiedade por plano + rotação diária."""

from __future__ import annotations

import hashlib
from typing import Any

from ego_api.plans import (
    PLAN_CONNECTION,
    PLAN_ESSENTIAL,
    PLAN_PREMIUM,
    PLAN_TOTAL,
    normalize_plan_tier,
)

TIER_RANK: dict[str, int] = {
    PLAN_ESSENTIAL: 0,
    PLAN_CONNECTION: 1,
    PLAN_PREMIUM: 2,
    PLAN_TOTAL: 3,
    "enterprise": 3,
}

MOOD_STRESS_KEYS = frozenset({"heavy", "anxious"})

EXERCISE_POOL: list[dict[str, Any]] = [
    {
        "key": "breath44",
        "tier": PLAN_ESSENTIAL,
        "emoji": "🌬️",
        "title": "Respiração 4–4",
        "subtitle": "Acalma o corpo em 1 minuto",
        "duration_seconds": 60,
        "mode": "breath",
        "breath_inhale": 4,
        "breath_exhale": 4,
        "tags": ["stress", "anxiety"],
    },
    {
        "key": "long_exh",
        "tier": PLAN_ESSENTIAL,
        "emoji": "💨",
        "title": "Expiração longa",
        "subtitle": "Solte o ar devagar — ativa o relaxamento",
        "duration_seconds": 60,
        "mode": "breath",
        "breath_inhale": 4,
        "breath_exhale": 6,
        "tags": ["stress", "anxiety"],
    },
    {
        "key": "phys_sigh",
        "tier": PLAN_ESSENTIAL,
        "emoji": "😮‍💨",
        "title": "Suspiro fisiológico",
        "subtitle": "Duas inspirações curtas + expiração longa",
        "duration_seconds": 45,
        "mode": "steps",
        "steps": [
            {"text": "Inspire pelo nariz.", "seconds": 2},
            {"text": "Inspire mais um pouco.", "seconds": 2},
            {"text": "Expire devagar pela boca.", "seconds": 6},
            {"text": "Repita o ciclo com calma.", "seconds": 4},
        ],
        "tags": ["anxiety"],
    },
    {
        "key": "shoulders",
        "tier": PLAN_ESSENTIAL,
        "emoji": "🫳",
        "title": "Soltar ombros",
        "subtitle": "Tensione 3s e deixe cair",
        "duration_seconds": 50,
        "mode": "steps",
        "steps": [
            {"text": "Suba os ombros até às orelhas.", "seconds": 3},
            {"text": "Segure a tensão…", "seconds": 3},
            {"text": "Solte tudo de uma vez.", "seconds": 4},
            {"text": "Mandíbula solta. Respire.", "seconds": 8},
        ],
        "tags": ["stress", "tension"],
    },
    {
        "key": "feet_floor",
        "tier": PLAN_ESSENTIAL,
        "emoji": "🦶",
        "title": "Pés no chão",
        "subtitle": "30s — sentado ou em pé, em qualquer lugar",
        "duration_seconds": 40,
        "mode": "steps",
        "steps": [
            {"text": "Sinta os pés apoiados.", "seconds": 8},
            {"text": "Pressione leve contra o chão.", "seconds": 8},
            {"text": "Solte. Você está aqui, agora.", "seconds": 10},
        ],
        "tags": ["anxiety", "stress"],
        "anywhere": True,
    },
    {
        "key": "pause1",
        "tier": PLAN_ESSENTIAL,
        "emoji": "⏸️",
        "title": "Pausa de 1 minuto",
        "subtitle": "Olhos abertos — casa, escritório ou fila",
        "duration_seconds": 60,
        "mode": "steps",
        "steps": [
            {"text": "Olhos abertos. Só observe.", "seconds": 10},
            {"text": "Ombros para baixo.", "seconds": 10},
            {"text": "Três respirações lentas.", "seconds": 20},
            {"text": "Volte ao que estava fazendo.", "seconds": 8},
        ],
        "tags": ["stress"],
        "anywhere": True,
    },
    {
        "key": "box_breath",
        "tier": PLAN_CONNECTION,
        "emoji": "⬜",
        "title": "Respiração quadrada",
        "subtitle": "4–4–4–4 para foco e calma",
        "duration_seconds": 96,
        "mode": "steps",
        "steps": [
            {"text": "Inspire 4 segundos.", "seconds": 4},
            {"text": "Segure 4 segundos.", "seconds": 4},
            {"text": "Expire 4 segundos.", "seconds": 4},
            {"text": "Pausa 4 segundos.", "seconds": 4},
        ],
        "tags": ["anxiety", "stress"],
    },
    {
        "key": "ground543",
        "tier": PLAN_CONNECTION,
        "emoji": "🌿",
        "title": "Ancoragem 5-4-3-2-1",
        "subtitle": "Volte ao presente com os sentidos",
        "duration_seconds": 90,
        "mode": "steps",
        "steps": [
            {"text": "5 coisas que você vê.", "seconds": 15},
            {"text": "4 coisas que pode tocar.", "seconds": 12},
            {"text": "3 sons ao redor.", "seconds": 12},
            {"text": "2 cheiros (ou memórias boas).", "seconds": 10},
            {"text": "1 coisa boa sobre você hoje.", "seconds": 10},
        ],
        "tags": ["anxiety"],
    },
    {
        "key": "sounds3",
        "tier": PLAN_CONNECTION,
        "emoji": "👂",
        "title": "Três sons agora",
        "subtitle": "Ouça sem julgar",
        "duration_seconds": 45,
        "mode": "steps",
        "steps": [
            {"text": "Feche os olhos ou baixe o olhar.", "seconds": 4},
            {"text": "Nomeie o 1.º som.", "seconds": 10},
            {"text": "Nomeie o 2.º som.", "seconds": 10},
            {"text": "Nomeie o 3.º som.", "seconds": 10},
        ],
        "tags": ["anxiety", "rumination"],
    },
    {
        "key": "colors3",
        "tier": PLAN_CONNECTION,
        "emoji": "🎨",
        "title": "Três cores ao redor",
        "subtitle": "Micro-pausa visual",
        "duration_seconds": 40,
        "mode": "steps",
        "steps": [
            {"text": "Olhe ao redor com calma.", "seconds": 4},
            {"text": "Encontre uma cor.", "seconds": 8},
            {"text": "Encontre outra cor.", "seconds": 8},
            {"text": "Mais uma cor — respire.", "seconds": 8},
        ],
        "tags": ["stress"],
    },
    {
        "key": "jaw_relax",
        "tier": PLAN_CONNECTION,
        "emoji": "😌",
        "title": "Mandíbula e pescoço",
        "subtitle": "Onde o stress costuma acumular",
        "duration_seconds": 55,
        "mode": "steps",
        "steps": [
            {"text": "Lingua no céu da boca, mandíbula solta.", "seconds": 8},
            {"text": "Incline a cabeça devagar à direita.", "seconds": 8},
            {"text": "Incline à esquerda.", "seconds": 8},
            {"text": "Ombros para baixo. Expire.", "seconds": 10},
        ],
        "tags": ["tension", "stress"],
    },
    {
        "key": "belly_br",
        "tier": PLAN_CONNECTION,
        "emoji": "🫁",
        "title": "Respiração abdominal",
        "subtitle": "Mão na barriga — sobe e desce",
        "duration_seconds": 70,
        "mode": "breath",
        "breath_inhale": 4,
        "breath_exhale": 5,
        "tags": ["stress", "anxiety"],
    },
    {
        "key": "worry_later",
        "tier": PLAN_PREMIUM,
        "emoji": "⏳",
        "title": "Preocupação depois",
        "subtitle": "Adie a ruminação com gentileza",
        "duration_seconds": 45,
        "mode": "steps",
        "steps": [
            {"text": "Note a preocupação — sem brigar.", "seconds": 8},
            {"text": "Diga: «Vou pensar nisto às 20h.»", "seconds": 10},
            {"text": "Volte ao corpo — pés no chão.", "seconds": 10},
            {"text": "Uma expiração longa.", "seconds": 6},
        ],
        "tags": ["rumination", "anxiety"],
    },
    {
        "key": "compassion",
        "tier": PLAN_PREMIUM,
        "emoji": "💜",
        "title": "Autocompaixão",
        "subtitle": "Uma frase para você hoje",
        "duration_seconds": 40,
        "mode": "steps",
        "steps": [
            {"text": "Mão no peito, se quiser.", "seconds": 5},
            {"text": "«Estou fazendo o meu melhor hoje.»", "seconds": 12},
            {"text": "«Posso ser gentil comigo.»", "seconds": 12},
            {"text": "Respire e solte.", "seconds": 6},
        ],
        "tags": ["stress", "anxiety"],
    },
    {
        "key": "control1",
        "tier": PLAN_PREMIUM,
        "emoji": "🎯",
        "title": "O que posso controlar",
        "subtitle": "Uma ação pequena agora",
        "duration_seconds": 50,
        "mode": "steps",
        "steps": [
            {"text": "O que está fora do seu controle?", "seconds": 8},
            {"text": "Solte com uma expiração.", "seconds": 6},
            {"text": "Uma coisa pequena que pode fazer agora?", "seconds": 12},
            {"text": "Comprometa-se só com isso.", "seconds": 8},
        ],
        "tags": ["anxiety", "rumination"],
    },
    {
        "key": "hand_press",
        "tier": PLAN_PREMIUM,
        "emoji": "🤲",
        "title": "Pressão nas mãos",
        "subtitle": "Ancoragem táctil rápida",
        "duration_seconds": 40,
        "mode": "steps",
        "steps": [
            {"text": "Palmas pressionando uma na outra.", "seconds": 8},
            {"text": "Sinta a pressão — 5 segundos.", "seconds": 5},
            {"text": "Solte devagar.", "seconds": 6},
            {"text": "Repita mais uma vez.", "seconds": 10},
        ],
        "tags": ["anxiety"],
    },
    {
        "key": "feet_rel",
        "tier": PLAN_PREMIUM,
        "emoji": "🦶",
        "title": "Tensionar e soltar pés",
        "subtitle": "Relaxamento muscular rápido",
        "duration_seconds": 55,
        "mode": "steps",
        "steps": [
            {"text": "Pés no chão — sinta o apoio.", "seconds": 6},
            {"text": "Tensione os pés 5 segundos.", "seconds": 5},
            {"text": "Solte completamente.", "seconds": 8},
            {"text": "Suba para as pernas e solte.", "seconds": 10},
        ],
        "tags": ["tension", "stress"],
    },
    {
        "key": "pace4",
        "tier": PLAN_PREMIUM,
        "emoji": "🚶",
        "title": "Quatro passos + respiração",
        "subtitle": "Corpo e mente juntos",
        "duration_seconds": 60,
        "mode": "steps",
        "steps": [
            {"text": "4 passos inspirando.", "seconds": 8},
            {"text": "4 passos expirando.", "seconds": 8},
            {"text": "Repita no lugar se estiver sentado.", "seconds": 10},
            {"text": "Ritmo lento — sem pressa.", "seconds": 10},
        ],
        "tags": ["stress"],
    },
    {
        "key": "mood_link",
        "tier": PLAN_TOTAL,
        "emoji": "🎭",
        "title": "Pausa do seu humor",
        "subtitle": "Ligada ao Monstrinhos de hoje",
        "duration_seconds": 60,
        "mode": "steps",
        "steps": [
            {"text": "Como você marcou o humor hoje?", "seconds": 8},
            {"text": "Valide sem julgar — «faz sentido». ", "seconds": 10},
            {"text": "O que o corpo precisa agora?", "seconds": 10},
            {"text": "Uma expiração longa com isso.", "seconds": 8},
        ],
        "tags": ["anxiety", "stress"],
        "mood_linked": True,
    },
    {
        "key": "avatar_1",
        "tier": PLAN_TOTAL,
        "emoji": "✨",
        "title": "Frase do avatar",
        "subtitle": "Presença guiada personalizada",
        "duration_seconds": 55,
        "mode": "steps",
        "steps": [
            {"text": "Seu avatar está aqui com você.", "seconds": 6},
            {"text": "«Você não precisa resolver tudo agora.»", "seconds": 12},
            {"text": "«Só este minuto — só esta respiração.»", "seconds": 12},
            {"text": "Solte os ombros. Ficou um pouco mais leve?", "seconds": 10},
        ],
        "tags": ["anxiety", "stress"],
    },
]

_EXERCISE_BY_KEY = {str(e["key"]): e for e in EXERCISE_POOL}

PLAN_BENEFITS: dict[str, dict[str, Any]] = {
    PLAN_ESSENTIAL: {
        "plan_label": "Essencial",
        "headline": "1 PAUSA/dia · 6 técnicas · em qualquer lugar",
        "detail": "1 minuto em casa, no escritório, no ônibus ou na fila. Técnica nova quase todo dia.",
        "techniques_unlocked": 6,
        "upgrade_tier": PLAN_CONNECTION,
        "upgrade_hint": "Conexão: 12 técnicas + grounding e ancoragem.",
    },
    PLAN_CONNECTION: {
        "plan_label": "Conexão",
        "headline": "12 técnicas · pausa onde estiver",
        "detail": "Grounding e respiração — casa, escritório, transporte. Sem tapete nem silêncio.",
        "techniques_unlocked": 12,
        "upgrade_tier": PLAN_PREMIUM,
        "upgrade_hint": "Premium adapta ao humor (Monstrinhos) e traz 18 técnicas.",
    },
    PLAN_PREMIUM: {
        "plan_label": "Premium",
        "headline": "18 técnicas · pausa inteligente",
        "detail": "Agita ou Nublina? Priorizamos a técnica certa para hoje.",
        "techniques_unlocked": 18,
        "upgrade_tier": PLAN_TOTAL,
        "upgrade_hint": "Total: 20 técnicas + pausa personalizada com avatar.",
    },
    PLAN_TOTAL: {
        "plan_label": "Total",
        "headline": "20 técnicas · pausa completa",
        "detail": "Tudo desbloqueado + humor Monstrinhos + frase do avatar.",
        "techniques_unlocked": 20,
        "upgrade_tier": None,
        "upgrade_hint": "",
    },
}

ANYWHERE_LINE = "1 min · casa, escritório, ônibus ou fila — olhos abertos, sentado ou em pé"


def exercise_catalog_size() -> int:
    return len(EXERCISE_POOL)


def exercises_for_tier(tier: str | None) -> list[dict[str, Any]]:
    """Todas as técnicas PAUSA — sem bloqueio por plano."""
    del tier
    return list(EXERCISE_POOL)


def plan_benefits_payload(tier: str | None) -> dict[str, Any]:
    total = len(EXERCISE_POOL)
    return {
        "plan_tier": normalize_plan_tier(tier),
        "plan_label": "PAUSA EGO",
        "headline": f"{total} técnicas · pausa completa para todos",
        "detail": "1 minuto em qualquer lugar — técnica nova quase todo dia. Grátis no Essencial.",
        "techniques_unlocked": total,
        "techniques_total": total,
        "upgrade_tier": None,
        "upgrade_hint": "",
    }


def _serialize_exercise(raw: dict[str, Any], *, mood_boosted: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "key": raw["key"],
        "emoji": raw["emoji"],
        "title": raw["title"],
        "subtitle": raw["subtitle"],
        "duration_seconds": int(raw.get("duration_seconds") or 60),
        "mode": raw.get("mode") or "breath",
        "focus": (raw.get("tags") or ["stress"])[0],
        "mood_boosted": mood_boosted,
        "anywhere_friendly": raw.get("anywhere", True) is not False,
    }
    if out["mode"] == "breath":
        out["breath_inhale"] = int(raw.get("breath_inhale") or 4)
        out["breath_exhale"] = int(raw.get("breath_exhale") or 4)
    else:
        steps = raw.get("steps") or []
        out["steps"] = [
            {"text": str(s.get("text") or ""), "seconds": max(3, int(s.get("seconds") or 8))}
            for s in steps
            if isinstance(s, dict)
        ]
    return out


def pick_daily_exercise(
    *,
    user_id: str,
    local_date: str,
    tier: str | None,
    mood_key: str | None = None,
    avoid_key: str | None = None,
) -> dict[str, Any]:
    eligible = exercises_for_tier(tier)
    if not eligible:
        eligible = [EXERCISE_POOL[0]]

    tier_norm = normalize_plan_tier(tier)
    mood_boosted = False
    mood = str(mood_key or "").strip().lower()

    if mood in MOOD_STRESS_KEYS:
        tagged = [e for e in eligible if "anxiety" in (e.get("tags") or [])]
        if tagged:
            eligible = tagged
            mood_boosted = True

        mood_linked = [e for e in eligible if e.get("mood_linked")]
        if mood_linked:
            eligible = mood_linked
            mood_boosted = True

    if avoid_key and len(eligible) > 1:
        filtered = [e for e in eligible if str(e.get("key")) != avoid_key]
        if filtered:
            eligible = filtered

    digest = hashlib.sha256(f"{user_id}:{local_date}".encode()).hexdigest()
    idx = int(digest[:8], 16) % len(eligible)
    return _serialize_exercise(eligible[idx], mood_boosted=mood_boosted)


def pick_tomorrow_teaser(
    *,
    user_id: str,
    local_date: str,
    tier: str | None,
    mood_key: str | None = None,
    today_key: str | None = None,
) -> dict[str, str]:
    """Gancho de retenção — amanhã vem outra técnica."""
    import datetime as dt

    try:
        day = dt.datetime.strptime(local_date, "%Y-%m-%d").date()
        tomorrow = (day + dt.timedelta(days=1)).isoformat()
    except ValueError:
        tomorrow = local_date
    nxt = pick_daily_exercise(
        user_id=user_id,
        local_date=tomorrow,
        tier=tier,
        mood_key=mood_key,
        avoid_key=today_key,
    )
    return {
        "emoji": str(nxt.get("emoji") or "🌬️"),
        "title": str(nxt.get("title") or "Nova técnica"),
    }


def get_exercise_by_key(key: str) -> dict[str, Any] | None:
    raw = _EXERCISE_BY_KEY.get(str(key or "").strip())
    if not raw:
        return None
    return _serialize_exercise(raw)


def is_valid_session_kind(kind: str) -> bool:
    k = str(kind or "").strip()
    return k in _EXERCISE_BY_KEY or k in {"breath60", "breath120", "sos"}
