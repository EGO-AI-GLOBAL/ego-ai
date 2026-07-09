"""PAUSA EGO — alívio de stress/ansiedade em ~2 min (UI substitui EGO de Bolso)."""

from __future__ import annotations

import datetime
from typing import Any

from ego_api import db
from ego_api.request_ctx import get_session
from ego_api.schedule_tz import local_now_from_session

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

MOMENTS: list[dict[str, str]] = [
    {
        "key": "morning",
        "emoji": "🌅",
        "title": "Manhã",
        "prompt": "Antes do dia: solte os ombros e respire com calma.",
    },
    {
        "key": "midday",
        "emoji": "☀️",
        "title": "Meio-dia",
        "prompt": "Pausa rápida — 60 segundos no presente.",
    },
    {
        "key": "afternoon",
        "emoji": "🌤️",
        "title": "Tarde",
        "prompt": "Respire fundo antes de continuar o dia.",
    },
    {
        "key": "evening",
        "emoji": "🌙",
        "title": "Noite",
        "prompt": "Desacelere — 60s de calma com seu avatar.",
    },
    {
        "key": "late_night",
        "emoji": "🌌",
        "title": "Madrugada",
        "prompt": "Ansiedade de madrugada? 60s aqui — você não está só.",
    },
]

RECENT_DAYS_MAX = 7
VALID_KINDS = frozenset({"breath60", "breath120", "sos"})
BREATH_DURATIONS: dict[str, int] = {"breath60": 60, "breath120": 120, "sos": 60}


def _profile_lonely_today(supabase: Client | None, user_id: str, today: str) -> bool:
    if not supabase or not user_id:
        return False
    from ego_api.gentleness import note_signals_lonely

    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    dc = ui.get("daily_care")
    if not isinstance(dc, dict):
        return False
    journal = dc.get("mood_journal")
    if not isinstance(journal, list):
        return False
    for entry in journal:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("date") or "").strip() != today:
            continue
        if note_signals_lonely(str(entry.get("note") or "")):
            return True
    return False


def _profile_mood_key(supabase: Client | None, user_id: str) -> str:
    if not supabase or not user_id:
        return ""
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    dc = ui.get("daily_care")
    if isinstance(dc, dict):
        return str(dc.get("last_mood") or "").strip().lower()
    return ""


def _profile_plan_tier(supabase: Client | None, user_id: str) -> str:
    from ego_api.plans import resolve_plan_tier

    if not supabase or not user_id:
        from ego_api.plans import PLAN_ESSENTIAL

        return PLAN_ESSENTIAL
    prof = db.load_profile(supabase, user_id) or {}
    return resolve_plan_tier(prof)


def bolso_replaced_by_pausa() -> bool:
    """UI Bolso substituída por PAUSA EGO — não avançar missões nem prompt de bolso."""
    return True


def pausa_chat_prompt_block() -> str:
    return (
        "\n\nPAUSA EGO (use com leveza — máx. 1 frase se couber):\n"
        "- Se o utilizador mencionar ansiedade, stress, pressão, solidão, «estou mal», "
        "«cabeça não para», domingo difícil ou madrugada, valide com empatia e convide à "
        "PAUSA (respirar 60s no cartão PAUSA ou menu PAUSA EGO).\n"
        "- Se disser que não quer falar ou desabafar, respeite: ofereça PAUSA no corpo "
        "ou Monstrinhos (cartinha no jardim) — não force conversa longa.\n"
        "- Não mencione EGO de Bolso, missões, ovo, níveis ou Tamagotchi.\n"
        "- Não diagnostique depressão/ansiedade; não substitua terapia. CVV 188 só se risco agudo.\n"
    )


def _local_date_str() -> str:
    sess = get_session()
    if sess:
        loc = local_now_from_session(sess)
        if loc:
            return loc.strftime("%Y-%m-%d")
    return datetime.datetime.now().strftime("%Y-%m-%d")


def _local_hour() -> int:
    sess = get_session()
    if sess:
        loc = local_now_from_session(sess)
        if loc:
            return loc.hour
    return datetime.datetime.now().hour


def _yesterday(local_date: str) -> str:
    try:
        dt = datetime.datetime.strptime(local_date, "%Y-%m-%d").date()
        return (dt - datetime.timedelta(days=1)).isoformat()
    except ValueError:
        return ""


def _moment_for_hour(hour: int) -> dict[str, str]:
    if hour >= 22 or hour < 5:
        return MOMENTS[4]
    if hour < 11:
        return MOMENTS[0]
    if hour < 14:
        return MOMENTS[1]
    if hour < 18:
        return MOMENTS[2]
    return MOMENTS[3]


def breath_duration_seconds(kind: str) -> int:
    return BREATH_DURATIONS.get(str(kind or "breath60").strip(), 60)


def _load_state(supabase: Client | None, user_id: str) -> dict[str, Any]:
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = ui.get("pausa_ego")
    if not isinstance(raw, dict):
        raw = {}
    try:
        streak_current = max(0, int(raw.get("streak_current") or 0))
    except (TypeError, ValueError):
        streak_current = 0
    try:
        streak_longest = max(0, int(raw.get("streak_longest") or 0))
    except (TypeError, ValueError):
        streak_longest = 0
    try:
        total_sessions = max(0, int(raw.get("total_sessions") or 0))
    except (TypeError, ValueError):
        total_sessions = 0
    recent = raw.get("recent_dates")
    if not isinstance(recent, list):
        recent = []
    clean_recent: list[str] = []
    for item in recent:
        d = str(item or "").strip()[:10]
        if len(d) == 10 and d not in clean_recent:
            clean_recent.append(d)
    return {
        "streak_current": streak_current,
        "streak_longest": max(streak_longest, streak_current),
        "streak_last_date": str(raw.get("streak_last_date") or "").strip()[:10],
        "total_sessions": total_sessions,
        "recent_dates": clean_recent[-RECENT_DAYS_MAX:],
        "last_kind": str(raw.get("last_kind") or "").strip()[:16],
        "last_exercise_key": str(raw.get("last_exercise_key") or "").strip()[:16],
    }


def _save_state(
    supabase: Client | None, user_id: str, state: dict[str, Any]
) -> None:
    if not supabase or not user_id:
        return
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    ui["pausa_ego"] = {
        "streak_current": max(0, int(state.get("streak_current") or 0)),
        "streak_longest": max(0, int(state.get("streak_longest") or 0)),
        "streak_last_date": str(state.get("streak_last_date") or "").strip()[:10],
        "total_sessions": max(0, int(state.get("total_sessions") or 0)),
        "recent_dates": list(state.get("recent_dates") or [])[-RECENT_DAYS_MAX:],
        "last_kind": str(state.get("last_kind") or "").strip()[:16],
        "last_exercise_key": str(state.get("last_exercise_key") or "").strip()[:16],
    }
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})


def _week_dots(recent_dates: list[str], today: str) -> list[dict[str, Any]]:
    try:
        end = datetime.datetime.strptime(today, "%Y-%m-%d").date()
    except ValueError:
        return []
    done_set = set(recent_dates)
    out: list[dict[str, Any]] = []
    for offset in range(6, -1, -1):
        day = (end - datetime.timedelta(days=offset)).isoformat()
        out.append({"date": day, "done": day in done_set, "today": day == today})
    return out


def get_pausa(supabase: Client | None, user_id: str) -> dict[str, Any]:
    from ego_api.pausa_exercises import (
        ANYWHERE_LINE,
        pick_daily_exercise,
        pick_tomorrow_teaser,
        plan_benefits_payload,
    )

    state = _load_state(supabase, user_id)
    today = _local_date_str()
    moment = _moment_for_hour(_local_hour())
    streak = int(state["streak_current"] or 0)
    today_done = state["streak_last_date"] == today
    tier = _profile_plan_tier(supabase, user_id)
    mood_key = _profile_mood_key(supabase, user_id)
    lonely_today = _profile_lonely_today(supabase, user_id, today)
    avoid = str(state.get("last_exercise_key") or "").strip() or None
    yesterday = _yesterday(today)
    if yesterday:
        from ego_api.pausa_exercises import pick_daily_exercise as _pick

        yday = _pick(
            user_id=user_id or "anon",
            local_date=yesterday,
            tier=tier,
            mood_key=mood_key,
        )
        ykey = str(yday.get("key") or "").strip()
        if ykey:
            avoid = ykey
    daily = pick_daily_exercise(
        user_id=user_id or "anon",
        local_date=today,
        tier=tier,
        mood_key=mood_key,
        avoid_key=avoid,
        lonely_note=lonely_today,
    )
    tomorrow = pick_tomorrow_teaser(
        user_id=user_id or "anon",
        local_date=today,
        tier=tier,
        mood_key=mood_key,
        today_key=str(daily.get("key") or ""),
    )
    share_line = (
        f"Hoje cuidei de mim 🔥 {streak} dias — {daily.get('title', 'PAUSA')}"
        if streak >= 2
        else f"PAUSA de hoje: {daily.get('title', 'calma')} 🌬️"
    )
    retention_line = (
        f"Amanhã: {tomorrow.get('emoji', '🌬️')} {tomorrow.get('title', 'nova técnica')}"
        if not today_done
        else (
            f"Amanhã: {tomorrow.get('emoji', '🌬️')} {tomorrow.get('title', 'nova técnica')}"
            if streak >= 1
            else "Volte amanhã — técnica diferente esperando você"
        )
    )
    return {
        "streak_current": streak,
        "streak_longest": max(int(state["streak_longest"] or 0), streak),
        "today_done": today_done,
        "total_sessions": int(state["total_sessions"] or 0),
        "moment_key": moment["key"],
        "moment_emoji": moment["emoji"],
        "moment_title": moment["title"],
        "moment_prompt": moment["prompt"],
        "lonely_boosted": bool(daily.get("lonely_boosted")),
        "share_line": share_line,
        "week_dots": _week_dots(state["recent_dates"], today),
        "last_kind": state.get("last_kind") or None,
        "daily_exercise": daily,
        "plan_benefit": plan_benefits_payload(tier),
        "tomorrow_teaser": tomorrow,
        "anywhere_line": ANYWHERE_LINE,
        "retention_line": retention_line,
    }


def complete_session(
    supabase: Client | None,
    user_id: str,
    *,
    kind: str = "breath60",
) -> dict[str, Any]:
    if not supabase or not user_id:
        return get_pausa(supabase, user_id)
    from ego_api.pausa_exercises import get_exercise_by_key, is_valid_session_kind

    session_kind = str(kind or "breath60").strip()[:16]
    if not is_valid_session_kind(session_kind):
        session_kind = "breath60"
    exercise_key = session_kind if get_exercise_by_key(session_kind) else ""
    if session_kind in VALID_KINDS:
        exercise_key = exercise_key or session_kind
    today = _local_date_str()
    state = _load_state(supabase, user_id)
    last = str(state.get("streak_last_date") or "").strip()
    current = int(state.get("streak_current") or 0)
    if last == today:
        pass
    elif last == _yesterday(today):
        current += 1
    else:
        current = 1
    longest = max(int(state.get("streak_longest") or 0), current)
    recent = [d for d in state.get("recent_dates") or [] if d != today]
    recent.append(today)
    state.update(
        {
            "streak_current": current,
            "streak_longest": longest,
            "streak_last_date": today,
            "total_sessions": int(state.get("total_sessions") or 0) + 1,
            "recent_dates": recent[-RECENT_DAYS_MAX:],
            "last_kind": session_kind,
            "last_exercise_key": exercise_key or session_kind,
        }
    )
    _save_state(supabase, user_id, state)
    return get_pausa(supabase, user_id)


def default_payload() -> dict[str, Any]:
    from ego_api.pausa_exercises import (
        ANYWHERE_LINE,
        pick_daily_exercise,
        pick_tomorrow_teaser,
        plan_benefits_payload,
    )
    from ego_api.plans import PLAN_ESSENTIAL

    moment = _moment_for_hour(_local_hour())
    today = _local_date_str()
    daily = pick_daily_exercise(
        user_id="default",
        local_date=today,
        tier=PLAN_ESSENTIAL,
    )
    tomorrow = pick_tomorrow_teaser(
        user_id="default",
        local_date=today,
        tier=PLAN_ESSENTIAL,
        today_key=str(daily.get("key") or ""),
    )
    return {
        "streak_current": 0,
        "streak_longest": 0,
        "today_done": False,
        "total_sessions": 0,
        "moment_key": moment["key"],
        "moment_emoji": moment["emoji"],
        "moment_title": moment["title"],
        "moment_prompt": moment["prompt"],
        "share_line": f"PAUSA de hoje: {daily.get('title', 'calma')} 🌬️",
        "week_dots": _week_dots([], today),
        "last_kind": None,
        "daily_exercise": daily,
        "plan_benefit": plan_benefits_payload(PLAN_ESSENTIAL),
        "tomorrow_teaser": tomorrow,
        "anywhere_line": ANYWHERE_LINE,
        "retention_line": f"Amanhã: {tomorrow.get('emoji', '🌬️')} {tomorrow.get('title', 'nova técnica')}",
    }
