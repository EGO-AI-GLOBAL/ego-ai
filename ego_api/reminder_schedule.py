"""Janelas de aviso para lembretes pontuais (1 h, 30 min e 10 min antes)."""

from __future__ import annotations

import datetime
import html

# Minutos antes do horário do compromisso (ordem decrescente).
REMINDER_ALERT_OFFSETS_MINUTES: tuple[int, ...] = (60, 30, 10)
REMINDER_WINDOW_MINUTES = 5
REMINDER_PAST_GRACE = datetime.timedelta(minutes=5)

_TAG_BY_OFFSET: dict[int, str] = {60: "1h", 30: "30m", 10: "10m"}
_LABEL_BY_TAG: dict[str, str] = {
    "1h": "1 hora antes",
    "30m": "30 min antes",
    "10m": "10 min antes",
}


def reminder_slot_windows(
    scheduled_at: datetime.datetime,
) -> list[tuple[datetime.datetime, datetime.datetime, str]]:
    """Janelas [início, fim) para cada aviso antes do compromisso."""
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=datetime.timezone.utc)
    windows: list[tuple[datetime.datetime, datetime.datetime, str]] = []
    width = datetime.timedelta(minutes=REMINDER_WINDOW_MINUTES)
    for minutes_before in REMINDER_ALERT_OFFSETS_MINUTES:
        start = scheduled_at - datetime.timedelta(minutes=minutes_before)
        tag = _TAG_BY_OFFSET.get(minutes_before, f"{minutes_before}m")
        windows.append((start, start + width, tag))
    return windows


def reminder_current_window(
    now: datetime.datetime, scheduled_at: datetime.datetime
) -> tuple[datetime.datetime, datetime.datetime, str] | None:
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    for a, b, tag in reminder_slot_windows(scheduled_at):
        if a <= now < b:
            return (a, b, tag)
    return None


def reminder_tag_label(tag: str) -> str:
    return _LABEL_BY_TAG.get(tag, tag)


def reminder_speech_text(
    tag: str, title: str, announce: str, when_local: str
) -> str:
    """Texto para TTS no Streamlit (e futuras push no mobile)."""
    t = (title or "Lembrete").strip()
    a = (announce or "").strip()
    when = (when_local or "").strip()
    if tag == "10m":
        return a or f"{t}. Começa em dez minutos, às {when}."
    if tag == "30m":
        return f"Lembrete: {t}. Daqui a trinta minutos, às {when}."
    if tag == "1h":
        return f"Lembrete: {t}. Daqui a uma hora, às {when}."
    return a or t


def reminder_alarm_html(tag: str, title: str, announce: str, when_local: str) -> str:
    title_e = html.escape(title or "Lembrete")
    when_e = html.escape(when_local)
    tag_label = html.escape(reminder_tag_label(tag))
    if tag == "10m":
        sub = html.escape((announce or title or "").strip())
    else:
        sub = title_e
    detail = f"Compromisso às <strong>{when_e}</strong>"
    return (
        f'<div class="ego-alarm-banner">'
        f'<div class="ego-alarm-tag">{tag_label}</div>'
        f'<p class="ego-alarm-title">{sub}</p>'
        f'<p class="ego-alarm-sub">{detail}</p>'
        f"</div>"
    )


def reminder_llm_instruction_block(agenda_horizon_days: int = 90) -> str:
    offsets = ", ".join(
        f"{m} minutes" if m != 60 else "1 hour"
        for m in REMINDER_ALERT_OFFSETS_MINUTES
    )
    return f"""
REMINDERS / ALARMS: If the user asks for a reminder, alarm, meeting, or important call at a specific time,
you may register it by adding EXACTLY ONE line at the very END of your reply (after your normal answer), with this format:
[[EGO_REMINDER:{{"title":"short title","scheduled_at":"ISO-8601 datetime WITH timezone offset","announce":"what to say at the 10-minute-before alert"}}]]
- scheduled_at is the moment the event happens (e.g. time of the call), NOT the alarm times.
- The app notifies the user at three times before the event: 1 hour, 30 minutes, and 10 minutes before ({offsets} before).
- Put in announce a short phrase for the 10-minute alert (e.g. "Your meeting starts in ten minutes").
- Agenda window: only schedule between now and the next {agenda_horizon_days} days (reject beyond that).
- If the user omits the year, use the current calendar year; if that date/time already passed, use the next year.
- If the user omits the month, use the current month.
- Always output scheduled_at as full ISO-8601 with timezone offset after resolving year/month/day/time.
- If date/time is still ambiguous, do NOT add the line; ask one short clarifying question instead.
- When the user clearly wants a reminder/alarm at a known time, you MUST output the [[EGO_REMINDER:...]] line automatically.
  Do NOT ask whether to turn on the alarm, wait for confirmation, or offer to "activate" it — the app registers the line as soon as you send it.
""".strip()
