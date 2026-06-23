"""Jornada de Cuidado — níveis progressivos de bem-estar (sem dinheiro, uso crescente do app)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ego_api import db
from ego_api import progression
from ego_api.streaks import get_streak

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]


# Cada nível exige requisitos; ao completar avança automaticamente.
JOURNEY_LEVELS: list[dict[str, Any]] = [
    {
        "level": 1,
        "title": "Respirar",
        "subtitle": "1 minuto — sem pressão",
        "emoji": "🌱",
        "today_task": "Toque no emoji de como está OU mande 1 mensagem",
        "why": "Nomear o que sente já alivia — psicólogos chamam de check-in emocional.",
        "requirements": [{"type": "or_steps", "options": [("checkin", 1), ("chat", 1)]}],
        "share_challenge": "Comecei minha Jornada de Cuidado no EGO-AI 🌱 Nível 1 feito!",
        "plan_nudge": None,
    },
    {
        "level": 2,
        "title": "Conectar",
        "subtitle": "Fale ou escreva — você escolhe",
        "emoji": "💬",
        "today_task": "3 mensagens no chat OU 1 áudio de voz",
        "why": "Ouvir sua voz ou ler suas palavras ajuda a organizar a mente.",
        "requirements": [
            {
                "type": "or_steps",
                "options": [("chat", 3), ("voice", 1)],
            }
        ],
        "share_challenge": "Nível 2 da Jornada de Cuidado 💬 Quem topa me acompanhar?",
        "plan_nudge": None,
    },
    {
        "level": 3,
        "title": "Registrar",
        "subtitle": "Tire da cabeça e ponha no papel",
        "emoji": "📝",
        "today_task": "Marque 1 hábito OU crie 1 lembrete na Agenda",
        "why": "Anotar reduz ansiedade — o cérebro para de repetir a mesma preocupação.",
        "requirements": [{"type": "or_steps", "options": [("habit", 1), ("reminder", 1)]}],
        "share_challenge": "Nível 3 📝 Organizando a mente com EGO-AI",
        "plan_nudge": "Plano Essencial: até 3 lembretes. Conexão libera 20.",
    },
    {
        "level": 4,
        "title": "Organizar",
        "subtitle": "Seu dia com mais clareza",
        "emoji": "📅",
        "today_task": "Confirme 1 item do desabafo OU marque 1 compromisso",
        "why": "Ver o dia organizado dá sensação de controlo — importante para quem ansia.",
        "requirements": [
            {"type": "or_steps", "options": [("draft_confirm", 1), ("reminder", 1)]}
        ],
        "share_challenge": "Nível 4 📅 Agenda no lugar, cabeça mais leve",
        "plan_nudge": None,
    },
    {
        "level": 5,
        "title": "Desabafar",
        "subtitle": "Solte antes de dormir",
        "emoji": "🌙",
        "today_task": "Grave 1 desabafo noturno OU 1 mensagem de voz",
        "why": "Desabafar à noite melhora o sono — amanhã você confirma na Agenda.",
        "requirements": [
            {"type": "or_steps", "options": [("night_dump", 1), ("voice", 1)]}
        ],
        "share_challenge": "Nível 5 🌙 Desabafo noturno — quem faz comigo?",
        "plan_nudge": "Essencial: 3 áudios/dia. Conexão: 15 áudios + mais mensagens.",
    },
    {
        "level": 6,
        "title": "Rotina da manhã",
        "subtitle": "Confirmar é cuidar de si",
        "emoji": "☀️",
        "today_task": "Confirme o desabafo de ontem E mande 1 mensagem",
        "why": "Ritual matinal cria previsibilidade — ansiedade odeia surpresas.",
        "requirements": [
            {"type": "step", "key": "draft_confirm", "min": 1},
            {"type": "step", "key": "chat", "min": 1},
        ],
        "share_challenge": "Nível 6 ☀️ Rotina de bem-estar funcionando!",
        "plan_nudge": None,
    },
    {
        "level": 7,
        "title": "Constância",
        "subtitle": "3 dias seguidos de cuidado",
        "emoji": "🔥",
        "today_task": "Mantenha a ofensiva — 1 ação hoje (chat, hábito ou desabafo)",
        "why": "3 dias formam hábito. Psicólogos dizem que a repetição acalma o sistema nervoso.",
        "requirements": [{"type": "streak", "min": 3}],
        "share_challenge": "3 dias na Jornada de Cuidado 🔥 Quem bate meu recorde?",
        "plan_nudge": "Você está usando mais — veja os planos se bater limites diários.",
    },
    {
        "level": 8,
        "title": "Cuidado completo",
        "subtitle": "Corpo e mente no mesmo ritmo",
        "emoji": "💜",
        "today_task": "Marque 1 hábito E faça 1 desabafo noturno",
        "why": "Combinar ação diária + desabafo é o combo que clínicas de bem-estar recomendam.",
        "requirements": [
            {"type": "step", "key": "habit", "min": 1},
            {"type": "step", "key": "night_dump", "min": 1},
        ],
        "share_challenge": "Nível 8 💜 Cuidado completo — desafio entre amigos!",
        "plan_nudge": "Plano Essencial: 200 mil tokens/mês. Conexão: 800 mil.",
    },
    {
        "level": 9,
        "title": "Uma semana",
        "subtitle": "7 dias de Jornada",
        "emoji": "⭐",
        "today_task": "Não quebre a sequência hoje",
        "why": "Uma semana inteira prova que você consegue — marco que muita gente em terapia busca.",
        "requirements": [{"type": "streak", "min": 7}],
        "share_challenge": "7 dias de bem-estar ⭐ Quem consegue igual?",
        "plan_nudge": None,
    },
    {
        "level": 10,
        "title": "Compartilhar cuidado",
        "subtitle": "Ninguém precisa fazer sozinho",
        "emoji": "🤝",
        "today_task": "Convide 1 pessoa (Entre Nós) OU complete 14 dias de ofensiva",
        "why": "Apoio social é gratuito e funciona — convide alguém de confiança.",
        "requirements": [
            {"type": "or_steps", "options": [("invite", 1), ("streak", 14)]}
        ],
        "share_challenge": "Completei 10 níveis da Jornada 🤝 Quem vem comigo?",
        "plan_nudge": None,
    },
    {
        "level": 11,
        "title": "Duas semanas",
        "subtitle": "14 dias de cuidado",
        "emoji": "🌿",
        "today_task": "Mantenha a sequência — você está perto de 2 semanas",
        "why": "Duas semanas é quando muita gente em terapia sente mudança real.",
        "requirements": [{"type": "streak", "min": 14}],
        "share_challenge": "14 dias de bem-estar 🌿 Bate meu recorde?",
        "plan_nudge": None,
    },
    {
        "level": 12,
        "title": "Desabafo frequente",
        "subtitle": "3 noites de desabafo na semana",
        "emoji": "🌙",
        "today_task": "Faça o desabafo noturno hoje",
        "why": "Desabafar com regularidade evita acumular ansiedade.",
        "requirements": [{"type": "step", "key": "night_dump", "min": 3}],
        "share_challenge": "Nível 12 🌙 Desabafo virou hábito",
        "plan_nudge": None,
    },
    {
        "level": 13,
        "title": "Agenda viva",
        "subtitle": "5 lembretes ou hábitos marcados",
        "emoji": "📋",
        "today_task": "Marque 1 coisa na Agenda hoje",
        "why": "Agenda viva = menos surpresas na cabeça.",
        "requirements": [
            {"type": "or_steps", "options": [("habit", 3), ("reminder", 3)]}
        ],
        "share_challenge": "Nível 13 📋 Agenda no piloto automático",
        "plan_nudge": None,
    },
    {
        "level": 14,
        "title": "Três semanas",
        "subtitle": "21 dias de Jornada",
        "emoji": "🏆",
        "today_task": "Não quebre a sequência hoje",
        "why": "21 dias — marco clássico para formar hábito duradouro.",
        "requirements": [{"type": "streak", "min": 21}],
        "share_challenge": "21 dias 🏆 Quem chega aqui comigo?",
        "plan_nudge": None,
    },
    {
        "level": 15,
        "title": "Voz confiante",
        "subtitle": "5 mensagens de voz",
        "emoji": "🎙️",
        "today_task": "Mande 1 áudio ao avatar",
        "why": "Falar em voz alta organiza emoções mais rápido que só pensar.",
        "requirements": [{"type": "step", "key": "voice", "min": 5}],
        "share_challenge": "Nível 15 🎙️ Falando com coragem",
        "plan_nudge": "Voz usa mais do plano — veja Conexão se precisar.",
    },
    {
        "level": 16,
        "title": "Check-in mestre",
        "subtitle": "10 desafios diários feitos",
        "emoji": "💜",
        "today_task": "Complete os Monstrinhos do Humor de hoje",
        "why": "Reconhecer como se sente todo dia é treino emocional.",
        "requirements": [{"type": "step", "key": "checkin", "min": 10}],
        "share_challenge": "10 check-ins 💜 Desafio Diário no sangue",
        "plan_nudge": None,
    },
    {
        "level": 17,
        "title": "Um mês",
        "subtitle": "30 dias seguidos",
        "emoji": "👑",
        "today_task": "Proteja sua sequência hoje",
        "why": "Um mês de cuidado — poucos chegam aqui. Você está.",
        "requirements": [{"type": "streak", "min": 30}],
        "share_challenge": "30 dias 👑 Quem aguenta igual?",
        "plan_nudge": None,
    },
    {
        "level": 18,
        "title": "Rede de apoio",
        "subtitle": "2 pessoas convidadas",
        "emoji": "🫶",
        "today_task": "Convide mais 1 pessoa para o Entre Nós",
        "why": "Cuidar junto é mais fácil — apoio social protege a saúde mental.",
        "requirements": [{"type": "step", "key": "invite", "min": 2}],
        "share_challenge": "Nível 18 🫶 Cuidado em rede",
        "plan_nudge": None,
    },
    {
        "level": 19,
        "title": "Rotina completa",
        "subtitle": "Check-in + desabafo + agenda na mesma semana",
        "emoji": "✨",
        "today_task": "Check-in + 1 ação na Agenda",
        "why": "Integrar corpo, mente e dia — o pacote completo de bem-estar.",
        "requirements": [
            {"type": "step", "key": "checkin", "min": 5},
            {"type": "step", "key": "night_dump", "min": 2},
            {"type": "or_steps", "options": [("habit", 2), ("reminder", 2)]},
        ],
        "share_challenge": "Nível 19 ✨ Rotina de bem-estar completa",
        "plan_nudge": None,
    },
    {
        "level": 20,
        "title": "Lenda do cuidado",
        "subtitle": "60 dias ou 20 níveis — você chegou",
        "emoji": "🌟",
        "today_task": "Celebre — e convide alguém a começar",
        "why": "Você provou constância. Agora inspire outros.",
        "requirements": [
            {"type": "or_steps", "options": [("streak", 60), ("invite", 3)]}
        ],
        "share_challenge": "Completei a Jornada 20/20 no EGO-AI 🌟",
        "plan_nudge": None,
    },
]

HANDCRAFTED_MAX = len(JOURNEY_LEVELS)

_STEP_ALIASES = {
    "habit": "habit",
    "night_dump": "night_dump",
    "draft_confirm": "draft_confirm",
    "delegation_confirm": "draft_confirm",
    "reminder": "reminder",
    "chat": "chat",
    "voice": "voice",
    "invite": "invite",
    "checkin": "checkin",
}


def _journey_cap(supabase: Client | None) -> int:
    return progression.get_cap(supabase, "wellness_journey")


def _procedural_level(n: int) -> dict[str, Any]:
    emojis = ("🌱", "💬", "📝", "📅", "🌙", "☀️", "🔥", "💜", "✨", "🌟")
    titles = (
        ("Constância", "Mais um passo de cuidado"),
        ("Conexão", "Fale com seu avatar"),
        ("Organização", "Use a Agenda"),
        ("Desabafo", "Esvazie a mente"),
        ("Hábito", "Marque um hábito"),
        ("Voz", "Mande um áudio"),
        ("Convite", "Traga alguém para o app"),
    )
    t_idx = (n - 1) % len(titles)
    title, subtitle = titles[t_idx]
    chat_need = 1 + max(0, (n - HANDCRAFTED_MAX) // 25)
    voice_need = 1 + max(0, (n - HANDCRAFTED_MAX) // 40)
    streak_need = max(3, n // 12)
    mod = n % 5
    if mod == 0:
        reqs: list[dict[str, Any]] = [{"type": "streak", "min": streak_need}]
    elif mod == 1:
        reqs = [{"type": "step", "key": "chat", "min": chat_need}]
    elif mod == 2:
        reqs = [{"type": "or_steps", "options": [("chat", chat_need), ("checkin", 1)]}]
    elif mod == 3:
        reqs = [{"type": "step", "key": "voice", "min": voice_need}]
    else:
        reqs = [{"type": "or_steps", "options": [("habit", 1), ("reminder", 1)]}]
    return {
        "level": n,
        "title": f"{title} {n}",
        "subtitle": subtitle,
        "emoji": emojis[(n - 1) % len(emojis)],
        "today_task": "Complete os passos de hoje — um de cada vez",
        "why": "Pequenos passos diários constroem bem-estar duradouro.",
        "requirements": reqs,
        "share_challenge": f"Nível {n} do Companheiro de Bolso no EGO-AI 🥚",
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
        if key:
            clean_counts[key] = max(0, int(v or 0))
    return {
        "level": level,
        "step_counts": clean_counts,
        "levels_completed": list(raw.get("levels_completed") or []),
        "show_level_up": bool(raw.get("show_level_up")),
    }


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
                    "label": _step_label(key, need),
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
                    labels.append(f"{need} dias de ofensiva")
                    if have >= int(need):
                        any_done = True
                else:
                    have = counts.get(str(key), 0)
                    labels.append(_step_label(str(key), int(need)))
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
                    "label": f"{need} dias seguidos de cuidado",
                    "done": have >= need,
                    "have": have,
                    "need": need,
                }
            )
    return out


def _step_label(key: str, need: int) -> str:
    labels = {
        "chat": "mensagem no chat" if need == 1 else f"{need} mensagens no chat",
        "voice": "mensagem de voz" if need == 1 else f"{need} mensagens de voz",
        "habit": "hábito marcado",
        "reminder": "lembrete na Agenda",
        "night_dump": "desabafo noturno",
        "draft_confirm": "confirmar desabafo na Agenda",
        "invite": "convidar alguém",
        "checkin": "check-in de hoje",
    }
    base = labels.get(key, key)
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


def _plan_nudge(level_def: dict[str, Any], plan_tier: str) -> str | None:
    if plan_tier and plan_tier != "essential":
        return None
    return level_def.get("plan_nudge")


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
    level = int(state["level"])
    level_def = _level_def(level, cap)
    counts = dict(state["step_counts"])
    complete = _level_complete(level_def, counts, streak_data)
    show_level_up = bool(state.get("show_level_up"))

    if clear_level_up and show_level_up:
        state["show_level_up"] = False
        _save_state(supabase, user_id, state)
        show_level_up = False

    at_max = level >= cap and complete
    companion = _companion_stage(level)
    care_pct = int(round(min(100, max(0, (1.0 if at_max else _progress_for_level(level_def, counts, streak_data)) * 100))))
    return {
        "level": level,
        "max_level": cap,
        "title": level_def["title"],
        "subtitle": level_def["subtitle"],
        "emoji": level_def["emoji"],
        "today_task": level_def["today_task"],
        "why": level_def["why"],
        "progress": 1.0 if at_max else _progress_for_level(level_def, counts, streak_data),
        "level_complete": complete,
        "steps": _steps_status(level_def, counts, streak_data),
        "show_level_up": show_level_up,
        "share_challenge": level_def["share_challenge"],
        "plan_nudge": _plan_nudge(level_def, plan_tier),
        "journey_finished": at_max,
        "companion_stage": companion["stage"],
        "companion_stage_label": companion["label"],
        "companion_sprite_emoji": companion["emoji"],
        "care_percent": care_pct,
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
    counts = dict(state["step_counts"])
    counts[key] = counts.get(key, 0) + 1
    state["step_counts"] = counts

    streak_data = get_streak(supabase, user_id)
    cap = _journey_cap(supabase)
    level_def = _level_def(int(state["level"]), cap)

    if _level_complete(level_def, counts, streak_data):
        completed = list(state.get("levels_completed") or [])
        cur = int(state["level"])
        if cur not in completed:
            completed.append(cur)
        state["levels_completed"] = completed
        if cur < cap:
            state["level"] = cur + 1
            state["step_counts"] = {}
            state["show_level_up"] = True
            try:
                progression.maybe_expand_cap(supabase, "wellness_journey", state["level"])
            except Exception as exc:
                print(f"[EGO] journey expand cap error: {exc}", flush=True)
        else:
            state["show_level_up"] = True

    _save_state(supabase, user_id, state)
    return build_journey_payload(
        supabase, user_id, streak=streak_data, plan_tier=plan_tier
    )


def sync_streak_levels(
    supabase: Client | None, user_id: str, *, plan_tier: str = "essential"
) -> dict[str, Any]:
    """Avança níveis que dependem só da ofensiva (sem novo passo)."""
    if not supabase or not user_id:
        return get_journey(supabase, user_id, plan_tier=plan_tier)
    state = _load_state(supabase, user_id)
    streak_data = get_streak(supabase, user_id)
    cap = _journey_cap(supabase)
    advanced = False
    while True:
        level_def = _level_def(int(state["level"]), cap)
        if not _level_complete(level_def, state["step_counts"], streak_data):
            break
        completed = list(state.get("levels_completed") or [])
        cur = int(state["level"])
        if cur not in completed:
            completed.append(cur)
        state["levels_completed"] = completed
        if cur < cap:
            state["level"] = cur + 1
            state["step_counts"] = {}
            state["show_level_up"] = True
            advanced = True
            try:
                progression.maybe_expand_cap(supabase, "wellness_journey", state["level"])
                cap = _journey_cap(supabase)
            except Exception as exc:
                print(f"[EGO] journey sync expand error: {exc}", flush=True)
        else:
            state["show_level_up"] = True
            break
    if advanced:
        _save_state(supabase, user_id, state)
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
