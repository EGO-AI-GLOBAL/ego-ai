"""Desafio semanal EGO de Bolso — 4 dias com 5/5 missões na semana."""

from __future__ import annotations

import datetime
from typing import Any

WEEK_DAYS_GOAL = 4


def _local_today() -> str:
    from ego_api.streaks import _local_date_str

    return _local_date_str()


def _iso_week_key(day: str | None = None) -> str:
    if day:
        try:
            dt = datetime.date.fromisoformat(day[:10])
        except ValueError:
            dt = datetime.date.today()
    else:
        dt = datetime.date.today()
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _normalize_days_done(raw: object, week_key: str) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        d = str(item or "").strip()[:10]
        if not d or d in out:
            continue
        if _iso_week_key(d) != week_key:
            continue
        out.append(d)
    return sorted(out)


def merge_weekly_into_state(state: dict[str, Any], raw: dict[str, Any]) -> None:
    today = _local_today()
    week_key = _iso_week_key(today)
    stored_key = str(raw.get("week_key") or "").strip()
    if stored_key != week_key:
        state["week_key"] = week_key
        state["week_days_done"] = []
    else:
        state["week_key"] = week_key
        state["week_days_done"] = _normalize_days_done(raw.get("week_days_done"), week_key)


def write_weekly_fields(state: dict[str, Any]) -> dict[str, Any]:
    week_key = str(state.get("week_key") or _iso_week_key()).strip()
    days = _normalize_days_done(state.get("week_days_done"), week_key)
    return {"week_key": week_key, "week_days_done": days}


def touch_weekly_day_complete(state: dict[str, Any]) -> bool:
    """Regista dia com 5/5 missões. Retorna True se contou novo dia."""
    today = _local_today()
    week_key = _iso_week_key(today)
    if str(state.get("week_key") or "") != week_key:
        state["week_key"] = week_key
        state["week_days_done"] = []
    days = list(state.get("week_days_done") or [])
    if today in days:
        return False
    days.append(today)
    state["week_days_done"] = sorted(days)
    return True


def build_weekly_payload(state: dict[str, Any]) -> dict[str, Any]:
    week_key = str(state.get("week_key") or _iso_week_key()).strip()
    days_done = len(_normalize_days_done(state.get("week_days_done"), week_key))
    goal = WEEK_DAYS_GOAL
    complete = days_done >= goal
    today = _local_today()
    today_done = today in _normalize_days_done(state.get("week_days_done"), week_key)
    remaining = max(0, goal - days_done)

    if complete:
        message = f"Desafio da semana completo — {days_done}/{goal} dias 🎉"
    elif today_done:
        message = f"Hoje fechou! Faltam {remaining} dia(s) esta semana para o bónus."
    else:
        message = f"Desafio da semana: {days_done}/{goal} dias com 5/5 missões"

    return {
        "week_key": week_key,
        "days_done": days_done,
        "days_goal": goal,
        "days_remaining": remaining,
        "complete": complete,
        "today_done": today_done,
        "message": message,
    }
