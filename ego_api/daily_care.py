"""Desafio Diário de Cuidado — check-in de 1 toque (estilo puzzle diário viral)."""

from __future__ import annotations

import datetime

from ego_api import db
from ego_api import progression
from ego_api.request_ctx import get_session
from ego_api.schedule_tz import local_now_from_session

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

MOODS: list[dict[str, str]] = [
    {"key": "heavy", "emoji": "😰", "label": "Peso"},
    {"key": "anxious", "emoji": "😟", "label": "Ansiosa"},
    {"key": "ok", "emoji": "😐", "label": "Ok"},
    {"key": "good", "emoji": "🙂", "label": "Bem"},
    {"key": "calm", "emoji": "😌", "label": "Leve"},
]

DAILY_QUESTIONS: list[str] = [
    "Como está sua mente agora?",
    "Quanto a ansiedade apertou hoje?",
    "Como você dormiu?",
    "O que mais pesou na cabeça?",
    "De 0 a 10, quanto precisa desabafar?",
    "Como está seu corpo agora?",
    "O que você precisa hoje?",
    "Conseguiu respirar fundo hoje?",
    "Algo te preocupou demais?",
    "Como foi sua manhã?",
    "Você foi gentil consigo hoje?",
    "O que te acalmou hoje?",
    "Precisa organizar a cabeça?",
    "Como está sua energia?",
]


def _local_date_str() -> str:
    sess = get_session()
    if sess:
        loc = local_now_from_session(sess)
        if loc:
            return loc.strftime("%Y-%m-%d")
    return datetime.datetime.now().strftime("%Y-%m-%d")


def _yesterday(local_date: str) -> str:
    try:
        dt = datetime.datetime.strptime(local_date, "%Y-%m-%d").date()
        return (dt - datetime.timedelta(days=1)).isoformat()
    except ValueError:
        return ""


def question_for_today(local_date: str | None = None) -> dict:
    today = local_date or _local_date_str()
    try:
        dt = datetime.datetime.strptime(today, "%Y-%m-%d").date()
        idx = dt.toordinal() % len(DAILY_QUESTIONS)
    except ValueError:
        idx = 0
    return {
        "index": idx + 1,
        "total": len(DAILY_QUESTIONS),
        "text": DAILY_QUESTIONS[idx],
    }


def _mood_by_key(key: str) -> dict[str, str]:
    k = (key or "").strip().lower()
    for m in MOODS:
        if m["key"] == k:
            return m
    return MOODS[2]

# Marcos visíveis no ranking (1 → 3 → 7 → 14 → 30 dias).
CARE_MILESTONES: list[dict[str, str | int]] = [
    {"min_days": 1, "emoji": "🌱", "label": "Iniciante"},
    {"min_days": 3, "emoji": "💪", "label": "Firme"},
    {"min_days": 7, "emoji": "🔥", "label": "Forte"},
    {"min_days": 14, "emoji": "⭐", "label": "Mestre"},
    {"min_days": 30, "emoji": "👑", "label": "Lenda"},
]
# Retrocompat (regression_guard)
CARE_TIERS = CARE_MILESTONES


def _tier_for_days(days: int, cap: int) -> dict:
    tier = progression.daily_tier_from_days(days, cap)
    emoji, label = progression.daily_tier_meta(tier)
    next_tier = tier + 1 if tier < cap else None
    next_label = progression.daily_tier_meta(next_tier)[1] if next_tier else None
    return {
        "tier_index": tier,
        "tier_total": cap,
        "tier_emoji": emoji,
        "tier_label": label,
        "next_tier_days": next_tier,
        "next_tier_label": next_label,
    }


def _ranking_payload(
    supabase: Client | None, current: int, longest: int
) -> dict:
    cap = progression.get_cap(supabase, "daily_care")
    tier = _tier_for_days(current, cap)
    top = _community_top_days()
    next_days = tier.get("next_tier_days")
    days_to_next = (int(next_days) - current) if next_days else 0
    challenge = (
        f"Faltam {days_to_next} dia(s) para nível {tier.get('next_tier_label')}"
        if days_to_next > 0 and tier.get("next_tier_label")
        else (
            f"Você está no topo ({cap} níveis) — desafie alguém a chegar em {top} dias"
            if current >= cap
            else f"Meta da comunidade: {top} dias · escada até {cap} níveis"
        )
    )
    return {
        **tier,
        "personal_best": longest,
        "community_top_days": top,
        "days_to_next_tier": max(0, days_to_next),
        "challenge_line": challenge,
        "ladder": progression.daily_ladder_window(tier["tier_index"], cap),
        "milestones": [
            {
                "min_days": int(t["min_days"]),
                "emoji": str(t["emoji"]),
                "label": str(t["label"]),
                "reached": current >= int(t["min_days"]),
            }
            for t in CARE_MILESTONES
        ],
    }


def _community_top_days() -> int:
    from ego_api.config import read_env

    try:
        return max(7, int(read_env("EGO_DAILY_CARE_COMMUNITY_TOP", "21")))
    except ValueError:
        return 21


def _load_raw(supabase: Client | None, user_id: str) -> dict:
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = ui.get("daily_care")
    return dict(raw) if isinstance(raw, dict) else {}


def get_daily_care(supabase: Client | None, user_id: str) -> dict:
    today = _local_date_str()
    raw = _load_raw(supabase, user_id)
    last = str(raw.get("last_date") or "").strip()
    current = int(raw.get("current") or 0)
    longest = int(raw.get("longest") or 0)
    last_mood = str(raw.get("last_mood") or "")
    mood = _mood_by_key(last_mood) if last_mood else MOODS[2]
    checked_today = last == today
    q = question_for_today(today)
    longest_eff = max(longest, current)
    if longest_eff > 0:
        try:
            progression.maybe_expand_cap(supabase, "daily_care", longest_eff)
        except Exception:
            pass
    ranking = _ranking_payload(supabase, current, longest_eff)
    return {
        "current": current,
        "longest": longest_eff,
        "last_date": last,
        "checked_today": checked_today,
        "at_risk": bool(current >= 1 and not checked_today),
        "last_mood": last_mood,
        "last_mood_emoji": str(raw.get("last_mood_emoji") or mood["emoji"]),
        "last_mood_label": str(raw.get("last_mood_label") or mood["label"]),
        "total_checkins": int(raw.get("total_checkins") or 0),
        "question": q,
        "moods": MOODS,
        "can_share": checked_today,
        "share_hook": _share_hook(current, checked_today, ranking),
        "ranking": ranking,
    }


def _share_hook(current: int, checked_today: bool, ranking: dict) -> str:
    if not checked_today:
        return "Faça o check-in de hoje para subir no ranking."
    tier = f"{ranking.get('tier_emoji', '')} {ranking.get('tier_label', '')}".strip()
    if current <= 1:
        return f"Dia 1 — nível {tier}. Desafie alguém no Stories!"
    if ranking.get("days_to_next_tier", 0) > 0:
        return (
            f"{current} dias · {tier} — "
            f"faltam {ranking['days_to_next_tier']} para {ranking.get('next_tier_label')}."
        )
    return f"{current} dias · {tier} — você está no topo! Quem bate?"


def record_checkin(
    supabase: Client | None,
    user_id: str,
    mood_key: str,
) -> dict:
    if not supabase or not user_id:
        return get_daily_care(supabase, user_id)
    mood = _mood_by_key(mood_key)
    today = _local_date_str()
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = dict(ui.get("daily_care") if isinstance(ui.get("daily_care"), dict) else {})
    last = str(raw.get("last_date") or "").strip()
    current = int(raw.get("current") or 0)
    longest = int(raw.get("longest") or 0)
    total = int(raw.get("total_checkins") or 0)

    if last == today:
        raw.update(
            {
                "last_mood": mood["key"],
                "last_mood_emoji": mood["emoji"],
                "last_mood_label": mood["label"],
            }
        )
    else:
        yesterday = _yesterday(today)
        if last == yesterday and current > 0:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
        total += 1
        raw = {
            "current": current,
            "longest": longest,
            "last_date": today,
            "last_mood": mood["key"],
            "last_mood_emoji": mood["emoji"],
            "last_mood_label": mood["label"],
            "total_checkins": total,
        }

    ui["daily_care"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})

    try:
        progression.maybe_expand_cap(
            supabase, "daily_care", max(current, longest)
        )
    except Exception as exc:
        print(f"[EGO] daily_care expand cap error: {exc}", flush=True)

    try:
        from ego_api import streaks, wellness_journey

        streaks.record_streak_activity(supabase, user_id, source="checkin")
        prof2 = db.load_profile(supabase, user_id) or {}
        tier, _ = db.user_plan_limits(prof2)
        wellness_journey.record_step(supabase, user_id, "checkin", plan_tier=tier)
    except Exception as exc:
        print(f"[EGO] daily_care journey step error: {exc}", flush=True)

    return get_daily_care(supabase, user_id)
