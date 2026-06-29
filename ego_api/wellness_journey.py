"""Jornada de Cuidado — níveis progressivos de bem-estar (sem dinheiro, uso crescente do app)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ego_api import db
from ego_api import progression
from ego_api.companion_shop import (
    DEFAULT_EGG_COLOR,
    award_mission_stars,
    merge_shop_into_state,
    shop_catalog,
    write_shop_fields,
)
from ego_api.companion_weekly import (
    build_weekly_payload,
    merge_weekly_into_state,
    touch_weekly_day_complete,
    try_award_weekly_bonus,
    write_weekly_fields,
)
from ego_api.streaks import _local_date_str, get_streak

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]


# Missões EGO de Bolso — USO do app (chat, voz, Monstrinhos, Agenda, desabafo)
# + CRESCIMENTO: níveis 20, 40, 60… = só convite (amigo novo aceita na Agenda).
JOURNEY_LEVELS: list[dict[str, Any]] = [
    {
        "level": 1,
        "title": "Primeiro uso",
        "subtitle": "Monstrinhos ou chat",
        "emoji": "🌱",
        "today_task": "Toque no emoji de humor OU mande 1 mensagem no chat",
        "why": "O app começa aqui — humor ou conversa com o avatar.",
        "requirements": [{"type": "or_steps", "options": [("checkin", 1), ("chat", 1)]}],
        "share_challenge": "Comecei a usar o EGO-AI 🌱 Quem vem comigo?",
        "plan_nudge": None,
    },
    {
        "level": 2,
        "title": "Conversar",
        "subtitle": "Texto ou voz no chat",
        "emoji": "💬",
        "today_task": "3 mensagens no chat OU 1 áudio de voz",
        "why": "Quanto mais você fala com o avatar, mais o app te conhece.",
        "requirements": [
            {"type": "or_steps", "options": [("chat", 3), ("voice", 1)]}
        ],
        "share_challenge": "Nível 2 💬 Já estou conversando com meu avatar",
        "plan_nudge": None,
    },
    {
        "level": 3,
        "title": "Agenda",
        "subtitle": "Hábito ou compromisso manual",
        "emoji": "📝",
        "today_task": "Marque 1 hábito OU 1 compromisso na Agenda",
        "why": "A Agenda é o centro do seu dia — use os botões, sem depender do chat.",
        "requirements": [{"type": "or_steps", "options": [("habit", 1), ("reminder", 1)]}],
        "share_challenge": "Nível 3 📝 Minha Agenda no EGO-AI",
        "plan_nudge": "Plano Essencial: até 3 lembretes. Conexão libera 20.",
    },
    {
        "level": 4,
        "title": "Desabafo",
        "subtitle": "Função «Desabafo agora» no chat",
        "emoji": "🌙",
        "today_task": "Faça 1 desabafo noturno no chat",
        "why": "O desabafo separa o que está na cabeça — amanhã você confirma na Agenda.",
        "requirements": [{"type": "step", "key": "night_dump", "min": 1}],
        "share_challenge": "Nível 4 🌙 Desabafo no EGO-AI — quem testa comigo?",
        "plan_nudge": None,
    },
    {
        "level": 5,
        "title": "Organizar",
        "subtitle": "Agenda após o desabafo",
        "emoji": "📅",
        "today_task": "Confirme 1 item do desabafo OU marque na Agenda",
        "why": "Fechar o ciclo desabafo → Agenda é o diferencial do app.",
        "requirements": [
            {
                "type": "or_steps",
                "options": [("draft_confirm", 1), ("reminder", 1), ("habit", 1)],
            }
        ],
        "share_challenge": "Nível 4 📅 Agenda no lugar no EGO-AI",
        "plan_nudge": None,
    },
    {
        "level": 6,
        "title": "Manhã no app",
        "subtitle": "Confirmar + conversar",
        "emoji": "☀️",
        "today_task": "1 mensagem no chat E confirmar desabafo OU marcar na Agenda",
        "why": "Rotina matinal no app: conversa com o avatar + Agenda no mesmo dia.",
        "requirements": [
            {"type": "step", "key": "chat", "min": 1},
            {
                "type": "or_steps",
                "options": [("draft_confirm", 1), ("reminder", 1), ("habit", 1)],
            },
        ],
        "share_challenge": "Nível 6 ☀️ Rotina EGO-AI funcionando",
        "plan_nudge": None,
    },
    {
        "level": 7,
        "title": "Voz",
        "subtitle": "Áudio no chat",
        "emoji": "🎙️",
        "today_task": "1 áudio de voz OU 3 mensagens no chat",
        "why": "A voz é um dos recursos mais usados — experimente o microfone.",
        "requirements": [
            {"type": "or_steps", "options": [("voice", 1), ("chat", 3)]}
        ],
        "share_challenge": "Nível 7 🎙️ Falando com meu avatar",
        "plan_nudge": "Essencial: 3 áudios/dia. Conexão: 15 áudios + mais mensagens.",
    },
    {
        "level": 8,
        "title": "Desabafo + Agenda",
        "subtitle": "Duas áreas do app no mesmo dia",
        "emoji": "💜",
        "today_task": "Desabafo noturno E 1 hábito ou compromisso na Agenda",
        "why": "Combinar chat e Agenda é como o app foi desenhado para funcionar.",
        "requirements": [
            {"type": "step", "key": "night_dump", "min": 1},
            {"type": "or_steps", "options": [("habit", 1), ("reminder", 1)]},
        ],
        "share_challenge": "Nível 8 💜 Chat + Agenda no mesmo dia",
        "plan_nudge": None,
    },
    {
        "level": 9,
        "title": "Humor + chat",
        "subtitle": "Monstrinhos e mensagem",
        "emoji": "⭐",
        "today_task": "Check-in nos Monstrinhos E 1 mensagem no chat",
        "why": "Monstrinhos + avatar = as duas portas de entrada do app.",
        "requirements": [
            {"type": "step", "key": "checkin", "min": 1},
            {"type": "step", "key": "chat", "min": 1},
        ],
        "share_challenge": "Nível 9 ⭐ Uso completo do EGO-AI hoje",
        "plan_nudge": None,
    },
    {
        "level": 10,
        "title": "Primeira dezena",
        "subtitle": "Monstrinhos, chat ou Agenda",
        "emoji": "🎯",
        "today_task": "Check-in nos Monstrinhos OU 3 mensagens no chat OU marque na Agenda",
        "why": "Dez níveis de cuidado — explore o app antes do marco de convite no 20.",
        "requirements": [
            {
                "type": "or_steps",
                "options": [
                    ("checkin", 1),
                    ("chat", 3),
                    ("habit", 1),
                    ("reminder", 1),
                ],
            }
        ],
        "share_challenge": "Nível 10 🎯 EGO de Bolso a todo vapor",
        "plan_nudge": None,
    },
    {
        "level": 11,
        "title": "Chat de novo",
        "subtitle": "Manter a conversa",
        "emoji": "🌿",
        "today_task": "3 mensagens no chat OU 1 áudio de voz",
        "why": "Voltar ao chat mantém o vínculo com o avatar.",
        "requirements": [
            {"type": "or_steps", "options": [("chat", 3), ("voice", 1)]}
        ],
        "share_challenge": "Nível 11 🌿 Ainda no chat do EGO-AI",
        "plan_nudge": None,
    },
    {
        "level": 12,
        "title": "Desabafo de rotina",
        "subtitle": "Use o botão no chat",
        "emoji": "🌙",
        "today_task": "Faça o desabafo noturno no chat",
        "why": "Usuários que desabafam voltam — é o coração do app.",
        "requirements": [{"type": "step", "key": "night_dump", "min": 1}],
        "share_challenge": "Nível 12 🌙 Desabafo virou hábito no app",
        "plan_nudge": None,
    },
    {
        "level": 13,
        "title": "Agenda ativa",
        "subtitle": "Marque algo hoje",
        "emoji": "📋",
        "today_task": "1 hábito OU 1 compromisso na Agenda",
        "why": "Agenda usada todo dia = app útil no dia a dia.",
        "requirements": [
            {"type": "or_steps", "options": [("habit", 1), ("reminder", 1)]}
        ],
        "share_challenge": "Nível 13 📋 Agenda viva no EGO-AI",
        "plan_nudge": None,
    },
    {
        "level": 14,
        "title": "Confirmar desabafo",
        "subtitle": "Banner na Agenda",
        "emoji": "🏆",
        "today_task": "Confirme 1 desabafo OU marque hábito/compromisso na Agenda",
        "why": "Confirmar na Agenda transforma desabafo em plano — ou organize o dia manualmente.",
        "requirements": [
            {
                "type": "or_steps",
                "options": [("draft_confirm", 1), ("habit", 1), ("reminder", 1)],
            }
        ],
        "share_challenge": "Nível 14 🏆 Ciclo desabafo fechado",
        "plan_nudge": None,
    },
    {
        "level": 15,
        "title": "Só voz",
        "subtitle": "Microfone no chat",
        "emoji": "🎙️",
        "today_task": "Mande 1 áudio de voz ao avatar",
        "why": "Áudio gasta mais do plano — e é o que mais prende quem usa o app.",
        "requirements": [{"type": "step", "key": "voice", "min": 1}],
        "share_challenge": "Nível 15 🎙️ Voz no EGO-AI",
        "plan_nudge": "Voz usa mais do plano — veja Conexão se precisar.",
    },
    {
        "level": 16,
        "title": "Monstrinhos",
        "subtitle": "Check-in de humor",
        "emoji": "💜",
        "today_task": "Toque no emoji de como está (Monstrinhos)",
        "why": "Monstrinhos trazem gente de volta ao app todos os dias.",
        "requirements": [{"type": "step", "key": "checkin", "min": 1}],
        "share_challenge": "Check-in feito 💜 Monstrinhos no EGO-AI",
        "plan_nudge": None,
    },
    {
        "level": 17,
        "title": "Explorar tudo",
        "subtitle": "Chat, Agenda ou desabafo",
        "emoji": "👑",
        "today_task": "Desabafo, voz, hábito ou compromisso — escolha 1",
        "why": "Você já conhece o app — use a função que fizer sentido hoje.",
        "requirements": [
            {
                "type": "or_steps",
                "options": [
                    ("night_dump", 1),
                    ("voice", 1),
                    ("habit", 1),
                    ("reminder", 1),
                ],
            }
        ],
        "share_challenge": "Nível 17 👑 Power user do EGO-AI",
        "plan_nudge": None,
    },
    {
        "level": 18,
        "title": "Ciclo completo",
        "subtitle": "Desabafo → confirmar na Agenda",
        "emoji": "🫶",
        "today_task": "Desabafo noturno E confirmar 1 item na Agenda",
        "why": "O fluxo completo do app em um dia: desabafar e organizar.",
        "requirements": [
            {"type": "step", "key": "night_dump", "min": 1},
            {"type": "step", "key": "draft_confirm", "min": 1},
        ],
        "share_challenge": "Nível 18 🫶 Dominei o fluxo do EGO-AI",
        "plan_nudge": None,
    },
    {
        "level": 19,
        "title": "Super dia",
        "subtitle": "Monstrinhos + Agenda",
        "emoji": "✨",
        "today_task": "Check-in nos Monstrinhos E 1 hábito ou compromisso",
        "why": "Humor + organização — o combo de retenção do app.",
        "requirements": [
            {"type": "step", "key": "checkin", "min": 1},
            {"type": "or_steps", "options": [("habit", 1), ("reminder", 1)]},
        ],
        "share_challenge": "Nível 19 ✨ Uso forte do EGO-AI",
        "plan_nudge": None,
    },
    {
        "level": 20,
        "title": "Embaixador",
        "subtitle": "Mais um amigo novo",
        "emoji": "🌟",
        "today_task": "Convide outro amigo pelo telefone (sem conta) — cumpre quando aceitar",
        "why": "A cada 20 níveis você traz alguém novo — assim o app cresce de graça, 1 vira 2, 2 vira 4…",
        "requirements": [{"type": "step", "key": "invite", "min": 1}],
        "share_challenge": "Nível 20/20 no EGO-AI 🌟 Embaixador do app",
        "plan_nudge": None,
    },
]

HANDCRAFTED_MAX = len(JOURNEY_LEVELS)

# Missões completas por dia (níveis) antes de «volte amanhã».
MISSIONS_PER_DAY = 5

_STEP_ALIASES = {
    "habit": "habit",
    "night_dump": "night_dump",
    "draft_confirm": "draft_confirm",
    "delegation_confirm": "draft_confirm",
    "reminder": "reminder",
    "commitment": "reminder",
    "compromisso": "reminder",
    "chat": "chat",
    "voice": "voice",
    "invite": "invite",
    "checkin": "checkin",
}


def _journey_cap(supabase: Client | None) -> int:
    return progression.get_cap(supabase, "wellness_journey")


def _is_invite_growth_level(n: int) -> bool:
    """Níveis 20, 40, 60… — só convite (crescimento viral)."""
    return n > 0 and n % 20 == 0


def _is_invite_only_level(level_def: dict[str, Any]) -> bool:
    reqs = level_def.get("requirements") or []
    if len(reqs) != 1:
        return False
    req = reqs[0]
    return (
        str(req.get("type") or "") == "step"
        and str(req.get("key") or "") == "invite"
        and int(req.get("min") or 1) == 1
    )


def _invite_growth_level(n: int) -> dict[str, Any]:
    return {
        "level": n,
        "title": "Trazer alguém" if n < 100 else f"Embaixador {n}",
        "subtitle": "Amigo novo aceita na Agenda",
        "emoji": "🤝" if n % 20 else "🌟",
        "today_task": "Convide pelo telefone alguém sem conta — missão fecha quando aceitar",
        "why": (
            "Missão de crescimento a cada 20 níveis: 1 amigo novo no app, "
            "sem propaganda — só convite na Agenda."
        ),
        "requirements": [{"type": "step", "key": "invite", "min": 1}],
        "share_challenge": f"Nível {n} 🤝 Convidei mais alguém pro EGO-AI — vem?",
        "plan_nudge": None,
    }


def _procedural_level(n: int) -> dict[str, Any]:
    if _is_invite_growth_level(n):
        return _invite_growth_level(n)
    emojis = ("🌱", "💬", "📝", "📅", "🌙", "☀️", "🔥", "💜", "✨", "🌟")
    titles = (
        ("Constância", "Mais um passo de cuidado"),
        ("Conexão", "Fale com seu avatar"),
        ("Organização", "Use a Agenda"),
        ("Desabafo", "Esvazie a mente"),
        ("Hábito", "Marque um hábito"),
        ("Voz", "Mande um áudio"),
        ("Monstrinhos", "Check-in de humor"),
    )
    t_idx = (n - 1) % len(titles)
    title, subtitle = titles[t_idx]
    chat_need = min(3, 1 + max(0, (n - HANDCRAFTED_MAX) // 25))
    mod = (n - HANDCRAFTED_MAX) % 6
    if mod == 0:
        reqs: list[dict[str, Any]] = [
            {
                "type": "or_steps",
                "options": [("night_dump", 1), ("checkin", 1), ("chat", 1)],
            }
        ]
    elif mod == 1:
        reqs = [{"type": "step", "key": "chat", "min": chat_need}]
    elif mod == 2:
        reqs = [
            {"type": "or_steps", "options": [("chat", 1), ("checkin", 1)]}
        ]
    elif mod == 3:
        reqs = [{"type": "step", "key": "voice", "min": 1}]
    elif mod == 4:
        reqs = [
            {"type": "or_steps", "options": [("habit", 1), ("reminder", 1)]}
        ]
    else:
        reqs = [
            {
                "type": "or_steps",
                "options": [("draft_confirm", 1), ("habit", 1), ("reminder", 1)],
            }
        ]
    return {
        "level": n,
        "title": f"{title} {n}",
        "subtitle": subtitle,
        "emoji": emojis[(n - 1) % len(emojis)],
        "today_task": "Complete os passos de hoje — um de cada vez",
        "why": "Pequenos passos diários constroem bem-estar duradouro.",
        "requirements": reqs,
        "share_challenge": f"Qual é teu nível? {n} do EGO de Bolso no EGO-AI 🥚",
        "plan_nudge": "Plano Conexão desbloqueia mais voz e lembretes." if n % 17 == 0 else None,
    }


def _level_def(level: int, cap: int) -> dict[str, Any]:
    lvl = max(1, min(int(level), cap))
    if lvl <= HANDCRAFTED_MAX:
        return JOURNEY_LEVELS[lvl - 1]
    return _procedural_level(lvl)


def _load_state(supabase: Client | None, user_id: str) -> dict[str, Any]:
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = ui.get("wellness_journey")
    if not isinstance(raw, dict):
        raw = {}
    level = int(raw.get("level") or 1)
    cap = _journey_cap(supabase)
    if level < 1:
        level = 1
    if level > cap:
        level = cap
    counts = raw.get("step_counts")
    if not isinstance(counts, dict):
        counts = {}
    clean_counts: dict[str, int] = {}
    for k, v in counts.items():
        key = str(k or "").strip()[:32]
        if not key:
            continue
        try:
            clean_counts[key] = max(0, int(v or 0))
        except (TypeError, ValueError):
            clean_counts[key] = 0
    try:
        missions_today_count = max(0, int(raw.get("missions_today_count") or 0))
    except (TypeError, ValueError):
        missions_today_count = 0
    state = {
        "level": level,
        "step_counts": clean_counts,
        "levels_completed": list(raw.get("levels_completed") or []),
        "show_level_up": bool(raw.get("show_level_up")),
        "mission_done_date": str(raw.get("mission_done_date") or "").strip()[:10],
        "missions_today_date": str(raw.get("missions_today_date") or "").strip()[:10],
        "missions_today_count": missions_today_count,
    }
    merge_shop_into_state(state, raw)
    merge_weekly_into_state(state, raw)
    return state


def _save_state(
    supabase: Client | None, user_id: str, state: dict[str, Any]
) -> None:
    if not supabase or not user_id:
        return
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    ui["wellness_journey"] = {
        "level": state["level"],
        "step_counts": state["step_counts"],
        "levels_completed": state.get("levels_completed") or [],
        "show_level_up": bool(state.get("show_level_up")),
        "mission_done_date": str(state.get("mission_done_date") or "").strip()[:10],
        "missions_today_date": str(state.get("missions_today_date") or "").strip()[:10],
        "missions_today_count": max(0, int(state.get("missions_today_count") or 0)),
        **write_shop_fields(state),
        **write_weekly_fields(state),
    }
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})


def _req_met(
    req: dict[str, Any], counts: dict[str, int], streak: dict[str, Any]
) -> bool:
    rtype = str(req.get("type") or "")
    if rtype == "step":
        key = str(req.get("key") or "")
        need = int(req.get("min") or 1)
        return counts.get(key, 0) >= need
    if rtype == "or_steps":
        for key, need in req.get("options") or []:
            if key == "streak":
                if int(streak.get("current") or 0) >= int(need):
                    return True
            elif counts.get(str(key), 0) >= int(need):
                return True
        return False
    if rtype == "streak":
        return int(streak.get("current") or 0) >= int(req.get("min") or 1)
    return False


def _level_complete(level_def: dict[str, Any], counts: dict[str, int], streak: dict) -> bool:
    for req in level_def.get("requirements") or []:
        if not _req_met(req, counts, streak):
            return False
    return True


def _progress_for_level(
    level_def: dict[str, Any], counts: dict[str, int], streak: dict
) -> float:
    reqs = level_def.get("requirements") or []
    if not reqs:
        return 1.0
    done = sum(1 for r in reqs if _req_met(r, counts, streak))
    return round(done / len(reqs), 2)


def _streak_label(need: int) -> str:
    return f"{need} dias de sequência"


def _steps_status(
    level_def: dict[str, Any], counts: dict[str, int], streak: dict
) -> list[dict[str, Any]]:
    """Lista amigável do que falta no nível actual."""
    out: list[dict[str, Any]] = []
    for req in level_def.get("requirements") or []:
        rtype = str(req.get("type") or "")
        if rtype == "step":
            key = str(req.get("key") or "")
            need = int(req.get("min") or 1)
            have = counts.get(key, 0)
            out.append(
                {
                    "key": key,
                    "label": _label_with_how(key, need),
                    "done": have >= need,
                    "have": have,
                    "need": need,
                }
            )
        elif rtype == "or_steps":
            opts = req.get("options") or []
            labels = []
            any_done = False
            for key, need in opts:
                if key == "streak":
                    have = int(streak.get("current") or 0)
                    labels.append(_streak_label(int(need)))
                    if have >= int(need):
                        any_done = True
                else:
                    have = counts.get(str(key), 0)
                    labels.append(_label_with_how(str(key), int(need)))
                    if have >= int(need):
                        any_done = True
            out.append(
                {
                    "key": "or",
                    "label": " OU ".join(labels),
                    "done": any_done,
                }
            )
        elif rtype == "streak":
            need = int(req.get("min") or 1)
            have = int(streak.get("current") or 0)
            out.append(
                {
                    "key": "streak",
                    "label": _streak_label(need),
                    "done": have >= need,
                    "have": have,
                    "need": need,
                }
            )
    return out


def _capitalize_pt(text: str) -> str:
    t = text.strip()
    if not t:
        return t
    return t[0].upper() + t[1:]


def _format_today_task(
    level_def: dict[str, Any], counts: dict[str, int], streak: dict[str, Any]
) -> str:
    """Missão mostrada ao utilizador — derivada das regras reais (não do marketing)."""
    steps = _steps_status(level_def, counts, streak)
    pending = [s for s in steps if not s.get("done")]
    if not pending:
        return str(level_def.get("today_task") or "Missão concluída neste nível")
    parts: list[str] = []
    for step in pending:
        label = str(step.get("label") or "").strip()
        have, need = step.get("have"), step.get("need")
        if have is not None and need is not None and int(need) > 1:
            label = f"{label} ({int(have)}/{int(need)})"
        if label:
            parts.append(label)
    if not parts:
        return str(level_def.get("today_task") or "")
    if len(parts) == 1:
        return _capitalize_pt(parts[0])
    return _capitalize_pt(" e ".join(parts))


_KNOWN_REQUIREMENT_KEYS = frozenset(
    {
        "checkin",
        "chat",
        "voice",
        "habit",
        "reminder",
        "night_dump",
        "draft_confirm",
        "invite",
        "streak",
    }
)

# Passos que o utilizador consegue fazer hoje no app (sem sequência oculta nem convite).
APP_MISSION_STEP_KEYS = frozenset(
    {
        "checkin",
        "chat",
        "voice",
        "habit",
        "reminder",
        "night_dump",
        "draft_confirm",
        "invite",
    }
)

# Passos com caminho implementado no app/API.
WIRED_STEP_SOURCES: dict[str, str] = {
    "checkin": "Monstrinhos do Humor (daily-care)",
    "chat": "mensagem no chat",
    "voice": "áudio de voz no chat",
    "habit": "Agenda → hábito",
    "reminder": "Agenda → compromisso",
    "night_dump": "chat → Desabafo agora",
    "draft_confirm": "Agenda → confirmar desabafo",
    "invite": "Agenda → telefone ou e-mail sem conta; amigo aceita",
}


def _iter_requirement_keys(level_def: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for req in level_def.get("requirements") or []:
        rtype = str(req.get("type") or "")
        if rtype == "step":
            keys.append(str(req.get("key") or ""))
        elif rtype == "or_steps":
            for key, _need in req.get("options") or []:
                keys.append(str(key))
        elif rtype == "streak":
            keys.append("streak")
    return keys


def _max_need_for_key(level_def: dict[str, Any], step_key: str) -> int:
    max_need = 0
    for req in level_def.get("requirements") or []:
        rtype = str(req.get("type") or "")
        if rtype == "step" and str(req.get("key") or "") == step_key:
            max_need = max(max_need, int(req.get("min") or 1))
        elif rtype == "or_steps":
            for key, need in req.get("options") or []:
                if str(key) == step_key:
                    max_need = max(max_need, int(need))
    return max_need


def _level_has_draft_confirm_escape(level_def: dict[str, Any]) -> bool:
    """draft_confirm só é justo com desabafo no mesmo nível ou alternativa na Agenda."""
    keys = _iter_requirement_keys(level_def)
    if "draft_confirm" not in keys:
        return True
    if "night_dump" in keys:
        return True
    for req in level_def.get("requirements") or []:
        if str(req.get("type") or "") == "or_steps":
            opts = [str(k) for k, _ in req.get("options") or []]
            if "draft_confirm" in opts and (
                "habit" in opts or "reminder" in opts or "chat" in opts
            ):
                return True
    return False


def _validate_one_level(level_def: dict[str, Any], *, procedural: bool) -> list[str]:
    errors: list[str] = []
    n = int(level_def.get("level") or 0)
    tag = f"nível {n}"
    reqs = level_def.get("requirements") or []
    if not reqs:
        errors.append(f"{tag}: sem requirements")
        return errors
    keys = _iter_requirement_keys(level_def)
    if _is_invite_growth_level(n):
        if not _is_invite_only_level(level_def):
            errors.append(f"{tag}: múltiplo de 20 deve ser missão só de convite")
    elif "invite" in keys:
        errors.append(f"{tag}: convite só nos níveis 20, 40, 60…")
    if not _level_has_draft_confirm_escape(level_def):
        errors.append(
            f"{tag}: confirmar desabafo sem alternativa nem desabafo no mesmo dia"
        )
    for key in keys:
        if key not in _KNOWN_REQUIREMENT_KEYS:
            errors.append(f"{tag}: passo desconhecido '{key}'")
        elif key not in APP_MISSION_STEP_KEYS:
            errors.append(f"{tag}: passo '{key}' não é missão cumprível no app atual")
        elif key not in WIRED_STEP_SOURCES:
            errors.append(f"{tag}: passo '{key}' sem origem documentada")
        need = _max_need_for_key(level_def, key)
        if need > 3 and key in ("chat", "voice", "checkin", "night_dump"):
            errors.append(f"{tag}: '{key}' pede {need} — máximo 3 por missão diária")
    task = _format_today_task(level_def, {}, {"current": 0})
    if not str(task or "").strip():
        errors.append(f"{tag}: today_task vazio para estado inicial")
    return errors


def validate_journey_levels(*, cap: int = 500) -> list[str]:
    """Garante que cada nível (1..cap) só pede passos justos e com fio no código."""
    errors: list[str] = []
    cap = max(HANDCRAFTED_MAX, int(cap or HANDCRAFTED_MAX))
    for lv in JOURNEY_LEVELS:
        errors.extend(_validate_one_level(lv, procedural=False))
    for n in range(HANDCRAFTED_MAX + 1, cap + 1):
        errors.extend(_validate_one_level(_procedural_level(n), procedural=True))
    return errors


def validate_journey_expansion_caps(
    caps: tuple[int, ...] = (500, 1000),
) -> list[str]:
    """Valida teto actual e próxima expansão (+500) — missões procedurais infinitas."""
    errors: list[str] = []
    seen: set[str] = set()
    for cap in caps:
        cap = max(HANDCRAFTED_MAX, int(cap))
        for err in validate_journey_levels(cap=cap):
            key = f"{cap}:{err}"
            if key not in seen:
                seen.add(key)
                errors.append(f"cap {cap}: {err}")
        # Amostra: convite a cada 20 mantém-se após expandir o teto.
        invite_samples = [20]
        if cap >= 40:
            invite_samples.append((cap // 20) * 20)
        for n in invite_samples:
            if n < 20 or n > cap:
                continue
            ld = _level_def(n, cap)
            if _is_invite_growth_level(n) and not _is_invite_only_level(ld):
                errors.append(f"cap {cap}: nível {n} perdeu missão só de convite")
    return errors


def _step_how(key: str) -> str:
    """Onde tocar no app — aparece entre parênteses em «Falta: …»."""
    hints = {
        "checkin": "Monstrinhos → toque no emoji de humor",
        "chat": "Chat → escreva 1 mensagem",
        "voice": "Chat → botão do microfone",
        "habit": "Agenda → marque 1 hábito",
        "reminder": "Agenda → + Novo compromisso",
        "night_dump": "Chat → Desabafo agora",
        "draft_confirm": "Agenda → confirme item do desabafo",
        "invite": "Agenda → Entre Nós → Convidar pessoa",
    }
    return hints.get(key, "")


def _label_with_how(key: str, need: int) -> str:
    base = _step_label(key, need)
    how = _step_how(key)
    if how:
        return f"{base} ({how})"
    return base


def _step_label(key: str, need: int) -> str:
    labels = {
        "chat": "mensagem no chat" if need == 1 else f"{need} mensagens no chat",
        "voice": "mensagem de voz" if need == 1 else f"{need} mensagens de voz",
        "habit": "hábito marcado",
        "reminder": "compromisso ou lembrete na Agenda",
        "night_dump": "desabafo noturno",
        "draft_confirm": "confirmar desabafo na Agenda",
        "invite": "convidar pelo telefone (ou e-mail) sem conta — aceitar na Agenda",
        "checkin": "check-in de hoje",
    }
    base = labels.get(key, key)
    if key == "invite" and need > 1:
        return f"{need} convites no Entre Nós"
    if need > 1 and key not in ("chat", "voice"):
        return f"{need}× {base}"
    return base


def _companion_stage(level: int) -> dict[str, str]:
    if level <= 5:
        return {"stage": "egg", "label": "Ovo", "emoji": "🥚"}
    if level <= 20:
        return {"stage": "hatchling", "label": "Filhote", "emoji": "🐣"}
    if level <= 100:
        return {"stage": "teen", "label": "Jovem", "emoji": "🐥"}
    return {"stage": "adult", "label": "Adulto", "emoji": "🦜"}


def _sanitize_companion_name(raw: object) -> str:
    if not isinstance(raw, str):
        raw = str(raw or "")
    name = "".join(c for c in raw.strip() if c.isprintable() and c not in "\n\r\t")
    name = " ".join(name.split())
    return name[:24]


def _companion_name_fields(supabase: Client | None, user_id: str) -> dict[str, Any]:
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    name = _sanitize_companion_name(ui.get("ego_companion_name"))
    setup_done = bool(ui.get("ego_companion_name_setup_done")) or bool(name)
    return {
        "companion_name": name or None,
        "companion_name_setup_done": setup_done,
    }


def _plan_nudge(level_def: dict[str, Any], plan_tier: str) -> str | None:
    if plan_tier and plan_tier != "essential":
        return None
    return level_def.get("plan_nudge")


def _mission_done_today(state: dict[str, Any]) -> bool:
    return int(state.get("missions_today_count") or 0) >= MISSIONS_PER_DAY


def _daily_care_fraction(missions_today: int, mission_done_today: bool) -> float:
    """Barra «Cuidado»: 1 missão = 20%, 2 = 40% … 5 = 100%."""
    if mission_done_today:
        return 1.0
    return min(1.0, max(0.0, int(missions_today) / MISSIONS_PER_DAY))


def _sync_daily_missions(
    state: dict[str, Any],
    supabase: Client | None,
    user_id: str,
    streak_data: dict[str, Any],
    cap: int,
) -> dict[str, Any]:
    """Novo dia: zera contador; legado 1 missão/dia avança nível pendente."""
    today = _local_date_str()
    if str(state.get("missions_today_date") or "") == today:
        return state
    done_date = str(state.get("mission_done_date") or "").strip()
    if done_date and done_date < today:
        level_def = _level_def(int(state["level"]), cap)
        if _level_complete(level_def, state["step_counts"], streak_data):
            cur = int(state["level"])
            if cur < cap:
                state["level"] = cur + 1
                state["step_counts"] = {}
                state["show_level_up"] = True
                try:
                    progression.maybe_expand_cap(
                        supabase, "wellness_journey", state["level"]
                    )
                except Exception as exc:
                    print(f"[EGO] journey legacy advance error: {exc}", flush=True)
    legacy_one_today = done_date == today
    state["missions_today_date"] = today
    state["missions_today_count"] = 1 if legacy_one_today else 0
    state["mission_done_date"] = ""
    if legacy_one_today:
        level_def = _level_def(int(state["level"]), cap)
        if _level_complete(level_def, state["step_counts"], streak_data):
            cur = int(state["level"])
            if cur < cap:
                state["level"] = cur + 1
                state["step_counts"] = {}
                try:
                    progression.maybe_expand_cap(
                        supabase, "wellness_journey", state["level"]
                    )
                except Exception as exc:
                    print(f"[EGO] journey legacy same-day advance: {exc}", flush=True)
    return state


def _on_level_complete(
    state: dict[str, Any],
    supabase: Client | None,
    cap: int,
) -> None:
    """Até MISSIONS_PER_DAY níveis no mesmo dia; convite no meio pausa até aceitar."""
    today = _local_date_str()
    if str(state.get("missions_today_date") or "") != today:
        state["missions_today_date"] = today
        state["missions_today_count"] = 0

    count = int(state.get("missions_today_count") or 0) + 1
    state["missions_today_count"] = count

    cur = int(state["level"])
    completed = list(state.get("levels_completed") or [])
    if cur not in completed:
        completed.append(cur)
    state["levels_completed"] = completed
    state["show_level_up"] = True

    if cur < cap:
        state["level"] = cur + 1
        state["step_counts"] = {}
        try:
            progression.maybe_expand_cap(supabase, "wellness_journey", state["level"])
        except Exception as exc:
            print(f"[EGO] journey level advance error: {exc}", flush=True)

    if count >= MISSIONS_PER_DAY:
        state["mission_done_date"] = today
        touch_weekly_day_complete(state)
        try_award_weekly_bonus(state)

    award_mission_stars(state, missions_per_day=MISSIONS_PER_DAY)


def build_journey_payload(
    supabase: Client | None,
    user_id: str,
    *,
    streak: dict | None = None,
    plan_tier: str = "essential",
    clear_level_up: bool = False,
) -> dict[str, Any]:
    state = _load_state(supabase, user_id)
    streak_data = streak if streak is not None else get_streak(supabase, user_id)
    cap = _journey_cap(supabase)
    before_level = int(state["level"])
    before_count = int(state.get("missions_today_count") or 0)
    state = _sync_daily_missions(state, supabase, user_id, streak_data, cap)
    if int(state["level"]) != before_level or int(state.get("missions_today_count") or 0) != before_count:
        _save_state(supabase, user_id, state)
    if try_award_weekly_bonus(state):
        _save_state(supabase, user_id, state)
    level = int(state["level"])
    level_def = _level_def(level, cap)
    counts = dict(state["step_counts"])
    complete = _level_complete(level_def, counts, streak_data)
    missions_today = int(state.get("missions_today_count") or 0)
    mission_done_today = _mission_done_today(state)
    show_level_up = bool(state.get("show_level_up"))

    if clear_level_up and show_level_up:
        state["show_level_up"] = False
        _save_state(supabase, user_id, state)
        show_level_up = False

    at_max = level >= cap and complete
    companion = _companion_stage(level)
    name_fields = _companion_name_fields(supabase, user_id)
    daily_fraction = _daily_care_fraction(missions_today, mission_done_today)
    progress = daily_fraction
    care_pct = int(round(min(100, max(0, daily_fraction * 100))))
    steps = _steps_status(level_def, counts, streak_data)
    if mission_done_today:
        steps = [{**s, "done": True} for s in steps]
        complete = True
        today_task = (
            f"Fez {MISSIONS_PER_DAY}/{MISSIONS_PER_DAY} missões hoje — volte amanhã"
        )
    else:
        today_task = _format_today_task(level_def, counts, streak_data)
        if missions_today > 0 and today_task:
            today_task = f"Missão {missions_today + 1}/{MISSIONS_PER_DAY}: {today_task}"
    return {
        "level": level,
        "max_level": cap,
        "title": level_def["title"],
        "subtitle": level_def["subtitle"],
        "emoji": level_def["emoji"],
        "today_task": today_task,
        "why": level_def["why"],
        "progress": progress,
        "level_complete": complete,
        "mission_done_today": mission_done_today,
        "missions_today": missions_today,
        "missions_per_day": MISSIONS_PER_DAY,
        "steps": steps,
        "show_level_up": show_level_up,
        "share_challenge": level_def["share_challenge"],
        "plan_nudge": _plan_nudge(level_def, plan_tier),
        "journey_finished": at_max,
        "companion_stage": companion["stage"],
        "companion_stage_label": companion["label"],
        "companion_sprite_emoji": companion["emoji"],
        "companion_name": name_fields["companion_name"],
        "companion_name_setup_done": name_fields["companion_name_setup_done"],
        "care_percent": care_pct,
        "stars": max(0, int(state.get("stars") or 0)),
        "companion_egg_color": str(state.get("egg_color") or DEFAULT_EGG_COLOR),
        "egg_color_shop": shop_catalog(state),
        "weekly_challenge": build_weekly_payload(state),
    }


def get_journey(
    supabase: Client | None, user_id: str, *, plan_tier: str = "essential"
) -> dict[str, Any]:
    return build_journey_payload(supabase, user_id, plan_tier=plan_tier)


def record_step(
    supabase: Client | None,
    user_id: str,
    step_key: str,
    *,
    plan_tier: str = "essential",
) -> dict[str, Any]:
    """Regista passo da jornada (pode repetir contagens no mesmo nível)."""
    if not supabase or not user_id:
        return get_journey(supabase, user_id, plan_tier=plan_tier)
    key = _STEP_ALIASES.get(str(step_key or "").strip(), str(step_key or "").strip()[:32])
    if not key:
        return get_journey(supabase, user_id, plan_tier=plan_tier)

    state = _load_state(supabase, user_id)
    streak_data = get_streak(supabase, user_id)
    cap = _journey_cap(supabase)
    state = _sync_daily_missions(state, supabase, user_id, streak_data, cap)

    if _mission_done_today(state):
        _save_state(supabase, user_id, state)
        return build_journey_payload(
            supabase, user_id, streak=streak_data, plan_tier=plan_tier
        )

    counts = dict(state["step_counts"])
    counts[key] = counts.get(key, 0) + 1
    state["step_counts"] = counts

    level_def = _level_def(int(state["level"]), cap)

    mission_advanced = _level_complete(level_def, counts, streak_data)
    if mission_advanced:
        _on_level_complete(state, supabase, cap)

    _save_state(supabase, user_id, state)
    if mission_advanced:
        from ego_api.bolso_chat import try_mission_complete_push

        try_mission_complete_push(supabase, user_id, plan_tier=plan_tier)
    return build_journey_payload(
        supabase, user_id, streak=streak_data, plan_tier=plan_tier
    )


def sync_streak_levels(
    supabase: Client | None, user_id: str, *, plan_tier: str = "essential"
) -> dict[str, Any]:
    """Avança níveis que dependem só da sequência (sem novo passo)."""
    if not supabase or not user_id:
        return get_journey(supabase, user_id, plan_tier=plan_tier)
    state = _load_state(supabase, user_id)
    streak_data = get_streak(supabase, user_id)
    cap = _journey_cap(supabase)
    state = _sync_daily_missions(state, supabase, user_id, streak_data, cap)
    changed = False

    if not _mission_done_today(state):
        level_def = _level_def(int(state["level"]), cap)
        mission_advanced = _level_complete(level_def, state["step_counts"], streak_data)
        if mission_advanced:
            _on_level_complete(state, supabase, cap)
            changed = True

    if changed:
        _save_state(supabase, user_id, state)
        from ego_api.bolso_chat import try_mission_complete_push

        try_mission_complete_push(supabase, user_id, plan_tier=plan_tier)
    return build_journey_payload(
        supabase, user_id, streak=streak_data, plan_tier=plan_tier
    )


def clear_level_up_flag(supabase: Client | None, user_id: str) -> dict[str, Any]:
    state = _load_state(supabase, user_id)
    state["show_level_up"] = False
    _save_state(supabase, user_id, state)
    prof = db.load_profile(supabase, user_id) or {}
    tier = str(prof.get("plan_tier") or "essential")
    return get_journey(supabase, user_id, plan_tier=tier)
