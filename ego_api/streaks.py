"""Ofensivas diárias — descarrego ou hábito concluído."""

from __future__ import annotations

import datetime

from ego_api import db
from ego_api.request_ctx import get_session
from ego_api.schedule_tz import local_now_from_session

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]


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


def get_streak(supabase: Client | None, user_id: str) -> dict:
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = ui.get("streak") if isinstance(ui.get("streak"), dict) else {}
    today = _local_date_str()
    last = str(raw.get("last_date") or "").strip()
    current = int(raw.get("current") or 0)
    longest = int(raw.get("longest") or 0)
    return {
        "current": current,
        "longest": max(longest, current),
        "last_date": last,
        "active_today": last == today,
        "at_risk": bool(current >= 1 and last != today),
    }


def record_streak_activity(
    supabase: Client | None,
    user_id: str,
    *,
    source: str,
) -> dict:
    """Regista actividade válida para ofensiva (1x por dia local)."""
    if not supabase or not user_id:
        return get_streak(supabase, user_id)
    today = _local_date_str()
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = dict(ui.get("streak") if isinstance(ui.get("streak"), dict) else {})
    last = str(raw.get("last_date") or "").strip()
    current = int(raw.get("current") or 0)
    longest = int(raw.get("longest") or 0)

    if last == today:
        raw["last_source"] = source[:32]
        ui["streak"] = raw
        db.update_profile_fields(supabase, user_id, {"ui_state": ui})
        return get_streak(supabase, user_id)

    yesterday = _yesterday(today)
    if last == yesterday and current > 0:
        current += 1
    else:
        current = 1
    longest = max(longest, current)
    raw = {
        "current": current,
        "longest": longest,
        "last_date": today,
        "last_source": source[:32],
    }
    ui["streak"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})
    return get_streak(supabase, user_id)


def evening_streak_notification_body(current: int, assistant_name: str) -> str | None:
    if current < 3:
        return None
    name = (assistant_name or "Luna").strip() or "Luna"
    return (
        f"Ei, você já está com {current} dias seguidos de organização! "
        f"Não vai deixar a peteca cair hoje, né? Solta um áudio rápido aqui "
        f"para {name} manter o ritmo amanhã!"
    )
