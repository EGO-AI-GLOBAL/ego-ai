"""Push PAUSA EGO — 10h e 18h (substitui EGO de Bolso quando PAUSA activa)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from ego_api import db
from ego_api.config import read_env
from ego_api.expo_push import send_expo_push
from ego_api.request_ctx import set_session
from ego_api.supabase_client import create_service_client

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

from ego_api.ego_de_bolso_push import (
    _avatar_display_name,
    _bind_user_session,
    _empty_push_stats,
    _fetch_active_profiles,
    _local_now_from_ui,
    _parse_ui_state,
    _rituals_enabled,
    _should_send_slot,
    _valid_expo_token,
)

_LOG = logging.getLogger(__name__)

MORNING_HOUR = 10
EVENING_HOUR = 18
MORNING_PUSH_DATE_KEY = "pausa_ego_push_morning_date"
EVENING_PUSH_DATE_KEY = "pausa_ego_push_evening_date"
PAUSA_SCREEN = "wellness-journey"


def pausa_push_enabled() -> bool:
    from ego_api.pausa_ego import bolso_replaced_by_pausa

    if not bolso_replaced_by_pausa():
        return False
    return read_env("EGO_PAUSA_PUSH_ENABLED", "1").lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def pausa_push_status() -> dict[str, Any]:
    return {
        "enabled": pausa_push_enabled(),
        "morning_hour_local": MORNING_HOUR,
        "evening_hour_local": EVENING_HOUR,
        "max_pushes_per_day": 2,
        "replaces": "ego_de_bolso",
    }


def _pausa_needs_nudge(pausa: dict[str, Any]) -> bool:
    return not bool(pausa.get("today_done"))


def morning_notification_copy(
    pausa: dict[str, Any], *, avatar_name: str = ""
) -> tuple[str, str, str]:
    avatar = (avatar_name or "EGO-AI").strip() or "EGO-AI"
    daily = pausa.get("daily_exercise") if isinstance(pausa.get("daily_exercise"), dict) else {}
    title_ex = str(daily.get("title") or "Calma de hoje").strip()
    emoji = str(daily.get("emoji") or "🌬️").strip()
    title = f"{avatar} · bom dia {emoji}"
    body = f"{title_ex} — alívie stress em poucos minutos"
    return title, body, PAUSA_SCREEN


def evening_notification_copy(
    pausa: dict[str, Any], *, avatar_name: str = "", local_hour: int | None = None
) -> tuple[str, str, str]:
    avatar = (avatar_name or "EGO-AI").strip() or "EGO-AI"
    streak = max(0, int(pausa.get("streak_current") or 0))
    daily = pausa.get("daily_exercise") if isinstance(pausa.get("daily_exercise"), dict) else {}
    ex_title = str(daily.get("title") or "Calma de hoje").strip()
    hour = local_hour if local_hour is not None else 18
    if hour >= 22 or hour < 5:
        title = f"{avatar} · madrugada 🌌"
        body = "Ansiedade à noite? Calma 1 min — falar é opcional depois"
        return title, body, PAUSA_SCREEN
    title = f"{avatar} · calma da tarde 🌙"
    if streak >= 2:
        body = f"{ex_title} — sequência 🔥 {streak} dias"
    elif streak == 1:
        body = f"{ex_title} — mantenha a sequência"
    else:
        body = f"{ex_title} — cuide do stress antes de dormir"
    return title, body, PAUSA_SCREEN


def _process_pausa_slot(
    *,
    hour: int,
    date_key: str,
    slot: str,
    copy_fn: Callable[[dict[str, Any], str], tuple[str, str, str]],
    limit: int = 200,
    active_days: int = 45,
    force: bool = False,
) -> dict[str, int]:
    stats = _empty_push_stats()
    if not pausa_push_enabled():
        stats["skipped"] = 1
        return stats

    svc = create_service_client()
    if not svc:
        stats["failed"] = 1
        return stats

    from ego_api import pausa_ego

    try:
        rows = _fetch_active_profiles(svc, limit=limit, active_days=active_days)
    except Exception as exc:
        _LOG.warning("pausa_push query failed (%s): %s", slot, exc)
        stats["failed"] = 1
        return stats

    stats["candidates"] = len(rows)

    for row in rows:
        user_id = str(row.get("id") or "").strip()
        if not user_id:
            stats["skipped"] += 1
            continue
        ui = _parse_ui_state(row.get("ui_state"))
        if not _rituals_enabled(ui):
            stats["skipped"] += 1
            continue
        ok, _reason = _should_send_slot(ui, hour=hour, date_key=date_key)
        if not ok and not force:
            stats["skipped"] += 1
            continue
        token = _valid_expo_token(ui)
        if not token:
            stats["skipped"] += 1
            continue

        try:
            _bind_user_session(user_id, ui)
            pausa = pausa_ego.get_pausa(svc, user_id)
            if not _pausa_needs_nudge(pausa):
                stats["skipped"] += 1
                continue
            stats["eligible"] += 1
            avatar_name = _avatar_display_name(svc, user_id)
            title, body, screen = copy_fn(pausa, avatar_name)
            sent = send_expo_push(
                [token],
                title=title,
                body=body,
                data={"type": "pausa_ego", "screen": screen, "slot": slot},
            )
            if sent > 0:
                local_date = _local_now_from_ui(ui).strftime("%Y-%m-%d")
                ui[date_key] = local_date
                db.update_profile_fields(svc, user_id, {"ui_state": ui})
                stats["sent"] += 1
            else:
                stats["failed"] += 1
        except Exception as exc:
            _LOG.warning("pausa_push user=%s slot=%s: %s", user_id, slot, exc)
            stats["failed"] += 1
        finally:
            set_session(None)

    return stats


def process_pausa_morning_pushes(
    *,
    limit: int = 200,
    active_days: int = 45,
    force: bool = False,
) -> dict[str, int]:
    return _process_pausa_slot(
        hour=MORNING_HOUR,
        date_key=MORNING_PUSH_DATE_KEY,
        slot="morning",
        copy_fn=lambda p, a: morning_notification_copy(p, avatar_name=a),
        limit=limit,
        active_days=active_days,
        force=force,
    )


def process_pausa_evening_pushes(
    *,
    limit: int = 200,
    active_days: int = 45,
    force: bool = False,
) -> dict[str, int]:
    return _process_pausa_slot(
        hour=EVENING_HOUR,
        date_key=EVENING_PUSH_DATE_KEY,
        slot="evening",
        copy_fn=lambda p, a: evening_notification_copy(p, avatar_name=a),
        limit=limit,
        active_days=active_days,
        force=force,
    )


def process_pausa_pushes(
    *,
    limit: int = 200,
    active_days: int = 45,
    force: bool = False,
) -> dict[str, dict[str, int]]:
    return {
        "morning": process_pausa_morning_pushes(
            limit=limit, active_days=active_days, force=force
        ),
        "evening": process_pausa_evening_pushes(
            limit=limit, active_days=active_days, force=force
        ),
    }


def start_background_jobs() -> None:
    """Verifica de hora a hora quem está às 10h ou 18h locais (PAUSA)."""
    if not pausa_push_enabled():
        _LOG.info("pausa_push: desligado (PAUSA inactiva ou EGO_PAUSA_PUSH_ENABLED=0)")
        return

    def _loop() -> None:
        time.sleep(120)
        while True:
            try:
                batch = process_pausa_pushes()
                sent = batch["morning"].get("sent", 0) + batch["evening"].get("sent", 0)
                if sent:
                    _LOG.info("pausa_push batch: %s", batch)
            except Exception as exc:
                _LOG.warning("pausa_push background loop: %s", exc)
            time.sleep(3600)

    threading.Thread(
        target=_loop,
        daemon=True,
        name="pausa-ego-push-background",
    ).start()
    _LOG.info(
        "pausa_push: job horário iniciado (%sh e %sh fuso do aparelho)",
        MORNING_HOUR,
        EVENING_HOUR,
    )
