"""Monstrinhos Fase 10 — quiz semanal de bem-estar (3 perguntas, recompensa sementes)."""

from __future__ import annotations

import datetime
from typing import Any

from ego_api import db

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

QUIZ_SEED_REWARD = 5

_WEEKLY_BANK: list[dict[str, Any]] = [
    {
        "id": "sleep",
        "question": "Como dormiu esta semana?",
        "options": [
            {"key": "bad", "label": "Mal / pouco", "emoji": "😴"},
            {"key": "ok", "label": "Razoável", "emoji": "😐"},
            {"key": "good", "label": "Bem", "emoji": "😌"},
        ],
    },
    {
        "id": "stress",
        "question": "Nível de stress nos últimos dias?",
        "options": [
            {"key": "high", "label": "Alto", "emoji": "😰"},
            {"key": "mid", "label": "Médio", "emoji": "😟"},
            {"key": "low", "label": "Baixo", "emoji": "🙂"},
        ],
    },
    {
        "id": "support",
        "question": "Sentiu apoio emocional esta semana?",
        "options": [
            {"key": "no", "label": "Pouco", "emoji": "🌧️"},
            {"key": "some", "label": "Um pouco", "emoji": "🌤️"},
            {"key": "yes", "label": "Sim", "emoji": "☀️"},
        ],
    },
]


def _week_key() -> str:
    today = datetime.date.today()
    iso = today.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _quiz_for_week() -> dict[str, Any]:
    iso = datetime.date.today().isocalendar()
    idx = (iso.week - 1) % len(_WEEKLY_BANK)
    base = _WEEKLY_BANK[idx]
    return {
        "week_key": _week_key(),
        "quiz_id": base["id"],
        "question": base["question"],
        "options": base["options"],
        "reward_seeds": QUIZ_SEED_REWARD,
    }


def _load_quiz_state(supabase: Client | None, user_id: str) -> dict[str, str]:
    if not supabase or not user_id:
        return {}
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = ui.get("mood_quiz")
    if not isinstance(raw, dict):
        return {}
    return {
        "week_key": str(raw.get("week_key") or "").strip(),
        "answer_key": str(raw.get("answer_key") or "").strip(),
    }


def _save_quiz_state(
    supabase: Client | None, user_id: str, *, week_key: str, answer_key: str
) -> None:
    if not supabase or not user_id:
        return
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    ui["mood_quiz"] = {"week_key": week_key, "answer_key": answer_key}
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})


def get_quiz(supabase: Client | None, user_id: str) -> dict[str, Any]:
    quiz = _quiz_for_week()
    state = _load_quiz_state(supabase, user_id)
    done = state.get("week_key") == quiz["week_key"] and bool(state.get("answer_key"))
    return {
        **quiz,
        "done": done,
        "answer_key": state.get("answer_key") or None,
    }


def submit_answer(
    supabase: Client | None,
    user_id: str,
    *,
    answer_key: str,
) -> dict[str, Any]:
    quiz = _quiz_for_week()
    key = str(answer_key or "").strip()[:16]
    valid = {str(o.get("key") or "") for o in quiz.get("options") or []}
    if key not in valid:
        return {"ok": False, "error": "Resposta inválida.", "weekly_quiz": get_quiz(supabase, user_id)}
    state = _load_quiz_state(supabase, user_id)
    if state.get("week_key") == quiz["week_key"] and state.get("answer_key"):
        return {
            "ok": True,
            "already_done": True,
            "weekly_quiz": get_quiz(supabase, user_id),
            "daily_care": None,
        }
    _save_quiz_state(supabase, user_id, week_key=quiz["week_key"], answer_key=key)
    daily_care = None
    if supabase and user_id:
        from ego_api import daily_care

        daily_care = daily_care.award_quiz_seeds(
            supabase, user_id, amount=QUIZ_SEED_REWARD
        )
    return {
        "ok": True,
        "already_done": False,
        "seeds_awarded": QUIZ_SEED_REWARD,
        "weekly_quiz": get_quiz(supabase, user_id),
        "daily_care": daily_care,
    }
