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


def get_night_dump_streak(supabase: Client | None, user_id: str) -> dict:
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = ui.get("night_dump_streak") if isinstance(ui.get("night_dump_streak"), dict) else {}
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
        "night_dump": get_night_dump_streak(supabase, user_id),
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
        _touch_wellness_journey(supabase, user_id, source)
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
    _touch_wellness_journey(supabase, user_id, source)
    return get_streak(supabase, user_id)


def _touch_wellness_journey(
    supabase: Client | None, user_id: str, source: str
) -> None:
    try:
        from ego_api import wellness_journey

        alias = {
            "habit": "habit",
            "night_dump": "night_dump",
            "draft_confirm": "draft_confirm",
            "delegation_confirm": "draft_confirm",
            "checkin": "checkin",
        }.get(str(source or "").strip())
        if alias:
            wellness_journey.record_step(supabase, user_id, alias)
        wellness_journey.sync_streak_levels(supabase, user_id)
    except Exception as exc:
        print(f"[EGO] wellness_journey touch error: {exc}", flush=True)


def record_night_dump_streak(supabase: Client | None, user_id: str) -> dict:
    """Ofensiva do desabafo noturno (1x por dia local)."""
    if not supabase or not user_id:
        return get_night_dump_streak(supabase, user_id)
    today = _local_date_str()
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = dict(ui.get("night_dump_streak") if isinstance(ui.get("night_dump_streak"), dict) else {})
    last = str(raw.get("last_date") or "").strip()
    current = int(raw.get("current") or 0)
    longest = int(raw.get("longest") or 0)

    if last == today:
        ui["night_dump_streak"] = raw
        db.update_profile_fields(supabase, user_id, {"ui_state": ui})
        return get_night_dump_streak(supabase, user_id)

    yesterday = _yesterday(today)
    if last == yesterday and current > 0:
        current += 1
    else:
        current = 1
    longest = max(longest, current)
    raw = {"current": current, "longest": longest, "last_date": today}
    ui["night_dump_streak"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})
    return get_night_dump_streak(supabase, user_id)


def morning_reveal_notification_body(
    pending_count: int,
    night_dump_current: int,
    assistant_name: str,
) -> tuple[str, str]:
    name = (assistant_name or "Luna").strip() or "Luna"
    if pending_count > 0:
        items = "1 item" if pending_count == 1 else f"{pending_count} itens"
        title = "🌙 Amanhã revelado"
        body = f"{name}: {items} do desabafo esperando — toque e confirme na Agenda."
        if night_dump_current >= 3:
            body = (
                f"🔥 {night_dump_current} noites de desabafo! {items} para confirmar na Agenda."
            )
        return title, body
    if night_dump_current >= 1:
        return (
            "Bom dia ☀️",
            f"{name}: confira a agenda de hoje. "
            + (
                f"Você está com {night_dump_current} noites seguidas de desabafo 🔥"
                if night_dump_current >= 2
                else "Marque o que falta na Agenda."
            ),
        )
    return (
        "Bom dia ☀️",
        f"{name}: toque — veja a agenda de hoje e marque o que falta.",
    )


def evening_streak_notification_body(current: int, assistant_name: str) -> str | None:
    if current < 3:
        return None
    name = (assistant_name or "Luna").strip() or "Luna"
    return (
        f"Ei, você já está com {current} dias seguidos de organização! "
        f"Não vai deixar a peteca cair hoje, né? Solta um áudio rápido aqui "
        f"para {name} manter o ritmo amanhã!"
    )
