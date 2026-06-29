"""EGO de Bolso — prompt de chat e push de missão completada."""

from __future__ import annotations

from typing import Any

from ego_api import db

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]


def bolso_mission_prompt_block(
    supabase: Client | None, user_id: str, *, plan_tier: str = "essential"
) -> str:
    """Injeta no system prompt quando há missões pendentes no bolso."""
    if not supabase or not user_id:
        return ""
    try:
        from ego_api import wellness_journey

        journey = wellness_journey.get_journey(supabase, user_id, plan_tier=plan_tier)
    except Exception:
        return ""
    if journey.get("mission_done_today") or journey.get("journey_finished"):
        return ""

    missions_today = max(0, int(journey.get("missions_today") or 0))
    missions_per_day = max(1, int(journey.get("missions_per_day") or 5))
    if missions_today >= missions_per_day:
        return ""

    remaining = missions_per_day - missions_today
    pet = (
        str(journey.get("companion_name") or "").strip()
        or str(journey.get("companion_stage_label") or "EGO de Bolso").strip()
    )
    task = str(journey.get("today_task") or "Complete a missão de hoje").strip()
    pending = [
        str(s.get("label") or "").strip()
        for s in (journey.get("steps") or [])
        if not s.get("done") and str(s.get("label") or "").strip()
    ]
    pending_line = " · ".join(pending[:3]) if pending else task

    return (
        "\n\nEGO DE BOLSO (missão pendente — use com leveza, no máximo 1–2 frases se couber):\n"
        f"- Bolso «{pet}»: {missions_today}/{missions_per_day} missões hoje; faltam {remaining}.\n"
        f"- Missão actual: {task}\n"
        f"- Passos em aberto: {pending_line}\n"
        "- Se o utilizador quiser falar do bolso, valide e ajude o próximo passo "
        "(Monstrinhos, chat, agenda ou voz — conforme a missão).\n"
        "- Não pressione nem repita o bolso em todas as respostas.\n"
    )


def try_mission_complete_push(
    supabase: Client | None,
    user_id: str,
    *,
    plan_tier: str = "essential",
) -> None:
    """Push imediato ao completar missão (avatar + bolso)."""
    if not supabase or not user_id:
        return
    from ego_api.ego_de_bolso_push import maybe_send_mission_complete_push

    maybe_send_mission_complete_push(supabase, user_id, plan_tier=plan_tier)
