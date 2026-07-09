"""Jardim da Gentileza — modo suave, espelho emocional e ponte PAUSA (Monstrinhos)."""

from __future__ import annotations

from typing import Any

STRESS_MOOD_KEYS = frozenset({"heavy", "anxious"})
CALM_MOOD_KEYS = frozenset({"calm", "good"})
POSITIVE_MOOD_KEYS = frozenset({"calm", "good", "ok"})

# Missões leves — evidência: respiração + autocuidado mínimo (sem exigir produtividade).
GENTLE_REGULAR_KEYS: tuple[str, ...] = (
    "breathe",
    "calm_breath",
    "pause",
    "gratitude",
    "kind_self",
    "music",
    "hydrate",
    "note",
)

GENTLE_SURPRISE: dict[str, str | int | bool] = {
    "key": "surprise_gentle_day",
    "label": "Surpresa: dia permitido ficar mal",
    "emoji": "🫂",
    "seeds_reward": 4,
    "kind": "tap",
    "surprise": True,
}

MIRROR_LINES: dict[str, list[str]] = {
    "heavy_week": [
        "Nublina viu uma semana pesada — aqui não há cobrança.",
        "Vários dias nublados: modo gentil ligado. Um passo de cada vez.",
        "Seu monstrinho espelha o peso da semana — respire, não se culpe.",
    ],
    "anxious_week": [
        "Agita percebeu ansiedade frequente — vamos devagar hoje.",
        "Semana agitada: PAUSA e respiração vêm antes das missões.",
        "Corpo em alerta? Seu jardim fica mais suave agora.",
    ],
    "mixed_stress": [
        "Semana mista e difícil — gentileza primeiro, metas depois.",
        "Seu espelho emocional mostra altos e baixos: tudo bem não estar bem.",
    ],
    "calm_return": [
        "Brisa voltou {n} vezes — seu corpo já sabe acalmar.",
        "{n} momentos mais leves esta semana. Pequeno, mas real.",
    ],
    "lonely_note": [
        "Guardei o que você escreveu — não precisa falar com ninguém agora.",
        "Sua carta ficou com o monstrinho. Silêncio também é cuidado.",
    ],
    "lonely_sunday": [
        "Domingo pode pesar — aqui não precisa fingir que está bem.",
        "Domingo sozinha é difícil. O jardim fica suave hoje.",
    ],
    "lonely_night": [
        "Madrugada difícil? PAUSA 60s — você não precisa desabafar agora.",
        "3h da manhã permitido. Respire antes de qualquer conversa.",
    ],
    "first_stress_today": [
        "Hoje pesa — PAUSA de 60s está aqui, sem julgamento.",
        "Dia difícil permitido. Respire antes de qualquer missão.",
    ],
}

CVV_LINE = "CVV 188 — se precisar de alguém agora, ligue."

LONELY_KEYWORDS = frozenset(
    {
        "sozin",
        "solidão",
        "solidao",
        "sozinh",
        "ninguém",
        "ninguem",
        "madrugada",
        "domingo",
        "cabeça não para",
        "cabeca nao para",
        "desabaf",
        "chor",
        "vazio",
        "não aguento",
        "nao aguento",
    }
)


def note_signals_lonely(note: str) -> bool:
    text = (note or "").strip().lower()
    if not text:
        return False
    return any(kw in text for kw in LONELY_KEYWORDS)


def is_sunday_garden(local_date: str) -> bool:
    try:
        import datetime as dt

        return dt.datetime.strptime(local_date, "%Y-%m-%d").date().weekday() == 6
    except ValueError:
        return False


def _journal_slice(journal: list[dict[str, Any]], days: int = 7) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in journal:
        if not isinstance(row, dict):
            continue
        date = str(row.get("date") or "").strip()
        if not date:
            continue
        out.append(row)
        if len(out) >= days:
            break
    return out


def gentle_mode_active(last_mood: str, journal: list[dict[str, Any]]) -> bool:
    mood = (last_mood or "").strip().lower()
    if mood in STRESS_MOOD_KEYS:
        return True
    week = _journal_slice(journal, 7)
    stress_days = sum(
        1 for e in week if str(e.get("mood") or "").strip().lower() in STRESS_MOOD_KEYS
    )
    if stress_days >= 3:
        return True
    for entry in week:
        if note_signals_lonely(str(entry.get("note") or "")):
            return True
    return False


def resolve_gentle_mode(raw: dict[str, Any], today: str) -> bool:
    last = str(raw.get("last_date") or "").strip()
    if last != today:
        return False
    last_mood = str(raw.get("last_mood") or "").strip().lower()
    journal = raw.get("mood_journal")
    if not isinstance(journal, list):
        journal = []
    return gentle_mode_active(last_mood, journal)


def _pick_line(pool_key: str, salt: str, **fmt: Any) -> str:
    pool = MIRROR_LINES.get(pool_key) or MIRROR_LINES["first_stress_today"]
    idx = sum(ord(c) for c in salt) % len(pool)
    line = pool[idx]
    if fmt:
        try:
            return line.format(**fmt)
        except (KeyError, ValueError):
            return line
    return line


def mirror_line(
    journal: list[dict[str, Any]],
    *,
    last_mood: str,
    today: str,
    checked_today: bool,
    local_hour: int = 12,
) -> str:
    if not checked_today:
        return ""
    week = _journal_slice(journal, 7)
    if not week:
        return _pick_line("first_stress_today", today)

    if is_sunday_garden(today):
        for entry in week:
            if str(entry.get("date") or "") == today:
                note = str(entry.get("note") or "")
                mood = str(entry.get("mood") or "").strip().lower()
                if note_signals_lonely(note) or mood in STRESS_MOOD_KEYS:
                    return _pick_line("lonely_sunday", f"{today}:sun")

    for entry in week:
        if str(entry.get("date") or "") == today and str(entry.get("note") or "").strip():
            note = str(entry.get("note") or "")
            if note_signals_lonely(note):
                if local_hour >= 22 or local_hour < 5:
                    return _pick_line("lonely_night", f"{today}:night")
                return _pick_line("lonely_note", f"{today}:note")

    mood = (last_mood or "").strip().lower()
    heavy_n = sum(1 for e in week if str(e.get("mood") or "") == "heavy")
    anxious_n = sum(1 for e in week if str(e.get("mood") or "") == "anxious")
    calm_n = sum(1 for e in week if str(e.get("mood") or "") in CALM_MOOD_KEYS)

    if mood in STRESS_MOOD_KEYS:
        return _pick_line("first_stress_today", f"{today}:{mood}")
    if heavy_n >= 3:
        return _pick_line("heavy_week", today)
    if anxious_n >= 3:
        return _pick_line("anxious_week", today)
    if heavy_n + anxious_n >= 3:
        return _pick_line("mixed_stress", today)
    if calm_n >= 2:
        return _pick_line("calm_return", today, n=calm_n)
    return ""


def _calm_marks(raw: dict[str, Any]) -> dict[str, bool]:
    marks = raw.get("calm_marks")
    if not isinstance(marks, dict):
        return {}
    return {str(k): bool(v) for k, v in marks.items() if str(k).strip()}


def mark_calm_day(raw: dict[str, Any], today: str) -> None:
    marks = _calm_marks(raw)
    marks[today] = True
    raw["calm_marks"] = marks


def _is_calm_day_entry(entry: dict[str, Any], marks: dict[str, bool]) -> bool:
    date = str(entry.get("date") or "").strip()
    mood = str(entry.get("mood") or "").strip().lower()
    if mood in CALM_MOOD_KEYS:
        return True
    if mood in STRESS_MOOD_KEYS and marks.get(date):
        return True
    return False


def compute_survival_streak(raw: dict[str, Any], journal: list[dict[str, Any]]) -> dict[str, int]:
    """Dias difíceis (Nublina/Agita) em que fez PAUSA no jardim."""
    marks = _calm_marks(raw)
    current = 0
    for entry in journal:
        if not isinstance(entry, dict):
            continue
        mood = str(entry.get("mood") or "").strip().lower()
        date = str(entry.get("date") or "").strip()
        if mood in STRESS_MOOD_KEYS and marks.get(date):
            current += 1
        else:
            break
    stored = int(raw.get("survival_streak_longest") or 0)
    longest = max(stored, current)
    return {"current": current, "longest": longest}


def survival_streak_line(current: int) -> str:
    if current <= 0:
        return ""
    if current == 1:
        return "1 dia difícil com PAUSA — você cuidou de si"
    return f"{current} dias difíceis com PAUSA — sequência de sobrevivência"


def compute_calm_streak(raw: dict[str, Any], journal: list[dict[str, Any]]) -> dict[str, int]:
    marks = _calm_marks(raw)
    current = 0
    for entry in journal:
        if not isinstance(entry, dict):
            continue
        if _is_calm_day_entry(entry, marks):
            current += 1
        else:
            break
    stored_longest = int(raw.get("calm_streak_longest") or 0)
    longest = max(stored_longest, current)
    return {"current": current, "longest": longest}


def crisis_bridge(
    last_mood: str,
    checked_today: bool,
    *,
    lonely_note: bool = False,
    local_hour: int = 12,
) -> dict[str, Any]:
    mood = (last_mood or "").strip().lower()
    night = local_hour >= 22 or local_hour < 5
    show = checked_today and (mood in STRESS_MOOD_KEYS or lonely_note)
    subtitle = "Respiração lenta — recomendada em momentos de ansiedade aguda."
    if lonely_note and night:
        subtitle = "Madrugada difícil? 60s no corpo — falar é opcional depois."
    elif lonely_note:
        subtitle = "Solidão pesa — PAUSA no corpo antes de qualquer conversa."
    chat_draft = ""
    if show:
        if lonely_note:
            chat_draft = (
                "Escrevi uma carta no jardim e fiz a PAUSA. "
                "Não quero desabafar muito — só um pouco de companhia agora."
            )
        else:
            chat_draft = (
                "Marquei Nublina/Agita no jardim e fiz a PAUSA. "
                "Quero falar sobre como estou me sentindo agora."
            )
    return {
        "show": show,
        "title": "PAUSA 60s",
        "subtitle": subtitle,
        "exercise_key": "breath44",
        "duration_seconds": 60,
        "cvv_line": CVV_LINE,
        "chat_draft": chat_draft,
    }


def held_note_preview(journal: list[dict[str, Any]], today: str) -> str:
    for entry in journal:
        if str(entry.get("date") or "") != today:
            continue
        note = str(entry.get("note") or "").strip()
        if not note:
            return ""
        if len(note) <= 72:
            return note
        return note[:69].rstrip() + "…"
    return ""


def night_garden_active(local_hour: int) -> bool:
    return local_hour >= 20 or local_hour < 6


def gentleness_payload(
    raw: dict[str, Any],
    *,
    today: str,
    checked_today: bool,
    last_mood: str,
    journal: list[dict[str, Any]],
    local_hour: int,
) -> dict[str, Any]:
    gentle = gentle_mode_active(last_mood, journal) if checked_today else False
    mirror = mirror_line(
        journal,
        last_mood=last_mood,
        today=today,
        checked_today=checked_today,
        local_hour=local_hour,
    )
    calm = compute_calm_streak(raw, journal) if journal else {"current": 0, "longest": 0}
    survival = compute_survival_streak(raw, journal) if journal else {"current": 0, "longest": 0}
    held = held_note_preview(journal, today) if checked_today else ""
    lonely_today = any(
        note_signals_lonely(str(e.get("note") or ""))
        for e in journal
        if str(e.get("date") or "") == today
    )
    bridge = crisis_bridge(
        last_mood,
        checked_today,
        lonely_note=lonely_today,
        local_hour=local_hour,
    )
    night = night_garden_active(local_hour)
    sunday = is_sunday_garden(today)
    tagline = ""
    if sunday and (gentle or lonely_today):
        tagline = "Domingo no jardim — sem pressa, sem cobrança"
    elif night and (gentle or lonely_today):
        tagline = "Jardim noturno — descanse sem pressa"
    elif gentle:
        tagline = "Jardim da Gentileza — dias difíceis permitidos"
    elif night:
        tagline = "Jardim noturno — descanse sem pressa"
    surv_line = survival_streak_line(survival["current"])
    return {
        "gentle_mode": gentle,
        "mirror_line": mirror,
        "calm_streak_current": calm["current"],
        "calm_streak_longest": calm["longest"],
        "survival_streak_current": survival["current"],
        "survival_streak_longest": survival["longest"],
        "survival_streak_line": surv_line,
        "held_note": held,
        "crisis_bridge": bridge,
        "night_garden": night,
        "sunday_garden": sunday,
        "lonely_note_today": lonely_today,
        "tagline": tagline,
    }
