"""Monstrinhos do Humor — check-in de 1 toque (gamificação de humor)."""

from __future__ import annotations

import datetime
import hashlib

from ego_api import db
from ego_api import progression
from ego_api.daily_care_missions import (
    apply_mission_complete,
    breathe_done_today,
    build_daily_goals,
    has_adventure_today,
    is_goal_done,
    is_mission_allowed_today,
    mission_by_key,
    reset_daily_goals,
)
from ego_api.daily_care_shop import (
    all_decor_ids,
    consumables_payload,
    lookup_consumable,
    lookup_shop_item,
    shop_catalog_payload,
    shop_owned_decor,
)
from ego_api.gentleness import (
    compute_calm_streak,
    compute_survival_streak,
    gentleness_payload,
    mark_calm_day,
    resolve_gentle_mode,
)
from ego_api.request_ctx import get_session
from ego_api.schedule_tz import local_now_from_session

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

MOODS: list[dict[str, str]] = [
    {"key": "heavy", "emoji": "😰", "label": "Nublina"},
    {"key": "anxious", "emoji": "😟", "label": "Agita"},
    {"key": "ok", "emoji": "😐", "label": "Neutro"},
    {"key": "good", "emoji": "🙂", "label": "Sol"},
    {"key": "calm", "emoji": "😌", "label": "Brisa"},
]

GARDEN_STAGES: list[dict[str, str | int]] = [
    {"min_days": 0, "stage": 1, "label": "Semente", "emoji": "🌱"},
    {"min_days": 3, "stage": 2, "label": "Broto", "emoji": "🪴"},
    {"min_days": 7, "stage": 3, "label": "Jardim", "emoji": "🌸"},
    {"min_days": 14, "stage": 4, "label": "Bosque", "emoji": "🌳"},
    {"min_days": 30, "stage": 5, "label": "Paraíso", "emoji": "🌈"},
]

MONSTER_LINES: dict[str, list[str]] = {
    "heavy": [
        "Nublina sente o peso — respira comigo.",
        "Nublina está aqui. Um passo de cada vez.",
        "Nublina precisa de gentileza hoje.",
    ],
    "anxious": [
        "Agita acalma quando você aparece.",
        "Agita tremelicou — você veio cuidar. 💜",
        "Agita fica menor quando você respira fundo.",
    ],
    "ok": [
        "Neutro observa o dia sem pressa.",
        "Neutro está firme no meio do caminho.",
        "Neutro agradece o check-in de hoje.",
    ],
    "good": [
        "Sol brilhou! Seu jardim cresceu. ☀️",
        "Sol está radiante — continue assim!",
        "Sol dançou quando você chegou.",
    ],
    "calm": [
        "Brisa trouxe leveza ao jardim.",
        "Brisa sussurra: você está no caminho.",
        "Brisa deixa tudo mais suave hoje.",
    ],
}

DEFAULT_MONSTER_LINE = "Escolha o monstrinho do seu humor hoje."

SEEDS_CHECKIN = 5
SEEDS_BREATHE = 2
SEEDS_WATER = 2
SEEDS_GRATITUDE = 2
SEEDS_ADVENTURE = 3
SEEDS_ALL_GOALS_BONUS = 3
SEED_HISTORY_MAX = 10
MOOD_JOURNAL_MAX = 42
JOURNAL_NOTE_MAX = 280

# Acolhimento (Finch/Duolingo): proteção de ofensiva ("escudo") — perder 1 dia
# NÃO zera a sequência se você tiver um escudo. Ganha 1 escudo a cada 7 dias (máx 2).
STREAK_SHIELD_EVERY = 7
STREAK_SHIELD_MAX = 2

# Reforço variável (Finch): além da base fixa, um bônus "sorte do dia" que varia
# — nunca punitivo (a base sempre entra), só dá dopamina extra às vezes.
CHECKIN_LUCKY_BONUS_BIG = 3
CHECKIN_LUCKY_BONUS_SMALL = 2

# Evolução do monstrinho (estilo Finch) — níveis SEM fim.
# XP = check-ins*10 + bônus de petiscos/caixas (pet_bonus_xp guardado no raw).
PET_XP_PER_CHECKIN = 10
PET_LEVEL_BASE_NEED = 40  # XP para sair do nível 1
PET_LEVEL_STEP = 15  # cada nível pede um pouco mais (progressão infinita)

# Estágios visíveis por faixa de nível (o nível continua a subir para sempre).
PET_STAGES: list[dict[str, str | int]] = [
    {"min_level": 1, "key": "filhote", "emoji": "🥚", "label": "Filhote"},
    {"min_level": 3, "key": "jovem", "emoji": "🐣", "label": "Jovem"},
    {"min_level": 6, "key": "crescido", "emoji": "🐥", "label": "Crescido"},
    {"min_level": 10, "key": "guardiao", "emoji": "🦉", "label": "Guardião"},
    {"min_level": 16, "key": "lendario", "emoji": "🐉", "label": "Lendário"},
    {"min_level": 25, "key": "mistico", "emoji": "✨", "label": "Místico"},
]


def _pet_level_from_xp(xp: int) -> dict:
    """Nível a partir do XP total — thresholds crescentes, sem teto."""
    xp = max(0, int(xp))
    level = 1
    acc = 0
    need = PET_LEVEL_BASE_NEED
    # Cap defensivo de iterações (nível ~1000) para nunca travar.
    for _ in range(1000):
        if xp < acc + need:
            break
        acc += need
        level += 1
        need += PET_LEVEL_STEP
    into = xp - acc
    stage = PET_STAGES[0]
    for st in PET_STAGES:
        if level >= int(st["min_level"]):
            stage = st
    return {
        "level": level,
        "xp": xp,
        "xp_into_level": into,
        "xp_for_next": need,
        "progress_pct": int(round(100 * into / need)) if need else 0,
        "stage_key": str(stage["key"]),
        "stage_emoji": str(stage["emoji"]),
        "stage_label": str(stage["label"]),
    }


def _pet_payload(raw: dict, total_checkins: int) -> dict:
    bonus = int(raw.get("pet_bonus_xp") or 0)
    xp = int(total_checkins) * PET_XP_PER_CHECKIN + bonus
    pet = _pet_level_from_xp(xp)
    pet["treats_given"] = int(raw.get("treats_given") or 0)
    pet["boxes_opened"] = int(raw.get("boxes_opened") or 0)
    name = str(raw.get("pet_name") or "").strip()
    if name:
        pet["name"] = name[:24]
    return pet

DECOR_UNLOCKS: list[dict[str, str | int]] = [
    {"id": "flowers", "emoji": "🌷", "min_days": 1, "label": "Flores"},
    {"id": "butterfly", "emoji": "🦋", "min_days": 3, "label": "Borboleta"},
    {"id": "fountain", "emoji": "⛲", "min_days": 7, "label": "Fonte"},
    {"id": "treehouse", "emoji": "🏡", "min_days": 14, "label": "Casinha"},
    {"id": "rainbow", "emoji": "🌈", "min_days": 30, "label": "Arco-íris"},
]

def _garden_for_days(days: int) -> dict[str, str | int]:
    picked = GARDEN_STAGES[0]
    for g in GARDEN_STAGES:
        if days >= int(g["min_days"]):
            picked = g
    return {
        "garden_stage": int(picked["stage"]),
        "garden_label": str(picked["label"]),
        "garden_emoji": str(picked["emoji"]),
    }


def _monster_line(mood_key: str, checked_today: bool) -> str:
    if not checked_today or not mood_key:
        return DEFAULT_MONSTER_LINE
    pool = MONSTER_LINES.get(mood_key) or MONSTER_LINES.get("ok", [])
    if not pool:
        return DEFAULT_MONSTER_LINE
    idx = sum(ord(c) for c in _local_date_str()) % len(pool)
    return pool[idx]


def _daily_mission(checked_today: bool, current: int, goals: list[dict]) -> dict[str, str]:
    pending = [g for g in goals if not g.get("done") and not g.get("locked")]
    if pending:
        nxt = pending[0]
        prefix = "Missão surpresa" if nxt.get("surprise") else "Missão"
        return {
            "text": f"{prefix}: {nxt.get('label', 'cuidar do jardim')}",
            "action": str(nxt.get("key") or "checkin"),
        }
    if checked_today:
        return {
            "text": "Tudo feito hoje 💜 Seu monstrinho está tranquilo. Até amanhã.",
            "action": "done",
        }
    if current >= 1:
        return {
            "text": "Seu monstrinho te espera 💜 Conte como você está — 1 toque.",
            "action": "checkin",
        }
    return {
        "text": "Conheça seu monstrinho: conte como você está hoje 💜",
        "action": "checkin",
    }


def _decor_unlocked(current: int) -> list[dict[str, str | int]]:
    return [
        {
            "id": str(d["id"]),
            "emoji": str(d["emoji"]),
            "label": str(d["label"]),
            "min_days": int(d["min_days"]),
        }
        for d in DECOR_UNLOCKS
        if current >= int(d["min_days"])
    ]


def _daily_goals(raw: dict, today: str, checked_today: bool) -> list[dict]:
    gentle = resolve_gentle_mode(raw, today) if checked_today else False
    return build_daily_goals(
        raw,
        today,
        checked_today,
        checkin_seeds=SEEDS_CHECKIN,
        gentle_mode=gentle,
    )


def _adventure_payload(raw: dict, today: str, checked_today: bool) -> dict:
    if not checked_today or not has_adventure_today(today):
        return {
            "active": False,
            "progress": 0,
            "title": "",
            "subtitle": "",
            "can_collect": False,
            "collected": False,
            "reward_seeds": SEEDS_ADVENTURE,
        }
    breathe_done = breathe_done_today(raw, today)
    collected = is_goal_done(raw, today, "adventure")
    progress = 100 if collected else (66 if breathe_done else 33)
    return {
        "active": not collected,
        "progress": progress,
        "title": "Aventura no jardim" if not collected else "Aventura concluída!",
        "subtitle": (
            "Monstrinho voltou com surpresas!"
            if collected
            else (
                "Respire e busque o monstrinho para a recompensa."
                if breathe_done
                else "Monstrinho saiu explorar… respire fundo para ajudar."
            )
        ),
        "can_collect": breathe_done and not collected,
        "collected": collected,
        "reward_seeds": SEEDS_ADVENTURE,
    }


def _shop_owned_ids(raw: dict) -> list[str]:
    owned = raw.get("shop_owned")
    if not isinstance(owned, list):
        return []
    return [str(x).strip() for x in owned if str(x).strip()]


def _append_seed_history(raw: dict, action: str, amount: int, label: str) -> None:
    hist = raw.get("seed_history")
    if not isinstance(hist, list):
        hist = []
    entry = {
        "action": action[:12],
        "amount": int(amount),
        "label": str(label)[:48],
        "date": _local_date_str(),
    }
    hist = [entry, *[h for h in hist if isinstance(h, dict)]]
    raw["seed_history"] = hist[:SEED_HISTORY_MAX]


def _seed_history_payload(raw: dict) -> list[dict]:
    hist = raw.get("seed_history")
    if not isinstance(hist, list):
        return []
    out: list[dict] = []
    for h in hist[:SEED_HISTORY_MAX]:
        if not isinstance(h, dict):
            continue
        out.append(
            {
                "action": str(h.get("action") or ""),
                "amount": int(h.get("amount") or 0),
                "label": str(h.get("label") or ""),
                "date": str(h.get("date") or ""),
            }
        )
    return out


def _append_mood_journal(raw: dict, date: str, mood: dict, note: str | None = None) -> None:
    hist = raw.get("mood_journal")
    if not isinstance(hist, list):
        hist = []
    existing_note = ""
    for h in hist:
        if isinstance(h, dict) and str(h.get("date") or "") == date:
            existing_note = str(h.get("note") or "").strip()
            break
    entry = {
        "date": date,
        "mood": str(mood.get("key") or ""),
        "emoji": str(mood.get("emoji") or ""),
        "label": str(mood.get("label") or ""),
    }
    final_note = note if note is not None else existing_note
    if final_note:
        entry["note"] = str(final_note).strip()[:JOURNAL_NOTE_MAX]
    hist = [h for h in hist if isinstance(h, dict) and str(h.get("date") or "") != date]
    hist.insert(0, entry)
    raw["mood_journal"] = hist[:MOOD_JOURNAL_MAX]


def _mood_journal_payload(raw: dict) -> list[dict]:
    hist = raw.get("mood_journal")
    if not isinstance(hist, list):
        return []
    out: list[dict] = []
    for h in hist[:MOOD_JOURNAL_MAX]:
        if not isinstance(h, dict):
            continue
        date = str(h.get("date") or "").strip()
        if not date:
            continue
        mood_key = str(h.get("mood") or "").strip()
        mood = _mood_by_key(mood_key) if mood_key else None
        row = {
            "date": date,
            "mood": mood_key,
            "emoji": mood["emoji"] if mood else str(h.get("emoji") or ""),
            "label": mood["label"] if mood else str(h.get("label") or ""),
        }
        note = str(h.get("note") or "").strip()
        if note:
            row["note"] = note[:JOURNAL_NOTE_MAX]
        out.append(row)
    return out


def _all_goals_done(goals: list[dict]) -> bool:
    return bool(goals) and all(bool(g.get("done")) for g in goals)


def _avatar_congrats_line(supabase: Client | None, user_id: str, raw: dict, today: str) -> str | None:
    """Frase do avatar quando completou todas as missões do jardim hoje."""
    if str(raw.get("all_goals_bonus_date") or "") != today:
        return None
    from ego_api.persona import assistant_display_name_for_avatar

    stored_a, _ = db.load_persona(supabase, user_id)
    name = assistant_display_name_for_avatar(stored_a or "f1")
    return (
        f"{name} viu que você completou as missões do jardim hoje — orgulho de você. "
        "Quer desabafar um pouco comigo?"
    )


def _maybe_all_goals_bonus(raw: dict, today: str) -> bool:
    goals = _daily_goals(raw, today, True)
    if not _all_goals_done(goals):
        return False
    if str(raw.get("all_goals_bonus_date") or "") == today:
        return False
    raw["all_goals_bonus_date"] = today
    raw["seeds"] = int(raw.get("seeds") or 0) + SEEDS_ALL_GOALS_BONUS
    _append_seed_history(raw, "bonus", SEEDS_ALL_GOALS_BONUS, "Dia perfeito no jardim")
    return True


DAILY_QUESTIONS: list[str] = [
    "Como está sua mente agora?",
    "Quanto a ansiedade apertou hoje?",
    "Como você dormiu?",
    "O que mais pesou na cabeça?",
    "De 0 a 10, quanto precisa desabafar?",
    "Como está seu corpo agora?",
    "O que você precisa hoje?",
    "Conseguiu respirar fundo hoje?",
    "Algo te preocupou demais?",
    "Como foi sua manhã?",
    "Você foi gentil consigo hoje?",
    "O que te acalmou hoje?",
    "Precisa organizar a cabeça?",
    "Como está sua energia?",
]


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


def _lucky_bonus(user_id: str, today: str) -> int:
    """Reforço variável (Finch): bônus surpresa estável no dia, nunca punitivo."""
    seed = f"{user_id}:{today}:luck".encode()
    r = int(hashlib.md5(seed).hexdigest(), 16) % 100
    if r < 15:
        return CHECKIN_LUCKY_BONUS_BIG  # ~15% dias de sorte
    if r < 45:
        return CHECKIN_LUCKY_BONUS_SMALL  # ~30% bônus pequeno
    return 0  # ~55% só a base (sem punição)


def _maybe_award_shield(raw: dict, current: int) -> bool:
    """Ganha 1 escudo de ofensiva a cada 7 dias (máx 2). Acolhimento, não punição."""
    if current <= 0 or current % STREAK_SHIELD_EVERY != 0:
        return False
    mark = current // STREAK_SHIELD_EVERY
    last_mark = int(raw.get("shield_last_mark") or 0)
    if mark <= last_mark:
        return False
    held = int(raw.get("shields") or 0)
    raw["shield_last_mark"] = mark
    if held >= STREAK_SHIELD_MAX:
        return False
    raw["shields"] = held + 1
    return True


def _streak_message(current: int, checked_today: bool, shields: int) -> str:
    """Mensagem de acolhimento sobre a ofensiva (sem vergonha, sem cobrança)."""
    if checked_today:
        if current >= 30:
            return f"{current} dias juntos 💜 Seu monstrinho confia em você."
        if current >= 7:
            return f"{current} dias de carinho 🌸 Vocês dois estão crescendo."
        if current >= 1:
            return f"Dia {current} com seu monstrinho 🌱 Um de cada vez."
        return "Seu monstrinho está feliz por você aparecer 💜"
    if current >= 1 and shields > 0:
        return (
            f"Se hoje for difícil, tá tudo bem — você tem "
            f"{shields} escudo{'s' if shields > 1 else ''} guardando sua sequência 🛡️"
        )
    if current >= 1:
        return "Seu monstrinho sente sua falta 💜 Um toque já basta hoje."
    return "Comece devagar: conte como você está hoje 💜"


def question_for_today(local_date: str | None = None) -> dict:
    today = local_date or _local_date_str()
    try:
        dt = datetime.datetime.strptime(today, "%Y-%m-%d").date()
        idx = dt.toordinal() % len(DAILY_QUESTIONS)
    except ValueError:
        idx = 0
    return {
        "index": idx + 1,
        "total": len(DAILY_QUESTIONS),
        "text": DAILY_QUESTIONS[idx],
    }


def _mood_by_key(key: str) -> dict[str, str]:
    k = (key or "").strip().lower()
    for m in MOODS:
        if m["key"] == k:
            return m
    return MOODS[2]

# Marcos visíveis no ranking (1 → 3 → 7 → 14 → 30 dias).
CARE_MILESTONES: list[dict[str, str | int]] = [
    {"min_days": 1, "emoji": "🌱", "label": "Iniciante"},
    {"min_days": 3, "emoji": "💪", "label": "Firme"},
    {"min_days": 7, "emoji": "🔥", "label": "Forte"},
    {"min_days": 14, "emoji": "⭐", "label": "Mestre"},
    {"min_days": 30, "emoji": "👑", "label": "Lenda"},
]
# Retrocompat (regression_guard)
CARE_TIERS = CARE_MILESTONES


def _tier_for_days(days: int, cap: int) -> dict:
    tier = progression.daily_tier_from_days(days, cap)
    emoji, label = progression.daily_tier_meta(tier)
    next_tier = tier + 1 if tier < cap else None
    next_label = progression.daily_tier_meta(next_tier)[1] if next_tier else None
    return {
        "tier_index": tier,
        "tier_total": cap,
        "tier_emoji": emoji,
        "tier_label": label,
        "next_tier_days": next_tier,
        "next_tier_label": next_label,
    }


def _ranking_payload(
    supabase: Client | None, current: int, longest: int
) -> dict:
    cap = progression.get_cap(supabase, "daily_care")
    tier = _tier_for_days(current, cap)
    top = _community_top_days()
    next_days = tier.get("next_tier_days")
    days_to_next = (int(next_days) - current) if next_days else 0
    challenge = (
        f"Faltam {days_to_next} dia(s) para nível {tier.get('next_tier_label')}"
        if days_to_next > 0 and tier.get("next_tier_label")
        else (
            f"Você está no topo ({cap} níveis) — desafie alguém a chegar em {top} dias"
            if current >= cap
            else f"Meta da comunidade: {top} dias · escada até {cap} níveis"
        )
    )
    return {
        **tier,
        "personal_best": longest,
        "community_top_days": top,
        "days_to_next_tier": max(0, days_to_next),
        "challenge_line": challenge,
        "ladder": progression.daily_ladder_window(tier["tier_index"], cap),
        "milestones": [
            {
                "min_days": int(t["min_days"]),
                "emoji": str(t["emoji"]),
                "label": str(t["label"]),
                "reached": current >= int(t["min_days"]),
            }
            for t in CARE_MILESTONES
        ],
    }


def _community_top_days() -> int:
    from ego_api.config import read_env

    try:
        return max(7, int(read_env("EGO_DAILY_CARE_COMMUNITY_TOP", "21")))
    except ValueError:
        return 21


def _load_raw(supabase: Client | None, user_id: str) -> dict:
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = ui.get("daily_care")
    return dict(raw) if isinstance(raw, dict) else {}


def get_daily_care(supabase: Client | None, user_id: str) -> dict:
    today = _local_date_str()
    raw = _load_raw(supabase, user_id)
    last = str(raw.get("last_date") or "").strip()
    current = int(raw.get("current") or 0)
    longest = int(raw.get("longest") or 0)
    last_mood = str(raw.get("last_mood") or "")
    mood = _mood_by_key(last_mood) if last_mood else MOODS[2]
    checked_today = last == today
    q = question_for_today(today)
    longest_eff = max(longest, current)
    if longest_eff > 0:
        try:
            progression.maybe_expand_cap(supabase, "daily_care", longest_eff)
        except Exception:
            pass
    ranking = _ranking_payload(supabase, current, longest_eff)
    garden = _garden_for_days(max(current, 1 if checked_today else 0))
    goals = _daily_goals(raw, today, checked_today)
    mission = _daily_mission(checked_today, current, goals)
    seeds = int(raw.get("seeds") or 0)
    shop_payload = shop_catalog_payload(raw, seeds)
    all_done = _all_goals_done(goals) if checked_today else False
    journal = _mood_journal_payload(raw)
    try:
        local_hour = local_now_from_session(get_session()).hour
    except Exception:
        local_hour = 12
    gentle_block = gentleness_payload(
        raw,
        today=today,
        checked_today=checked_today,
        last_mood=last_mood if checked_today else "",
        journal=journal,
        local_hour=local_hour,
    )
    payload = {
        "current": current,
        "longest": longest_eff,
        "last_date": last,
        "checked_today": checked_today,
        "at_risk": bool(current >= 1 and not checked_today),
        "shields": int(raw.get("shields") or 0),
        "streak_message": _streak_message(
            current, checked_today, int(raw.get("shields") or 0)
        ),
        "last_mood": last_mood,
        "last_mood_emoji": mood["emoji"],
        "last_mood_label": mood["label"],
        "total_checkins": int(raw.get("total_checkins") or 0),
        "question": q,
        "moods": MOODS,
        "can_share": checked_today,
        "share_hook": _share_hook(current, checked_today, ranking),
        "ranking": ranking,
        "garden_stage": garden["garden_stage"],
        "garden_label": garden["garden_label"],
        "garden_emoji": garden["garden_emoji"],
        "monster_line": _monster_line(last_mood if checked_today else "", checked_today),
        "daily_mission": mission["text"],
        "daily_mission_action": mission["action"],
        "seeds": seeds,
        "decor_unlocked": _decor_unlocked(max(current, longest_eff)),
        "daily_goals": goals,
        "adventure": _adventure_payload(raw, today, checked_today),
        "shop_items": shop_payload["shop_items"],
        "shop_owned": shop_owned_decor(raw),
        "shop_week_label": shop_payload["shop_week_label"],
        "shop_rotation_reset": shop_payload["shop_rotation_reset"],
        "shop_base_complete": shop_payload["shop_base_complete"],
        "shop_rotating_available": shop_payload["shop_rotating_available"],
        "seed_history": _seed_history_payload(raw),
        "mood_journal": journal,
        "all_goals_done": all_done,
        "all_goals_bonus": SEEDS_ALL_GOALS_BONUS,
        "gentleness": gentle_block,
        "pet": _pet_payload(raw, int(raw.get("total_checkins") or 0)),
        "consumables": consumables_payload(seeds),
    }
    last_box = raw.get("last_box_reward")
    if isinstance(last_box, dict) and last_box:
        payload["last_box_reward"] = {
            "kind": str(last_box.get("kind") or ""),
            "emoji": str(last_box.get("emoji") or "🎁"),
            "label": str(last_box.get("label") or ""),
            "amount": int(last_box.get("amount") or 0),
        }
    congrats = _avatar_congrats_line(supabase, user_id, raw, today)
    if congrats:
        payload["avatar_congrats"] = congrats
    try:
        from ego_api import mood_quiz, mood_social, seasonal_events

        event = seasonal_events.get_active_event()
        if event:
            payload["seasonal_event"] = event
        payload["weekly_quiz"] = mood_quiz.get_quiz(supabase, user_id)
        payload["social_invite"] = mood_social.invite_payload(supabase, user_id)
    except Exception:
        pass
    return payload


def award_quiz_seeds(
    supabase: Client | None, user_id: str, *, amount: int = 5
) -> dict:
    """Recompensa sementes pelo quiz semanal (Fase 10)."""
    if not supabase or not user_id:
        return get_daily_care(supabase, user_id)
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = _load_raw(supabase, user_id)
    reward = max(0, int(amount))
    raw["seeds"] = int(raw.get("seeds") or 0) + reward
    _append_seed_history(raw, "quiz", reward, "Quiz semanal")
    ui["daily_care"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})
    return get_daily_care(supabase, user_id)


def _share_hook(current: int, checked_today: bool, ranking: dict) -> str:
    if not checked_today:
        return "Seu monstrinho sente sua falta 💜 Um toque cuida de você hoje."
    tier = f"{ranking.get('tier_emoji', '')} {ranking.get('tier_label', '')}".strip()
    if current <= 1:
        return "Dia 1 com seu monstrinho 🌱 Mostre pra alguém que precisa de um sorriso."
    if ranking.get("days_to_next_tier", 0) > 0:
        return (
            f"{current} dias de carinho · {tier} — "
            f"faltam {ranking['days_to_next_tier']} para {ranking.get('next_tier_label')}. Leve alguém junto 💜"
        )
    return f"{current} dias cuidando de você · {tier}. Convide um amigo pra esse cantinho calmo 💜"


def record_checkin(
    supabase: Client | None,
    user_id: str,
    mood_key: str,
    note: str | None = None,
) -> dict:
    if not supabase or not user_id:
        return get_daily_care(supabase, user_id)
    mood = _mood_by_key(mood_key)
    today = _local_date_str()
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = dict(ui.get("daily_care") if isinstance(ui.get("daily_care"), dict) else {})
    last = str(raw.get("last_date") or "").strip()
    current = int(raw.get("current") or 0)
    longest = int(raw.get("longest") or 0)
    total = int(raw.get("total_checkins") or 0)
    seeds = int(raw.get("seeds") or 0)
    lucky = 0
    streak_protected = False
    shield_earned = False

    if last == today:
        raw.update(
            {
                "last_mood": mood["key"],
                "last_mood_emoji": mood["emoji"],
                "last_mood_label": mood["label"],
            }
        )
        _append_mood_journal(raw, today, mood, note=note)
    else:
        yesterday = _yesterday(today)
        day_before = _yesterday(yesterday)
        shields_held = int(raw.get("shields") or 0)
        streak_protected = False
        if last == yesterday and current > 0:
            current += 1
        elif last == day_before and current > 0 and shields_held > 0:
            # Acolhimento: faltou 1 dia mas o escudo segura a ofensiva.
            raw["shields"] = shields_held - 1
            current += 1
            streak_protected = True
        else:
            current = 1
        longest = max(longest, current)
        total += 1
        lucky = _lucky_bonus(user_id, today)
        seeds += SEEDS_CHECKIN + lucky
        _append_seed_history(raw, "earn", SEEDS_CHECKIN, "Check-in de humor")
        if lucky > 0:
            _append_seed_history(raw, "bonus", lucky, "Bônus surpresa 🍀")
        raw.update(
            {
                "current": current,
                "longest": longest,
                "last_date": today,
                "last_mood": mood["key"],
                "last_mood_emoji": mood["emoji"],
                "last_mood_label": mood["label"],
                "total_checkins": total,
                "seeds": seeds,
            }
        )
        shield_earned = _maybe_award_shield(raw, current)
        _append_mood_journal(raw, today, mood, note=note)
        reset_daily_goals(raw)

    ui["daily_care"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})

    try:
        progression.maybe_expand_cap(
            supabase, "daily_care", max(current, longest)
        )
    except Exception as exc:
        print(f"[EGO] daily_care expand cap error: {exc}", flush=True)

    try:
        from ego_api import streaks, wellness_journey

        streaks.record_streak_activity(supabase, user_id, source="checkin")
        prof2 = db.load_profile(supabase, user_id) or {}
        tier, _ = db.user_plan_limits(prof2)
        wellness_journey.record_step(supabase, user_id, "checkin", plan_tier=tier)
    except Exception as exc:
        print(f"[EGO] daily_care journey step error: {exc}", flush=True)

    care = get_daily_care(supabase, user_id)
    if lucky > 0:
        care["checkin_bonus"] = int(lucky)
    if streak_protected:
        care["streak_protected"] = True
    if shield_earned:
        care["shield_earned"] = True
    return care


def record_journal_note(
    supabase: Client | None,
    user_id: str,
    note: str,
) -> dict:
    if not supabase or not user_id:
        return get_daily_care(supabase, user_id)
    today = _local_date_str()
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = dict(ui.get("daily_care") if isinstance(ui.get("daily_care"), dict) else {})
    if str(raw.get("last_date") or "").strip() != today:
        return get_daily_care(supabase, user_id)
    mood_key = str(raw.get("last_mood") or "calm").strip() or "calm"
    mood = _mood_by_key(mood_key)
    cleaned = str(note or "").strip()[:JOURNAL_NOTE_MAX]
    _append_mood_journal(raw, today, mood, note=cleaned)
    ui["daily_care"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})
    return get_daily_care(supabase, user_id)


def record_goal(
    supabase: Client | None,
    user_id: str,
    goal_key: str,
) -> dict:
    if not supabase or not user_id:
        return get_daily_care(supabase, user_id)
    today = _local_date_str()
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = dict(ui.get("daily_care") if isinstance(ui.get("daily_care"), dict) else {})
    last = str(raw.get("last_date") or "").strip()
    if last != today:
        return get_daily_care(supabase, user_id)

    key = (goal_key or "").strip().lower()[:24]
    mission = mission_by_key(key)
    if not mission or not is_mission_allowed_today(raw, today, key):
        return get_daily_care(supabase, user_id)
    if is_goal_done(raw, today, key):
        return get_daily_care(supabase, user_id)

    kind = str(mission.get("kind") or "tap")
    if kind == "adventure" and not breathe_done_today(raw, today):
        return get_daily_care(supabase, user_id)

    seeds = int(raw.get("seeds") or 0)
    reward = apply_mission_complete(raw, today, mission)
    if reward <= 0:
        return get_daily_care(supabase, user_id)
    if kind == "breathe":
        mark_calm_day(raw, today)
    raw["seeds"] = seeds + reward
    label = str(mission.get("label") or key)
    _append_seed_history(raw, "earn", reward, label[:48])
    bonus_granted = _maybe_all_goals_bonus(raw, today)

    ui["daily_care"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})
    care = get_daily_care(supabase, user_id)
    if bonus_granted:
        care["goals_bonus_granted"] = True
        line = _avatar_congrats_line(supabase, user_id, raw, today)
        if line:
            care["avatar_congrats"] = line
    return care


def record_calm_mark(supabase: Client | None, user_id: str) -> dict:
    """Marca dia calmo (PAUSA inline no jardim) — sequência calma em dias difíceis."""
    if not supabase or not user_id:
        return get_daily_care(supabase, user_id)
    today = _local_date_str()
    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = dict(ui.get("daily_care") if isinstance(ui.get("daily_care"), dict) else {})
    if str(raw.get("last_date") or "").strip() != today:
        return get_daily_care(supabase, user_id)
    mark_calm_day(raw, today)
    journal = _mood_journal_payload(raw)
    calm = compute_calm_streak(raw, journal)
    survival = compute_survival_streak(raw, journal)
    if calm["current"] > int(raw.get("calm_streak_longest") or 0):
        raw["calm_streak_longest"] = calm["current"]
    if survival["current"] > int(raw.get("survival_streak_longest") or 0):
        raw["survival_streak_longest"] = survival["current"]
    ui["daily_care"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})
    return get_daily_care(supabase, user_id)


def purchase_shop_item(
    supabase: Client | None,
    user_id: str,
    item_id: str,
) -> dict:
    if not supabase or not user_id:
        return get_daily_care(supabase, user_id)
    iid = (item_id or "").strip().lower()[:24]
    item = lookup_shop_item(iid)
    if not item:
        return get_daily_care(supabase, user_id)

    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = dict(ui.get("daily_care") if isinstance(ui.get("daily_care"), dict) else {})
    owned = _shop_owned_ids(raw)
    if iid in owned:
        return get_daily_care(supabase, user_id)

    price = int(item["price"])
    seeds = int(raw.get("seeds") or 0)
    if seeds < price:
        return get_daily_care(supabase, user_id)

    raw["seeds"] = seeds - price
    raw["shop_owned"] = owned + [iid]
    _append_seed_history(raw, "spend", price, f"Loja: {item['label']}")

    ui["daily_care"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})
    return get_daily_care(supabase, user_id)


def _grant_box_reward(raw: dict) -> dict:
    """Caixa surpresa — decoração nova por gastar, senão amêndoas bônus."""
    import secrets

    owned = set(_shop_owned_ids(raw))
    unowned = [iid for iid in all_decor_ids() if iid not in owned]
    # 60% decor nova (se houver), senão sempre amêndoas — nunca "vazia".
    if unowned and secrets.randbelow(100) < 60:
        pick = unowned[secrets.randbelow(len(unowned))]
        item = lookup_shop_item(pick)
        raw["shop_owned"] = _shop_owned_ids(raw) + [pick]
        label = str(item["label"]) if item else "Decoração"
        emoji = str(item["emoji"]) if item else "🎁"
        return {"kind": "decor", "emoji": emoji, "label": label, "amount": 0}
    bonus = 6 + secrets.randbelow(12)  # 6–17 amêndoas
    raw["seeds"] = int(raw.get("seeds") or 0) + bonus
    _append_seed_history(raw, "box", bonus, "Caixa surpresa")
    return {"kind": "seeds", "emoji": "🌰", "label": "Amêndoas bônus", "amount": bonus}


def purchase_consumable(
    supabase: Client | None,
    user_id: str,
    item_id: str,
) -> dict:
    """Compra REPETÍVEL (petisco / caixa surpresa) — o gasto nunca acaba."""
    if not supabase or not user_id:
        return get_daily_care(supabase, user_id)
    item = lookup_consumable(item_id)
    if not item:
        return get_daily_care(supabase, user_id)

    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001
    raw = dict(ui.get("daily_care") if isinstance(ui.get("daily_care"), dict) else {})

    price = int(item["price"])
    seeds = int(raw.get("seeds") or 0)
    if seeds < price:
        return get_daily_care(supabase, user_id)

    raw["seeds"] = seeds - price
    raw["pet_bonus_xp"] = int(raw.get("pet_bonus_xp") or 0) + int(item.get("xp") or 0)
    kind = str(item["kind"])
    raw.pop("last_box_reward", None)

    if kind == "treat":
        raw["treats_given"] = int(raw.get("treats_given") or 0) + 1
        _append_seed_history(raw, "spend", price, f"{item['label']}")
    elif kind == "box":
        raw["boxes_opened"] = int(raw.get("boxes_opened") or 0) + 1
        _append_seed_history(raw, "spend", price, f"{item['label']}")
        raw["last_box_reward"] = _grant_box_reward(raw)

    ui["daily_care"] = raw
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})
    return get_daily_care(supabase, user_id)
