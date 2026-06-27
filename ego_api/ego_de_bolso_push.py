"""Push EGO de Bolso — 10h (missões pendentes) e 18h (cuidado) via Expo Push API."""

from __future__ import annotations

import datetime
import logging
import threading
import time
from typing import Any, Callable

from ego_api import db
from ego_api.config import read_env
from ego_api.expo_push import send_expo_push
from ego_api.request_ctx import UserSession, set_session
from ego_api.supabase_client import create_service_client

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore[misc, assignment]

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

_LOG = logging.getLogger(__name__)
MORNING_HOUR = 10
CARE_HOUR = 18
MORNING_PUSH_DATE_KEY = "ego_de_bolso_push_morning_date"
CARE_PUSH_DATE_KEY = "ego_de_bolso_push_date"


def ego_de_bolso_push_enabled() -> bool:
    return read_env("EGO_BOLSO_PUSH_ENABLED", "1").lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def ego_de_bolso_push_status() -> dict[str, Any]:
    return {
        "enabled": ego_de_bolso_push_enabled(),
        "morning_hour_local": MORNING_HOUR,
        "care_hour_local": CARE_HOUR,
        "max_pushes_per_day": 2,
    }


def _parse_ui_state(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        import json

        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _tzinfo_from_ui(ui: dict[str, Any]) -> datetime.tzinfo | None:
    tz_name = str(ui.get("ego_client_timezone") or "").strip()
    if tz_name and ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    raw_off = ui.get("ego_client_tz_offset_min")
    try:
        if raw_off is not None:
            return datetime.timezone(datetime.timedelta(minutes=int(raw_off)))
    except (TypeError, ValueError):
        pass
    return None


def _local_now_from_ui(ui: dict[str, Any]) -> datetime.datetime:
    tz = _tzinfo_from_ui(ui)
    if tz is not None:
        return datetime.datetime.now(tz)
    return datetime.datetime.now().astimezone()


def _rituals_enabled(ui: dict[str, Any]) -> bool:
    raw = ui.get("ego_daily_checkin_enabled")
    if raw is False or str(raw).strip().lower() in ("0", "false", "no", "off"):
        return False
    return True


def _valid_expo_token(ui: dict[str, Any]) -> str:
    tok = str(ui.get("expo_push_token") or "").strip()
    if tok.startswith("ExponentPushToken[") or tok.startswith("ExpoPushToken["):
        return tok
    return ""


def _text_hints_agenda(text: str) -> bool:
    t = text.lower()
    return any(
        k in t
        for k in (
            "agenda",
            "hábito",
            "habito",
            "lembrete",
            "compromisso",
            "entre nós",
            "entre nos",
            "convite",
        )
    )


def _text_hints_daily_care(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("check-in", "checkin", "monstrinho", "humor"))


def resolve_care_screen(journey: dict[str, Any]) -> str:
    """Espelha app/src/utils/egoDeBolsoCareRoute.ts para deep link."""
    pending = [s for s in (journey.get("steps") or []) if not s.get("done")]
    task = str(journey.get("today_task") or "")

    for step in pending:
        key = str(step.get("key") or "").lower()
        label = str(step.get("label") or "")

        if key in ("habit", "reminder", "invite", "draft_confirm"):
            return "agenda"
        if key in ("checkin", "streak"):
            return "daily-care"
        if key == "night_dump":
            return "chat"
        if key in ("chat", "voice"):
            return "chat"
        if key == "or":
            if _text_hints_agenda(label):
                return "agenda"
            if _text_hints_daily_care(label):
                return "daily-care"
            ll = label.lower()
            if "desabafo" in ll or "chat" in ll or "voz" in ll:
                return "chat"

    if _text_hints_agenda(task):
        return "agenda"
    if _text_hints_daily_care(task):
        return "daily-care"
    return "chat"


def _missions_remaining(journey: dict[str, Any]) -> int:
    per_day = max(1, int(journey.get("missions_per_day") or 5))
    today = max(0, int(journey.get("missions_today") or 0))
    return max(0, per_day - today)


def companion_needs_care(journey: dict[str, Any]) -> bool:
    if journey.get("mission_done_today") or journey.get("journey_finished"):
        return False
    pending = [s for s in (journey.get("steps") or []) if not s.get("done")]
    return bool(pending) or not journey.get("level_complete")


def companion_has_morning_nudge(journey: dict[str, Any]) -> bool:
    if journey.get("mission_done_today") or journey.get("journey_finished"):
        return False
    return _missions_remaining(journey) > 0


def _sanitize_companion_name(raw: object) -> str:
    if not isinstance(raw, str):
        raw = str(raw or "")
    name = "".join(c for c in raw.strip() if c.isprintable() and c not in "\n\r\t")
    name = " ".join(name.split())
    return name[:24]


def _companion_stage_label(journey: dict[str, Any], *, companion_name: str = "") -> str:
    custom = _sanitize_companion_name(companion_name or journey.get("companion_name"))
    return custom or str(journey.get("companion_stage_label") or "EGO de Bolso").strip()


def morning_notification_copy(
    journey: dict[str, Any], *, companion_name: str = ""
) -> tuple[str, str, str]:
    stage = _companion_stage_label(journey, companion_name=companion_name)
    per_day = max(1, int(journey.get("missions_per_day") or 5))
    remaining = _missions_remaining(journey)
    screen = resolve_care_screen(journey)
    title = f"{stage} — bom dia! 🌅"
    body = f"Faltam {remaining}/{per_day} missões hoje"
    return title, body, screen


def notification_copy(
    journey: dict[str, Any], *, companion_name: str = ""
) -> tuple[str, str, str]:
    stage = _companion_stage_label(journey, companion_name=companion_name)
    task = str(journey.get("today_task") or "Complete a missão de hoje").strip()
    screen = resolve_care_screen(journey)
    title = f"{stage} precisa de você 🥚"
    body = task if len(task) <= 90 else f"{task[:87]}…"
    return title, body, screen


def _bind_user_session(user_id: str, ui: dict[str, Any]) -> None:
    off = ui.get("ego_client_tz_offset_min")
    try:
        off_int = int(off) if off is not None else None
    except (TypeError, ValueError):
        off_int = None
    set_session(
        UserSession(
            user_id=user_id,
            timezone=str(ui.get("ego_client_timezone") or "").strip(),
            tz_offset_min=off_int,
        )
    )


def _should_send_slot(
    ui: dict[str, Any], *, hour: int, date_key: str
) -> tuple[bool, str]:
    if not _rituals_enabled(ui):
        return False, "rituals_off"
    if not _valid_expo_token(ui):
        return False, "no_token"
    local = _local_now_from_ui(ui)
    if local.hour != hour:
        return False, "not_push_hour"
    today = local.strftime("%Y-%m-%d")
    if str(ui.get(date_key) or "").strip() == today:
        return False, "already_sent"
    return True, ""


def _empty_push_stats() -> dict[str, int]:
    return {
        "candidates": 0,
        "eligible": 0,
        "sent": 0,
        "skipped": 0,
        "failed": 0,
    }


def _fetch_active_profiles(
    svc: Client, *, limit: int, active_days: int
) -> list[dict[str, Any]]:
    since = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=max(1, active_days))
    ).isoformat()
    res = (
        svc.table("profiles")
        .select("id,ui_state,last_login_at")
        .not_.is_("last_login_at", "null")
        .gte("last_login_at", since)
        .order("last_login_at", desc=True)
        .limit(min(500, max(1, limit)))
        .execute()
    )
    return list(res.data or [])


def _process_push_slot(
    *,
    hour: int,
    date_key: str,
    slot: str,
    journey_eligible: Callable[[dict[str, Any]], bool],
    copy_fn: Callable[[dict[str, Any], str], tuple[str, str, str]],
    limit: int = 200,
    active_days: int = 45,
    force: bool = False,
) -> dict[str, int]:
    stats = _empty_push_stats()
    if not ego_de_bolso_push_enabled():
        stats["skipped"] = 1
        return stats

    svc = create_service_client()
    if not svc:
        stats["failed"] = 1
        return stats

    from ego_api import wellness_journey

    try:
        rows = _fetch_active_profiles(svc, limit=limit, active_days=active_days)
    except Exception as exc:
        _LOG.warning("ego_de_bolso_push query failed (%s): %s", slot, exc)
        stats["failed"] = 1
        return stats

    stats["candidates"] = len(rows)

    for row in rows:
        user_id = str(row.get("id") or "").strip()
        if not user_id:
            stats["skipped"] += 1
            continue
        ui = _parse_ui_state(row.get("ui_state"))
        ok, _reason = _should_send_slot(ui, hour=hour, date_key=date_key)
        if not ok and not force:
            stats["skipped"] += 1
            continue
        if force and not _valid_expo_token(ui):
            stats["skipped"] += 1
            continue

        try:
            _bind_user_session(user_id, ui)
            plan_tier = str(ui.get("plan_tier") or "essential").strip() or "essential"
            journey = wellness_journey.get_journey(svc, user_id, plan_tier=plan_tier)
            if not journey_eligible(journey):
                stats["skipped"] += 1
                continue
            stats["eligible"] += 1
            companion_name = str(ui.get("ego_companion_name") or "")
            title, body, screen = copy_fn(journey, companion_name)
            sent = send_expo_push(
                [_valid_expo_token(ui)],
                title=title,
                body=body,
                data={"type": "ego_de_bolso", "screen": screen, "slot": slot},
            )
            if sent > 0:
                local_date = _local_now_from_ui(ui).strftime("%Y-%m-%d")
                ui[date_key] = local_date
                db.update_profile_fields(svc, user_id, {"ui_state": ui})
                stats["sent"] += 1
            else:
                stats["failed"] += 1
        except Exception as exc:
            _LOG.warning("ego_de_bolso_push user=%s slot=%s: %s", user_id, slot, exc)
            stats["failed"] += 1
        finally:
            set_session(None)

    return stats


def _morning_copy_wrapper(
    journey: dict[str, Any], companion_name: str
) -> tuple[str, str, str]:
    return morning_notification_copy(journey, companion_name=companion_name)


def _care_copy_wrapper(
    journey: dict[str, Any], companion_name: str
) -> tuple[str, str, str]:
    return notification_copy(journey, companion_name=companion_name)


def process_ego_de_bolso_morning_pushes(
    *,
    limit: int = 200,
    active_days: int = 45,
    force: bool = False,
) -> dict[str, int]:
    """Envia push às 10h (fuso do aparelho): «Faltam X/5 missões»."""
    return _process_push_slot(
        hour=MORNING_HOUR,
        date_key=MORNING_PUSH_DATE_KEY,
        slot="morning",
        journey_eligible=companion_has_morning_nudge,
        copy_fn=_morning_copy_wrapper,
        limit=limit,
        active_days=active_days,
        force=force,
    )


def process_ego_de_bolso_care_pushes(
    *,
    limit: int = 200,
    active_days: int = 45,
    force: bool = False,
) -> dict[str, int]:
    """Envia push às 18h (fuso do aparelho) a quem tem missão pendente."""
    return _process_push_slot(
        hour=CARE_HOUR,
        date_key=CARE_PUSH_DATE_KEY,
        slot="care",
        journey_eligible=companion_needs_care,
        copy_fn=_care_copy_wrapper,
        limit=limit,
        active_days=active_days,
        force=force,
    )


def process_ego_de_bolso_pushes(
    *,
    limit: int = 200,
    active_days: int = 45,
    force: bool = False,
) -> dict[str, dict[str, int]]:
    """Processa os dois slots (máx. 2 push/dia por utilizador)."""
    return {
        "morning": process_ego_de_bolso_morning_pushes(
            limit=limit, active_days=active_days, force=force
        ),
        "care": process_ego_de_bolso_care_pushes(
            limit=limit, active_days=active_days, force=force
        ),
    }


def start_background_jobs() -> None:
    """Verifica de hora a hora quem está às 10h ou 18h locais."""
    if not ego_de_bolso_push_enabled():
        _LOG.info("ego_de_bolso_push: desligado (EGO_BOLSO_PUSH_ENABLED=0)")
        return

    def _loop() -> None:
        time.sleep(90)
        while True:
            try:
                batch = process_ego_de_bolso_pushes()
                sent = batch["morning"].get("sent", 0) + batch["care"].get("sent", 0)
                if sent:
                    _LOG.info("ego_de_bolso_push batch: %s", batch)
            except Exception as exc:
                _LOG.warning("ego_de_bolso_push background loop: %s", exc)
            time.sleep(3600)

    threading.Thread(
        target=_loop,
        daemon=True,
        name="ego-de-bolso-push-background",
    ).start()
    _LOG.info(
        "ego_de_bolso_push: job horário iniciado (%sh e %sh fuso do aparelho)",
        MORNING_HOUR,
        CARE_HOUR,
    )
