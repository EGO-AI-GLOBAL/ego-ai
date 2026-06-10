"""Fluxo de chat: agenda pessoal vs compartilhada (multi-turno)."""

from __future__ import annotations

import datetime
import json
import re
from typing import Any

from ego_api.services import ui_state_from_profile

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

_SCHEDULE_KEY = "chat_schedule"
_SCOPE_PERSONAL = re.compile(
    r"\b(pessoal|minha agenda|agenda pessoal|só minha|so minha|individual|privad[ao])\b",
    re.I,
)
_SCOPE_SHARED = re.compile(
    r"\b(compartilhad[ao]|partilhad[ao]|equipe|time|team|família|familia|grupo)\b",
    re.I,
)
_SCHEDULE_INTENT = re.compile(
    r"\b("
    r"marcar|marca|marque|marques|agendar|agenda|agende|"
    r"reunião|reuniao|compromisso|"
    r"lembrete|lembrar|encontro|call|chamada|consulta|atendimento"
    r")\b",
    re.I,
)
_GROUP_SCHEDULE_INTENT = re.compile(
    r"(?i)\b(marcar|marca|marque|marques|agendar|agende|reuni|compromisso|encontro)\b"
)
# Nome de agenda de grupo (ex.: Família) sem dizer «compartilhada»
_AGENDA_GROUP_NAME = re.compile(
    r"(?i)\bagenda\s+(?!pessoal\b|minha\b|individual\b|privad[ao]\b)"
    r"[«\"']?\s*([^«\"'\n.?]+)"
)


def parse_invite_from_plain_text(text: str) -> dict | None:
    """Fallback quando o LLM responde em texto mas não envia [[EGO_SHARED_INVITE:...]]."""
    raw = (text or "").strip()
    if not raw:
        return None
    if not re.search(r"(?i)\b(convida|convite|adiciona|inclui|adicione|add)\b", raw):
        return None
    cal_name = _extract_shared_calendar_name(raw)
    payload: dict[str, Any] = {}
    if cal_name:
        payload["calendar_name"] = cal_name
    emails = _normalize_email_list(
        re.findall(r"([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})", raw, re.I)
    )
    phones = _normalize_phone_list_from_text(raw)
    if emails:
        payload["invite_emails"] = emails
    if phones:
        payload["invite_phones"] = phones
    if not emails and not phones:
        return None
    return payload


def _trim_calendar_name_tail(name: str) -> str:
    trimmed = re.split(
        r"(?i)\s+(?:"
        r"reuni|marca|agend|convida|amanh|hoje|depois|às|as|"
        r"ensaio|compromisso|encontro|chamada|consulta|"
        r"pra\s+dia|para\s+dia|"
        r"\d"
        r")",
        name.strip().strip("«»\"' "),
    )[0].strip()
    if re.match(r"(?i)^(com\s+)?nome\s+", trimmed):
        trimmed = re.sub(r"(?i)^(com\s+)?nome\s+", "", trimmed).strip()
    return trimmed


def _extract_create_calendar_name(raw: str) -> str:
    """Nome ao criar agenda («com nome 360 nas alturas», «chamada Equipe X»)."""
    patterns = (
        r"(?i)(?:com\s+)?nome\s+(?:da\s+agenda(?:\s+compartilhada)?\s+)?[«\"']?\s*([^«\"'\n.?]+)",
        r"(?i)(?:chamad[ao]|batizad[ao]|intitulad[ao])\s+(?:de\s+)?[«\"']?\s*([^«\"'\n.?]+)",
        r"(?i)cria(?:r|r?\s+(?:uma|um))?\s+agenda(?:\s+compartilhada)?\s+com\s+(?:o\s+)?nome\s+"
        r"[«\"']?\s*([^«\"'\n.?]+)",
    )
    for pat in patterns:
        m = re.search(pat, raw)
        if m:
            name = _trim_calendar_name_tail(m.group(1))
            if name and not re.match(
                r"(?i)^(compartilhada|compartilhado|grupo|família|familia)$", name
            ):
                return name
    return ""


def _extract_shared_calendar_name(raw: str) -> str:
    created = _extract_create_calendar_name(raw)
    if created:
        return created

    def _trim_calendar_tail(name: str) -> str:
        return _trim_calendar_name_tail(name)

    patterns = (
        r"(?i)(?:agenda\s+compartilhada|grupo)\s+[«\"']?\s*([^«\"'\n.?]+)",
        r"(?i)\b(?:no|na|do|da)\s+agenda\s+(?!pessoal\b|minha\b|individual\b)"
        r"[«\"']?\s*([^«\"'\n.?]+)",
        r"(?i)(?:para|pra)\s+(?:a\s+)?agenda\s+(?!pessoal\b|minha\b|individual\b)"
        r"[«\"']?\s*([^«\"'\n.?]+)",
        r"(?i)\bagenda\s+(?!pessoal\b|minha\b|individual\b|privad[ao]\b)"
        r"[«\"']?\s*([^«\"'\n.?]+)",
        r"(?i)\b(?:no|na|do|da)\s+grupo\s+[«\"']?\s*([^«\"'\n.?]+)",
    )
    for pat in patterns:
        m = re.search(pat, raw)
        if m:
            name = _trim_calendar_tail(m.group(1))
            if name:
                return name
    if re.search(r"(?i)\bfamília\b|\bfamilia\b", raw):
        return "Família"
    return ""


def _strip_schedule_scope_prefix(fragment: str) -> str:
    """Remove «na agenda pessoal», «um», etc. — mantém o título completo como no manual."""
    s = (fragment or "").strip().strip("«»\"' ")
    prefix_patterns = (
        r"(?:(?:na|no|n[oa]|da|do|de|para|pra|em)\s+)?"
        r"(?:(?:minha|sua)\s+)?agenda\s+(?:pessoal\s+)?",
        r"(?:um|uma|o|a)\s+",
    )
    for _ in range(4):
        changed = False
        for pat in prefix_patterns:
            nxt = re.sub(rf"(?i)^{pat}", "", s).strip()
            if nxt != s:
                s = nxt
                changed = True
        if not changed:
            break
    return s


def _trim_event_title_tail(fragment: str) -> str:
    """Remove hora, data e nome da agenda do que o utilizador disse."""
    s = _strip_schedule_scope_prefix(fragment)
    if not s:
        return ""
    s = re.split(
        r"(?i)\s+(?:"
        r"pra\s+dia|para\s+o\s+dia|para\s+dia|no\s+dia|"
        r"às|as\s+\d{1,2}\b|"
        r"hoje|amanh\w*|depois|"
        r"segunda|ter[cç]a|quarta|quinta|sexta|s[aá]bado|domingo|"
        r"\bna\s+agenda\b|\bno\s+dia\b|\bpara\s+o\s+dia\b|"
        r"\bagenda\b|\bgrupo\b|compartilhad[ao]|fam[ií]lia|"
        r"\d{1,2}[:/h]\d*"
        r")",
        s,
        maxsplit=1,
    )[0].strip()
    s = re.sub(r"(?i)^(um|uma|o|a)\s+", "", s).strip()
    if re.match(r"(?i)^(compartilhada|compartilhado|grupo|família|familia)$", s):
        return ""
    return s


def _format_event_title(fragment: str) -> str:
    s = _trim_event_title_tail(fragment)
    if not s or len(s) < 2:
        return ""
    if s.islower() and len(s) <= 80:
        return (s[0].upper() + s[1:])[:500]
    return s[:500]


def _extract_event_title_after_calendar(raw: str) -> str:
    """Texto do compromisso logo após o nome da agenda (ex.: «…alturas ensaio pra dia 18»)."""
    cal = _extract_shared_calendar_name(raw)
    if not cal:
        return ""
    m = re.search(re.escape(cal), raw, re.I)
    if not m:
        return ""
    return _format_event_title(raw[m.end() :])


_EVENT_KEYWORD_TITLES: tuple[tuple[str, str], ...] = (
    (r"\bensaio\b", "Ensaio"),
    (r"\breuni", "Reunião"),
    (r"\bencontro\b", "Encontro"),
    (r"\bchamada\b|\bcall\b", "Chamada"),
    (r"\bconsulta\b", "Consulta"),
    (r"\batendimento\b", "Atendimento"),
    (r"\bprova\b", "Prova"),
    (r"\baula\b", "Aula"),
    (r"\btreino\b", "Treino"),
    (r"\bshow\b", "Show"),
    (r"\bapresenta", "Apresentação"),
)


def _keyword_event_title(text: str) -> str:
    low = (text or "").lower()
    for pat, label in _EVENT_KEYWORD_TITLES:
        if re.search(pat, low):
            return label
    return ""


def _extract_shared_event_title(raw: str) -> str:
    """Título que o utilizador disse (ex.: «marca ensaio amanhã 15h» → Ensaio)."""
    text = (raw or "").strip()
    if not text:
        return "Compromisso"

    m = re.search(
        r"(?i)(?:título|titulo)\s*:?\s*[«\"']?\s*([^«\"'\n]+)",
        text,
    )
    if m:
        title = _format_event_title(m.group(1))
        if title:
            return title

    after_cal = _extract_event_title_after_calendar(text)
    if after_cal and len(after_cal) <= 80:
        return after_cal

    appt = re.search(
        r"(?i)\batendimento\s+(?:(?:ao|à|a)\s+)?([A-Za-zÀ-ú][A-Za-zÀ-ú\s'.-]{1,58})",
        text,
    )
    if appt:
        name = _trim_event_title_tail(appt.group(1))
        if name:
            return _format_event_title(f"Atendimento {name}")

    verb = re.search(
        r"(?i)\b(?:marca|marcar|marque|marques|agende|agendar|coloca|colocar)\s+"
        r"(?:(?:um|uma|o|a)\s+|(?:na|no)\s+)?"
        r"(.+)$",
        text,
    )
    if verb:
        title = _format_event_title(verb.group(1))
        if title and not re.search(r"(?i)^agenda\b", title[:24]):
            return title

    kw = _keyword_event_title(text)
    if kw:
        return kw

    return "Compromisso"


def _should_replace_event_title(
    current: str,
    extracted: str,
    user_text: str,
    *,
    calendar_name: str = "",
) -> bool:
    """Substitui título do LLM quando o utilizador foi mais específico no chat."""
    if not extracted or extracted == "Compromisso":
        return False
    cur = (current or "").strip()
    if not cur or cur.lower() in (
        "compromisso",
        "reunião",
        "reuniao",
        "evento",
        "lembrete",
    ):
        return True
    ext = extracted.strip()
    if cur.lower() == ext.lower():
        return False
    low_u = (user_text or "").lower()
    ext_low = ext.lower()
    if ext_low not in low_u:
        return False
    cal_low = (calendar_name or "").strip().lower()
    cur_low = cur.lower()
    if cur_low == ext_low:
        return False
    if cal_low and (cur_low == cal_low or cal_low in cur_low):
        return True
    if re.search(r"(?i)^agenda\b", cur):
        return True
    if cur_low in ("reunião", "reuniao", "compromisso", "evento", "lembrete"):
        return True
    if len(cur) > 24 and ext_low in low_u:
        return True
    if ext_low in low_u and cur_low != ext_low:
        return True
    return False


def override_title_from_user_message(
    user_text: str, payload: dict | list[dict] | None
) -> dict | list[dict] | None:
    """Título vem do pedido do utilizador (Ensaio), nunca do nome da agenda nem «Reunião» genérico."""
    if not payload:
        return payload
    if not looks_like_schedule_intent(user_text):
        return payload
    extracted = _extract_shared_event_title(user_text)
    if not extracted or extracted == "Compromisso":
        return payload

    def _patch(item: dict) -> dict:
        current = str(item.get("title") or item.get("event_title") or "").strip()
        cal_name = _extract_shared_calendar_name(user_text)
        if _should_replace_event_title(
            current, extracted, user_text, calendar_name=cal_name
        ):
            return {**item, "title": extracted, "announce": extracted}
        return item

    if isinstance(payload, dict):
        return _patch(payload)
    return [_patch(it) if isinstance(it, dict) else it for it in payload]


def apply_shared_event_fields_from_user(
    user_text: str,
    data: dict[str, Any],
    *,
    ref: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Última passagem antes de gravar: título e data do texto do chat."""
    patched = override_title_from_user_message(user_text, data)
    out = patched if isinstance(patched, dict) else data
    sched = override_scheduled_from_user_message(user_text, out, ref=ref)
    return sched if isinstance(sched, dict) else out


_RELATIVE_DAY_HINT = re.compile(
    r"\b(hoje|amanhã|amanha|depois de amanhã|depois de amanha)\b",
    re.I,
)
_EXPLICIT_DATE_HINT = re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
_EXPLICIT_DAY_MONTH = re.compile(
    r"\b\d{1,2}\s+de\s+"
    r"(janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|"
    r"setembro|outubro|novembro|dezembro)\b",
    re.I,
)
_MONTH_PT: dict[str, int] = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def user_message_has_relative_day(text: str) -> bool:
    return bool(_RELATIVE_DAY_HINT.search(text or ""))


def user_message_has_explicit_date(text: str) -> bool:
    t = text or ""
    return bool(_EXPLICIT_DATE_HINT.search(t) or _EXPLICIT_DAY_MONTH.search(t))


def user_message_has_schedule_time(text: str) -> bool:
    low = (text or "").lower()
    return bool(
        re.search(r"(?:às|as)\s*\d{1,2}", low)
        or re.search(r"\b\d{1,2}:\d{2}\b", low)
        or re.search(r"\b\d{1,2}\s*h(?:oras)?\b", low)
        or re.search(r"\b\d{1,2}\s*horas?\b", low)
    )


def _parse_pt_schedule_hint(
    text: str, ref: datetime.datetime | None = None
) -> datetime.datetime | None:
    """Interpreta frases comuns (hoje/amanhã + hora) para ISO no fuso de ref."""
    raw = (text or "").strip()
    if not raw:
        return None
    from ego_api.schedule_tz import local_now_from_session

    ref = ref or local_now_from_session()
    low = raw.lower()
    tm = re.search(
        r"(?:às|as)\s*(\d{1,2})(?::(\d{2}))?\s*(?:h|horas)?",
        low,
    )
    if not tm:
        tm = re.search(r"\b(\d{1,2}):(\d{2})\b", low)
    if not tm:
        tm = re.search(r"\b(\d{1,2})\s*horas?\b", low)
    if not tm:
        tm = re.search(r"\b(\d{1,2})\s*h\b", low)
    if not tm:
        return None
    hour = int(tm.group(1))
    minute = int(tm.group(2) or 0)
    if hour > 23 or minute > 59:
        return None

    day = ref.date()
    explicit_day = False
    if re.search(r"\bdepois de amanhã\b|\bdepois de amanha\b", low):
        explicit_day = True
        day = day + datetime.timedelta(days=2)
    elif re.search(r"\bamanhã\b|\bamanha\b", low):
        explicit_day = True
        day = day + datetime.timedelta(days=1)
    elif re.search(r"\bhoje\b", low):
        explicit_day = True
    else:
        wd = re.search(
            r"(?i)\b(?:na\s+)?(?:próxima\s+|proxima\s+)?"
            r"(segunda|seg|terça|terca|ter|quarta|qua|quinta|qui|sexta|sex|sábado|sabado|sab|domingo|dom)\b",
            low,
        )
        dm = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", low)
        if wd:
            explicit_day = True
            key = wd.group(1).lower().replace("ç", "c")
            weekday_map = {
                "segunda": 0,
                "seg": 0,
                "terca": 1,
                "terça": 1,
                "ter": 1,
                "quarta": 2,
                "qua": 2,
                "quinta": 3,
                "qui": 3,
                "sexta": 4,
                "sex": 4,
                "sabado": 5,
                "sábado": 5,
                "sab": 5,
                "domingo": 6,
                "dom": 6,
            }
            target = weekday_map.get(key)
            if target is not None:
                delta = (target - ref.weekday()) % 7
                if delta == 0 and not re.search(r"\bhoje\b", low):
                    delta = 7
                day = ref.date() + datetime.timedelta(days=delta)
        elif dm:
            explicit_day = True
            d_num = int(dm.group(1))
            m_num = int(dm.group(2))
            y_raw = dm.group(3)
            year = int(y_raw) if y_raw else ref.year
            if year < 100:
                year += 2000
            try:
                day = datetime.date(year, m_num, d_num)
            except ValueError:
                return None
            if not y_raw and day < ref.date():
                try:
                    day = datetime.date(year + 1, m_num, d_num)
                except ValueError:
                    return None
        else:
            md = _EXPLICIT_DAY_MONTH.search(low)
            if md:
                explicit_day = True
                d_num = int(md.group(1))
                m_key = md.group(2).lower().replace("ç", "c")
                m_num = _MONTH_PT.get(m_key)
                if not m_num:
                    return None
                year = ref.year
                try:
                    day = datetime.date(year, m_num, d_num)
                except ValueError:
                    return None
                if day < ref.date():
                    try:
                        day = datetime.date(year + 1, m_num, d_num)
                    except ValueError:
                        return None

    try:
        dt = datetime.datetime.combine(
            day, datetime.time(hour, minute), tzinfo=ref.tzinfo
        )
        # Só hora (ex.: «às 9:00» sem «amanhã»): hoje se ainda não passou, senão amanhã.
        if not explicit_day and dt <= ref:
            dt = dt + datetime.timedelta(days=1)
        return dt
    except ValueError:
        return None


def stash_pending_schedule_from_text(
    schedule: dict[str, Any],
    user_text: str,
    ref: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Guarda data/hora do pedido ambíguo para a resposta curta («marca na agenda familia»)."""
    when = _parse_pt_schedule_hint(user_text, ref)
    title = _extract_shared_event_title(user_text)
    draft: dict[str, Any] = {"title": title}
    if when:
        draft["scheduled_at"] = when.isoformat()
    return merge_schedule_draft(
        schedule, {"step": "choose_scope", "draft": draft}
    )


def apply_scope_follow_up_if_pending(
    schedule: dict[str, Any],
    user_text: str,
    supabase: Client | None,
    user_id: str,
    ref: datetime.datetime | None = None,
) -> dict[str, Any] | None:
    """Completa marcação após «marca na agenda pessoal» / «marca na agenda familia»."""
    draft = schedule.get("draft") or {}
    pending = draft.get("scheduled_at") or schedule.get("step") == "choose_scope"
    if not pending:
        return None
    scope = detect_scope_from_user_text(user_text, supabase, user_id)
    t = (user_text or "").strip()
    if not scope and _SCOPE_PERSONAL.search(t):
        scope = "personal"
    if not scope and user_named_shared_calendar(t):
        scope = "shared"
    if not scope:
        return None
    when = _parse_pt_schedule_hint(t, ref)
    scheduled_at = when.isoformat() if when else draft.get("scheduled_at")
    if not scheduled_at:
        return None
    title = str(draft.get("title") or _extract_shared_event_title(t) or "Compromisso")[
        :500
    ]
    new_draft: dict[str, Any] = {
        "scope": scope,
        "scheduled_at": scheduled_at,
        "title": title,
    }
    if scope == "shared":
        cal = _extract_shared_calendar_name(t) or str(draft.get("calendar_name") or "")
        if cal:
            new_draft["calendar_name"] = cal
    return merge_schedule_draft(schedule, {"draft": new_draft, "step": ""})


def reminder_from_schedule_draft(schedule: dict[str, Any]) -> dict | None:
    draft = schedule.get("draft") or {}
    if str(draft.get("scope") or "") != "personal":
        return None
    scheduled_at = draft.get("scheduled_at")
    title = str(draft.get("title") or "Compromisso").strip()
    if not scheduled_at or not title:
        return None
    return {
        "title": title,
        "scheduled_at": scheduled_at,
        "announce": title,
    }


def shared_event_from_schedule_draft(schedule: dict[str, Any]) -> dict | None:
    draft = schedule.get("draft") or {}
    if str(draft.get("scope") or "") != "shared":
        return None
    cal_name = str(draft.get("calendar_name") or draft.get("name") or "").strip()
    title = str(draft.get("title") or draft.get("event_title") or "").strip()
    scheduled_at = draft.get("scheduled_at")
    if not cal_name or not title or not scheduled_at:
        return None
    return {
        "calendar_name": cal_name,
        "title": title,
        "scheduled_at": scheduled_at,
    }


def parse_shared_event_from_plain_text(
    text: str, ref: datetime.datetime | None = None
) -> dict | None:
    """Fallback quando o LLM responde em texto mas não envia [[EGO_SHARED_EVENT:...]]."""
    raw = (text or "").strip()
    if not raw:
        return None
    if not looks_like_schedule_intent(raw):
        return None
    if _SCOPE_PERSONAL.search(raw) and not _extract_shared_calendar_name(raw):
        return None
    if not is_group_schedule_request(raw):
        return None
    when = _parse_pt_schedule_hint(raw, ref)
    if not when:
        return None
    cal_name = _extract_shared_calendar_name(raw)
    title = _extract_shared_event_title(raw)
    return {
        "calendar_name": cal_name,
        "title": title,
        "scheduled_at": when.isoformat(),
    }


def override_scheduled_from_user_message(
    user_text: str,
    payload: dict | list[dict] | None,
    *,
    ref: datetime.datetime | None = None,
) -> dict | list[dict] | None:
    """Corrige data/hora com base no texto (fuso de ref), mesmo se o LLM errou."""
    if not payload or not (
        user_message_has_relative_day(user_text)
        or user_message_has_schedule_time(user_text)
        or user_message_has_explicit_date(user_text)
    ):
        return payload
    when = _parse_pt_schedule_hint(user_text, ref)
    if not when:
        return payload
    iso = when.isoformat()
    if isinstance(payload, dict):
        return {**payload, "scheduled_at": iso}
    return [
        {**it, "scheduled_at": iso} if isinstance(it, dict) else it for it in payload
    ]


def parse_personal_reminder_request(
    text: str,
    ref: datetime.datetime | None = None,
    *,
    implicit_personal: bool = False,
) -> dict | None:
    """Marcação na agenda pessoal quando título + hora estão claros."""
    raw = (text or "").strip()
    if not raw or not looks_like_schedule_intent(raw):
        return None
    if not _SCOPE_PERSONAL.search(raw) and not implicit_personal:
        return None
    if not user_message_has_schedule_time(raw):
        return None
    when = _parse_pt_schedule_hint(raw, ref)
    if not when:
        return None
    title = _extract_shared_event_title(raw)
    if not title or title == "Compromisso":
        title = "Compromisso"
    return {
        "title": title,
        "scheduled_at": when.isoformat(),
        "announce": title,
    }


def parse_reminder_from_plain_text(
    text: str,
    ref: datetime.datetime | None = None,
    *,
    implicit_personal: bool = False,
) -> dict | None:
    """Fallback: agenda pessoal quando o LLM não envia [[EGO_REMINDER:...]]."""
    return parse_personal_reminder_request(
        text, ref, implicit_personal=implicit_personal
    )


def is_group_schedule_request(text: str) -> bool:
    """True se o pedido cita agenda de grupo (nome, família, etc.) — não basta «marcar»."""
    t = (text or "").strip()
    if not t or _SCOPE_PERSONAL.search(t):
        return False
    return bool(
        _SCOPE_SHARED.search(t)
        or _extract_shared_calendar_name(t)
        or _AGENDA_GROUP_NAME.search(t)
    )


def resolve_default_shared_calendar_name(
    supabase: Client | None,
    user_id: str,
    *,
    prefer_text: str = "",
) -> str:
    explicit = _extract_shared_calendar_name(prefer_text)
    if explicit:
        return explicit
    if not supabase or not user_id:
        return ""
    try:
        from ego_api import shared_calendars as sc

        rows = sc.list_calendars_for_user(supabase, user_id)
    except Exception:
        rows = []
    if not rows:
        return ""
    if len(rows) == 1:
        return str(rows[0].get("name") or "").strip()
    for row in rows:
        name = str(row.get("name") or "").strip()
        if name.lower() in ("família", "familia", "family"):
            return name
    return ""


def apply_user_create_calendar_intent(
    user_display: str, data: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Pedido do utilizador manda no nome ao criar (ignora JSON errado do LLM)."""
    parsed = parse_create_shared_calendar_from_plain_text(user_display)
    if not parsed:
        return data
    name = str(parsed.get("calendar_name") or "").strip()
    if not name or not _user_requests_new_calendar(user_display):
        return data
    out = dict(data) if isinstance(data, dict) else {}
    out["calendar_name"] = name
    out.pop("calendar_id", None)
    for key in ("invite_emails", "emails", "members"):
        if key in parsed and parsed[key]:
            out[key] = parsed[key]
    return out


def _user_requests_new_calendar(text: str) -> bool:
    raw = (text or "").strip()
    if not raw:
        return False
    if not re.search(r"(?i)\b(cria|criar|crie|abre|abrir|novo|nova)\b", raw):
        return False
    return bool(
        re.search(r"(?i)\bagenda\b", raw)
        or re.search(r"(?i)\bgrupo\b", raw)
        or _SCOPE_SHARED.search(raw)
        or _extract_create_calendar_name(raw)
    )


def fill_shared_calendar_name(
    supabase: Client | None,
    user_id: str,
    data: dict[str, Any],
    *,
    prefer_text: str = "",
) -> dict[str, Any]:
    out = dict(data)
    from_user = ""
    if prefer_text:
        from_user = (
            _extract_create_calendar_name(prefer_text)
            or _extract_shared_calendar_name(prefer_text)
        ).strip()
    name = str(out.get("calendar_name") or out.get("name") or "").strip()
    if from_user:
        name = from_user
    elif not name:
        name = resolve_default_shared_calendar_name(
            supabase, user_id, prefer_text=prefer_text
        )

    creating = bool(prefer_text and _user_requests_new_calendar(prefer_text) and from_user)
    if creating:
        out.pop("calendar_id", None)

    if supabase and user_id:
        from ego_api import shared_calendars as sc

        if creating:
            found = sc.find_calendar_id_by_name(supabase, user_id, name)
            if found:
                for row in sc.list_calendars_for_user(supabase, user_id):
                    if str(row.get("id") or "") == found:
                        row_name = str(row.get("name") or "").strip()
                        if sc.calendar_name_key(row_name) == sc.calendar_name_key(name):
                            out["calendar_id"] = found
                            out["calendar_name"] = row_name or name
                            return out
                        break
            out.pop("calendar_id", None)
            out["calendar_name"] = name
            return out

        cid, canon = sc.resolve_calendar_for_user(
            supabase,
            user_id,
            calendar_id=str(out.get("calendar_id") or ""),
            calendar_name=name,
        )
        key_wanted = sc.calendar_name_key(name)
        key_canon = sc.calendar_name_key(canon) if canon else ""
        if cid and key_wanted and key_canon and key_wanted == key_canon:
            out["calendar_id"] = cid
            out["calendar_name"] = canon
        else:
            out.pop("calendar_id", None)
            out["calendar_name"] = name
    elif name:
        out["calendar_name"] = name
    return out


def load_chat_schedule(prof: dict | None) -> dict[str, Any]:
    ui = ui_state_from_profile(prof)
    raw = ui.get(_SCHEDULE_KEY)
    if isinstance(raw, dict):
        draft = raw.get("draft")
        if not isinstance(draft, dict):
            draft = {}
        return {"step": str(raw.get("step") or ""), "draft": dict(draft)}
    return {"step": "", "draft": {}}


def save_chat_schedule(
    supabase: Client | None,
    user_id: str,
    prof: dict | None,
    schedule: dict[str, Any] | None,
) -> None:
    if not supabase or not user_id:
        return
    from ego_api import db

    ui = dict(ui_state_from_profile(prof))
    if schedule:
        ui[_SCHEDULE_KEY] = schedule
    else:
        ui.pop(_SCHEDULE_KEY, None)
    db.update_profile_fields(supabase, user_id, {"ui_state": ui})


def merge_schedule_draft(
    schedule: dict[str, Any], patch: dict[str, Any]
) -> dict[str, Any]:
    out = {
        "step": schedule.get("step") or "",
        "draft": dict(schedule.get("draft") or {}),
    }
    if patch.get("step"):
        out["step"] = str(patch["step"])
    draft_patch = patch.get("draft")
    if isinstance(draft_patch, dict):
        for key, val in draft_patch.items():
            if val is None:
                out["draft"].pop(key, None)
            elif val != "":
                out["draft"][key] = val
    for key in ("scope", "calendar_name", "calendar_id", "title", "scheduled_at"):
        if key in patch and patch[key] not in (None, ""):
            out["draft"][key] = patch[key]
    if "invite_emails" in patch:
        emails = _normalize_email_list(patch.get("invite_emails"))
        if emails:
            out["draft"]["invite_emails"] = emails
    return out


def user_named_shared_calendar(text: str) -> bool:
    """Utilizador indicou agenda de grupo pelo nome (ex. «agenda familia»)."""
    t = (text or "").strip()
    if not t:
        return False
    return bool(_extract_shared_calendar_name(t) or _AGENDA_GROUP_NAME.search(t))


def user_shared_calendar_count(
    supabase: Client | None, user_id: str
) -> int:
    if not supabase or not user_id:
        return 0
    try:
        from ego_api import shared_calendars as sc

        return len(sc.list_calendars_for_user(supabase, user_id))
    except Exception:
        return 0


def schedule_scope_is_ambiguous(
    text: str, supabase: Client | None, user_id: str
) -> bool:
    """Marcar sem «pessoal» nem nome de grupo — só pergunta se existir agenda de grupo."""
    t = (text or "").strip()
    if not looks_like_schedule_intent(t) or _SCOPE_PERSONAL.search(t):
        return False
    if user_named_shared_calendar(t):
        return False
    if not _GROUP_SCHEDULE_INTENT.search(t):
        return False
    if not supabase or not user_id:
        return False
    try:
        from ego_api import shared_calendars as sc

        rows = sc.list_calendars_for_user(supabase, user_id)
    except Exception:
        rows = []
    return len(rows) >= 1


def only_personal_schedule_available(
    supabase: Client | None, user_id: str
) -> bool:
    """Sem agendas de grupo: marcações ambíguas vão para agenda pessoal."""
    if not supabase or not user_id:
        return False
    return user_shared_calendar_count(supabase, user_id) == 0


def build_schedule_scope_choice_reply(
    supabase: Client | None, user_id: str, user_text: str
) -> str | None:
    if not schedule_scope_is_ambiguous(user_text, supabase, user_id):
        return None
    try:
        from ego_api import shared_calendars as sc

        rows = sc.list_calendars_for_user(supabase, user_id)
    except Exception:
        rows = []
    names = [str(r.get("name") or "").strip() for r in rows if r.get("name")]
    if len(names) == 1:
        n = names[0]
        return (
            f"Agenda **pessoal** ou **{n}**? "
            f"Diga só: «marca na agenda pessoal» ou «marca na agenda {n}»."
        )
    if len(names) > 1:
        listed = ", ".join(n for n in names[:3])
        return (
            f"Agenda **pessoal** ou de grupo ({listed})? "
            "Diga só: «marca na agenda pessoal» ou «marca na agenda» + o nome."
        )
    return "Agenda **pessoal**? Diga: «marca na agenda pessoal»."


def resolve_effective_schedule_scope(
    schedule: dict[str, Any],
    user_text: str,
    supabase: Client | None = None,
    user_id: str = "",
) -> str | None:
    """Uma única agenda por mensagem: personal ou shared, nunca as duas."""
    t = (user_text or "").strip()
    if _SCOPE_PERSONAL.search(t):
        return "personal"
    if user_named_shared_calendar(t):
        return "shared"
    draft_scope = str((schedule.get("draft") or {}).get("scope") or "").strip()
    if draft_scope in ("personal", "shared"):
        return draft_scope
    user_scope = detect_scope_from_user_text(t, supabase, user_id)
    return user_scope


def detect_scope_from_user_text(
    text: str,
    supabase: Client | None = None,
    user_id: str = "",
) -> str | None:
    t = (text or "").strip()
    if not t:
        return None
    if _SCOPE_PERSONAL.search(t):
        return "personal"
    if is_group_schedule_request(t) and user_named_shared_calendar(t):
        return "shared"
    if (
        supabase
        and user_id
        and looks_like_schedule_intent(t)
        and only_personal_schedule_available(supabase, user_id)
    ):
        return "personal"
    return None


def looks_like_schedule_intent(text: str) -> bool:
    raw = text or ""
    # «desmarca compromisso» contém «compromisso» mas é apagar, não marcar.
    if _DISMISS_VERBS.search(raw):
        return False
    return bool(_SCHEDULE_INTENT.search(raw))


def _normalize_phone_list(raw: object) -> list[str]:
    from ego_api.phone_utils import normalize_phone_br

    if raw is None:
        return []
    if isinstance(raw, str):
        parts = re.split(r"[,;\s]+", raw)
    elif isinstance(raw, list):
        parts = [str(x) for x in raw]
    else:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        norm, err = normalize_phone_br(p)
        if err or not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def _normalize_phone_list_from_text(raw: str) -> list[str]:
    chunks = re.findall(
        r"(?:\+?55[\s\-]?)?(?:\(?\d{2}\)?[\s\-]?)?\d{4,5}[\s\-]?\d{4}",
        raw or "",
    )
    return _normalize_phone_list(chunks)


def _normalize_email_list(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = re.split(r"[,;\s]+", raw)
    elif isinstance(raw, list):
        parts = [str(x) for x in raw]
    else:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        em = p.strip().lower()
        if "@" not in em or em in seen:
            continue
        seen.add(em)
        out.append(em)
    return out


def build_shared_calendars_context(supabase: Client | None, user_id: str) -> str:
    if not supabase or not user_id:
        return ""
    try:
        from ego_api import shared_calendars as sc

        rows = sc.list_calendars_for_user(supabase, user_id)
    except Exception:
        rows = []
    lines = [
        "",
        "=== AGENDAS DE GRUPO DO UTILIZADOR (Família, etc.) ===",
    ]
    if not rows:
        lines.append("(nenhuma ainda — criar com «cria agenda Família»)")
    else:
        from ego_api.config import MAX_SHARED_CALENDARS_PER_OWNER

        owned = sum(1 for row in rows if row.get("is_owner"))
        cap = max(1, MAX_SHARED_CALENDARS_PER_OWNER)
        lines.append(
            f"Pode ter até {cap} agendas criadas por si ({owned} agora). "
            "Cada «cria agenda NOME» com nome novo cria OUTRA agenda (nomes podem repetir entre utilizadores diferentes)."
        )
        for row in rows[:cap]:
            cid = str(row.get("id") or "")
            name = (row.get("name") or "Agenda").strip()
            nmem = row.get("member_count") or len(row.get("members") or [])
            owner = " (criou)" if row.get("is_owner") else " (membro)"
            lines.append(
                f'  - id={cid} | «{name}» | {nmem} membros{owner}'
            )
        if len(rows) == 1:
            only = (rows[0].get("name") or "Agenda").strip()
            lines.append(
                f"Omissão: se o utilizador marcar reunião/compromisso SEM dizer «pessoal», "
                f"use calendar_name «{only}»."
            )
        elif len(rows) > 1:
            lines.append(
                "Várias agendas: marcar/convidar exige o nome exacto da lista; "
                "«cria agenda X» cria agenda NOVA se X ainda não existir nas dele."
            )
        lines.append(
            "Ao CRIAR agenda nova, use no JSON o nome EXATO que o utilizador pediu "
            "(ex. «360 nas alturas»), nunca substitua por outro nome da lista."
        )
    lines.append("=== FIM AGENDAS DE GRUPO ===")
    return "\n".join(lines)


def build_schedule_wizard_context(
    schedule: dict[str, Any],
    user_text: str,
    supabase: Client | None = None,
    user_id: str = "",
) -> str:
    draft = schedule.get("draft") or {}
    scope = draft.get("scope")
    default_cal = resolve_default_shared_calendar_name(
        supabase, user_id, prefer_text=user_text
    )
    lines = [
        "",
        "=== FLUXO AGENDAMENTO (CHAT) ===",
        "A aba Agenda no app é só consulta. Marcações fazem-se no chat.",
        "",
        "REGRA PRINCIPAL (obrigatória):",
        "- «agenda pessoal» / «minha agenda» / «pessoal» → [[EGO_REMINDER:...]] (só pessoal).",
        "- «agenda familia» / «agenda Família» + reunião → [[EGO_SHARED_EVENT:...]] com esse nome.",
        "- Só «marca reunião amanhã 15h» SEM pessoal nem familia: se o utilizador "
        "tiver agenda de grupo → pergunte pessoal ou familia; se só tiver pessoal → "
        "[[EGO_REMINDER:...]] directo.",
        "- Não use a palavra «compartilhada».",
        "",
        "Marcadores:",
        "1) Pessoal explícito → [[EGO_REMINDER:{...}]]",
        "2) Grupo novo → [[EGO_SHARED_SETUP:{...}]]",
        "3) Grupo existente — marcar → [[EGO_SHARED_EVENT:{...}]]",
        "4) Convidar e-mail (criador) → [[EGO_SHARED_INVITE:{...}]]",
        "5) Apagar grupo (criador) → [[EGO_SHARED_DELETE:{...}]]",
        "",
        f"Estado actual: step={schedule.get('step') or '—'} draft={json.dumps(draft, ensure_ascii=False)}",
    ]
    if only_personal_schedule_available(supabase, user_id):
        lines.append(
            "O utilizador só tem agenda pessoal (sem grupo): "
            "«marca reunião …» → [[EGO_REMINDER:...]] sem perguntar."
        )
    elif schedule_scope_is_ambiguous(user_text, supabase, user_id):
        lines.append(
            "Pedido ambíguo (reunião sem «pessoal» nem «agenda familia»): "
            "pergunte pessoal vs grupo; NÃO envie marcadores até responder."
        )
    elif default_cal:
        lines.append(
            f"Se disser agenda de grupo pelo nome, use «{default_cal}» quando for essa agenda."
        )
    elif is_group_schedule_request(user_text):
        lines.append(
            "Várias agendas de grupo — pergunte QUAL nome se não disse «pessoal» nem o nome da agenda."
        )
    if scope == "shared":
        missing = []
        if not draft.get("calendar_id") and not draft.get("calendar_name"):
            missing.append("qual agenda de grupo (nome, ex. Família)")
        if not draft.get("scheduled_at"):
            missing.append("data e hora")
        if not draft.get("title"):
            missing.append("título do compromisso")
        if missing:
            lines.append(f"Falta na agenda de grupo: {', '.join(missing)}.")
            if not draft.get("calendar_id") and not draft.get("calendar_name"):
                lines.append(
                    "Se for agenda NOVA, peça também e-mails a convidar e use EGO_SHARED_SETUP. "
                    "Se for agenda EXISTENTE (utilizador já é membro), use EGO_SHARED_EVENT — sem e-mails."
                )
            elif not missing or len(missing) <= 1:
                lines.append(
                    "Quando tiver título e data/hora, use EGO_SHARED_EVENT (membros também podem marcar)."
                )
    elif scope == "personal":
        lines.append("Tipo escolhido: pessoal. Use EGO_REMINDER quando data/hora estiverem claras.")
    elif is_group_schedule_request(user_text):
        lines.append(
            "Pedido de grupo (não disse «pessoal»). Use EGO_SHARED_EVENT com calendar_name "
            "por omissão se souber qual."
        )
    lines.append("=== FIM FLUXO ===")
    return "\n".join(lines)


def extract_schedule_draft(text: str) -> tuple[str, dict | None]:
    marker = "[[EGO_SCHEDULE_DRAFT:"
    if marker not in text:
        return text, None
    idx = text.find(marker)
    end = text.find("]]", idx)
    if end == -1:
        return text, None
    raw = text[idx + len(marker) : end].strip()
    clean = (text[:idx].rstrip() + "\n" + text[end + 2 :].lstrip()).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        j0, j1 = raw.find("{"), raw.rfind("}")
        if j0 == -1 or j1 <= j0:
            return text, None
        try:
            obj = json.loads(raw[j0 : j1 + 1])
        except json.JSONDecodeError:
            return text, None
    return clean, obj if isinstance(obj, dict) else None


def extract_shared_setup(text: str) -> tuple[str, dict | None]:
    marker = "[[EGO_SHARED_SETUP:"
    if marker not in text:
        return text, None
    idx = text.find(marker)
    end = text.find("]]", idx)
    if end == -1:
        return text, None
    raw = text[idx + len(marker) : end].strip()
    clean = (text[:idx].rstrip() + "\n" + text[end + 2 :].lstrip()).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        j0, j1 = raw.find("{"), raw.rfind("}")
        if j0 == -1 or j1 <= j0:
            return text, None
        try:
            obj = json.loads(raw[j0 : j1 + 1])
        except json.JSONDecodeError:
            return text, None
    if not isinstance(obj, dict):
        return text, None
    has_cal = bool(obj.get("calendar_id") or obj.get("calendar_name") or obj.get("name"))
    has_when = bool(obj.get("scheduled_at"))
    has_title = bool(obj.get("title") or obj.get("event_title"))
    emails = _normalize_email_list(
        obj.get("invite_emails") or obj.get("emails") or obj.get("members")
    )
    if has_cal and has_when and has_title:
        return clean, obj
    if has_cal and emails:
        return clean, obj
    if has_cal and bool(obj.get("calendar_name") or obj.get("name")):
        return clean, obj
    return text, None


def extract_shared_invite(text: str) -> tuple[str, dict | None]:
    """Convidar e-mail(s) numa agenda compartilhada existente."""
    marker = "[[EGO_SHARED_INVITE:"
    if marker not in text:
        return text, None
    idx = text.find(marker)
    end = text.find("]]", idx)
    if end == -1:
        return text, None
    raw = text[idx + len(marker) : end].strip()
    clean = (text[:idx].rstrip() + "\n" + text[end + 2 :].lstrip()).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        j0, j1 = raw.find("{"), raw.rfind("}")
        if j0 == -1 or j1 <= j0:
            return text, None
        try:
            obj = json.loads(raw[j0 : j1 + 1])
        except json.JSONDecodeError:
            return text, None
    if not isinstance(obj, dict):
        return text, None
    has_cal = bool(obj.get("calendar_id") or obj.get("calendar_name") or obj.get("name"))
    emails = _normalize_email_list(
        obj.get("invite_emails") or obj.get("emails") or obj.get("members")
    )
    phones = _normalize_phone_list(
        obj.get("invite_phones") or obj.get("phones")
    )
    if has_cal and (emails or phones):
        return clean, obj
    return text, None


def extract_shared_event(text: str) -> tuple[str, dict | None]:
    """Compromisso numa agenda compartilhada existente (qualquer membro)."""
    marker = "[[EGO_SHARED_EVENT:"
    if marker not in text:
        return text, None
    idx = text.find(marker)
    end = text.find("]]", idx)
    if end == -1:
        return text, None
    raw = text[idx + len(marker) : end].strip()
    clean = (text[:idx].rstrip() + "\n" + text[end + 2 :].lstrip()).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        j0, j1 = raw.find("{"), raw.rfind("}")
        if j0 == -1 or j1 <= j0:
            return text, None
        try:
            obj = json.loads(raw[j0 : j1 + 1])
        except json.JSONDecodeError:
            return text, None
    if not isinstance(obj, dict):
        return text, None
    has_cal = bool(obj.get("calendar_id") or obj.get("calendar_name") or obj.get("name"))
    has_when = bool(obj.get("scheduled_at"))
    has_title = bool(obj.get("title") or obj.get("event_title"))
    if has_cal and has_when and has_title:
        return clean, obj
    return text, None


def _resolve_calendar_id_for_user(
    supabase: Client | None,
    user_id: str,
    calendar_id: str,
    calendar_name: str,
) -> str | None:
    if not supabase or not user_id:
        return (calendar_id or "").strip() or None
    try:
        from ego_api import shared_calendars as sc

        cid, _ = sc.resolve_calendar_for_user(
            supabase,
            user_id,
            calendar_id=calendar_id,
            calendar_name=calendar_name,
        )
        return cid or None
    except Exception:
        return (calendar_id or "").strip() or None


def process_shared_event(
    supabase: Client | None,
    user_id: str,
    data: dict[str, Any],
    *,
    user_message: str = "",
) -> tuple[list[dict], list[str]]:
    """Marca compromisso numa agenda em que o utilizador já é membro."""
    from ego_api import shared_calendars as sc

    if user_message:
        data = apply_shared_event_fields_from_user(user_message, data)

    calendar_id = _resolve_calendar_id_for_user(
        supabase,
        user_id,
        str(data.get("calendar_id") or ""),
        str(data.get("calendar_name") or data.get("name") or ""),
    )
    title = str(data.get("title") or data.get("event_title") or "Compromisso").strip()[
        :500
    ]
    scheduled_at = data.get("scheduled_at")
    warnings: list[str] = []
    events: list[dict] = []

    if not calendar_id:
        return events, ["Agenda compartilhada não encontrada ou sem acesso."]
    if not scheduled_at:
        return events, ["Data/hora do compromisso em falta."]

    ok, err, event = sc.insert_event(
        supabase,
        user_id,
        calendar_id,
        title=title,
        scheduled_at=scheduled_at,
        announce=title,
    )
    if ok and event:
        events.append(event)
    elif err:
        warnings.append(err)
    return events, warnings


def process_shared_setup(
    supabase: Client | None,
    user_id: str,
    data: dict[str, Any],
    *,
    user_message: str = "",
) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    """Cria agenda (se preciso), convida e-mails e marca compromisso."""
    from ego_api import shared_calendars as sc

    if user_message:
        data = apply_shared_event_fields_from_user(user_message, data)

    calendar_id = str(data.get("calendar_id") or "").strip()
    calendar_name = str(
        data.get("calendar_name") or data.get("name") or ""
    ).strip()[:120]
    title = str(data.get("title") or data.get("event_title") or "Compromisso").strip()[
        :500
    ]
    scheduled_at = data.get("scheduled_at")
    emails = _normalize_email_list(
        data.get("invite_emails") or data.get("emails") or data.get("members")
    )

    warnings: list[str] = []
    calendars: list[dict] = []
    events: list[dict] = []
    members_added: list[dict] = []

    if calendar_id and calendar_name:
        bound = sc.get_calendar(supabase, user_id, calendar_id)
        if bound:
            bound_name = str(bound.get("name") or "").strip()
            if bound_name and sc.calendar_name_key(bound_name) != sc.calendar_name_key(
                calendar_name
            ):
                calendar_id = ""

    if not calendar_id:
        if not calendar_name:
            return calendars, events, members_added, [
                "Informe o nome da agenda compartilhada."
            ]
        calendar_id = (
            _resolve_calendar_id_for_user(supabase, user_id, "", calendar_name) or ""
        )
        if not calendar_id:
            ok, err, cal = sc.create_calendar(supabase, user_id, name=calendar_name)
            if not ok or not cal:
                return calendars, events, members_added, [
                    err or "Não foi possível criar a agenda compartilhada."
                ]
            calendar_id = str(cal.get("id") or "")
            full = sc.get_calendar(supabase, user_id, calendar_id) if calendar_id else None
            calendars.append(full or cal)
    else:
        calendar_id = (
            _resolve_calendar_id_for_user(
                supabase, user_id, calendar_id, calendar_name
            )
            or calendar_id
        )
        if calendar_id and not calendars:
            existing = sc.get_calendar(supabase, user_id, calendar_id)
            if existing:
                calendars.append(existing)

    if not calendar_id:
        return calendars, events, members_added, ["Agenda compartilhada inválida."]

    phones = _normalize_phone_list(
        data.get("invite_phones") or data.get("phones")
    )
    for em in emails:
        ok, err, mem = sc.add_member_by_email(
            supabase, user_id, calendar_id, em
        )
        if ok and mem:
            members_added.append(mem)
        elif err:
            warnings.append(f"{em}: {err}")
    for ph in phones:
        ok, err, mem = sc.add_member_by_phone(supabase, user_id, calendar_id, ph)
        if ok and mem:
            members_added.append(mem)
        elif err:
            warnings.append(f"{ph}: {err}")

    if scheduled_at and title:
        ok, err, event = sc.insert_event(
            supabase,
            user_id,
            calendar_id,
            title=title,
            scheduled_at=scheduled_at,
            announce=title,
        )
        if ok and event:
            events.append(event)
        elif err:
            warnings.append(err)
    elif scheduled_at and not title:
        warnings.append("Informe o título do compromisso para marcar na agenda.")

    if calendar_id:
        full = sc.get_calendar(supabase, user_id, calendar_id)
        if full:
            if calendars:
                calendars[0] = full
            else:
                calendars.append(full)

    return calendars, events, members_added, warnings


def process_shared_invite(
    supabase: Client | None,
    user_id: str,
    data: dict[str, Any],
) -> tuple[dict | None, list[str], list[dict]]:
    """Convida e-mail(s) numa agenda compartilhada existente (qualquer membro ativo)."""
    from ego_api import shared_calendars as sc

    calendar_id = _resolve_calendar_id_for_user(
        supabase,
        user_id,
        str(data.get("calendar_id") or ""),
        str(data.get("calendar_name") or data.get("name") or ""),
    )
    emails = _normalize_email_list(
        data.get("invite_emails") or data.get("emails") or data.get("members")
    )
    phones = _normalize_phone_list(
        data.get("invite_phones") or data.get("phones")
    )
    warnings: list[str] = []
    added: list[dict] = []

    if not calendar_id:
        return None, ["Agenda compartilhada não encontrada."], []
    if not emails and not phones:
        return None, ["Informe e-mail ou telefone a convidar."], []

    for em in emails:
        ok, err, mem = sc.add_member_by_email(supabase, user_id, calendar_id, em)
        if ok and mem:
            added.append(mem)
        elif err:
            warnings.append(f"{em}: {err}")
    for ph in phones:
        ok, err, mem = sc.add_member_by_phone(supabase, user_id, calendar_id, ph)
        if ok and mem:
            added.append(mem)
        elif err:
            warnings.append(f"{ph}: {err}")

    cal = sc.get_calendar(supabase, user_id, calendar_id) if calendar_id else None
    if not added and not warnings:
        warnings.append("Não foi possível adicionar os convites.")
    return cal, warnings, added


def parse_create_shared_calendar_from_plain_text(text: str) -> dict | None:
    """Fallback quando o LLM responde em texto mas não envia [[EGO_SHARED_SETUP:...]]."""
    raw = (text or "").strip()
    if not raw:
        return None
    if not re.search(r"(?i)\b(cria|criar|crie|abre|abrir|novo|nova)\b", raw):
        return None
    if not (
        _SCOPE_SHARED.search(raw)
        or re.search(r"(?i)\bagenda\b", raw)
        or re.search(r"(?i)\bgrupo\b", raw)
    ):
        return None
    cal_name = _extract_create_calendar_name(raw) or _extract_shared_calendar_name(raw)
    if not cal_name:
        m = re.search(
            r"(?i)(?:cria|criar|crie|abre|abrir)\s+(?:a\s+)?"
            r"(?:agenda(?:\s+compartilhada)?\s+)?[«\"']?\s*([^«\"'\n.?]+)",
            raw,
        )
        if m:
            cal_name = _trim_calendar_name_tail(m.group(1))
    if not cal_name:
        return None
    emails = _normalize_email_list(
        re.findall(r"([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})", raw, re.I)
    )
    payload: dict[str, Any] = {"calendar_name": cal_name}
    if emails:
        payload["invite_emails"] = emails
    return payload


def extract_shared_delete(text: str) -> tuple[str, dict | None]:
    """Apagar agenda compartilhada (só criador)."""
    marker = "[[EGO_SHARED_DELETE:"
    if marker not in text:
        return text, None
    idx = text.find(marker)
    end = text.find("]]", idx)
    if end == -1:
        return text, None
    raw = text[idx + len(marker) : end].strip()
    clean = (text[:idx].rstrip() + "\n" + text[end + 2 :].lstrip()).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        j0, j1 = raw.find("{"), raw.rfind("}")
        if j0 == -1 or j1 <= j0:
            return text, None
        try:
            obj = json.loads(raw[j0 : j1 + 1])
        except json.JSONDecodeError:
            return text, None
    if not isinstance(obj, dict):
        return text, None
    if obj.get("calendar_id") or obj.get("calendar_name") or obj.get("name"):
        return clean, obj
    return text, None


def apply_user_delete_calendar_intent(
    user_display: str, data: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Pedido do utilizador define qual agenda apagar (ex. «360 nas alturas»)."""
    parsed = parse_delete_shared_calendar_from_plain_text(user_display)
    if not parsed:
        return data
    name = str(parsed.get("calendar_name") or "").strip()
    if not name:
        return data
    out = dict(data) if isinstance(data, dict) else {}
    out["calendar_name"] = name
    out.pop("calendar_id", None)
    return out


def parse_delete_shared_calendar_from_plain_text(text: str) -> dict | None:
    """Fallback quando o criador pede apagar agenda em texto livre."""
    raw = (text or "").strip()
    if not raw:
        return None
    if not re.search(
        r"(?i)\b(apaga|apagar|deleta|deletar|exclui|excluir|elimina|eliminar|remove|remover)\b",
        raw,
    ):
        return None
    if not (_SCOPE_SHARED.search(raw) or re.search(r"(?i)\bagenda\b", raw)):
        return None
    cal_name = _extract_create_calendar_name(raw) or _extract_shared_calendar_name(raw)
    if not cal_name:
        m = re.search(
            r"(?i)(?:apaga|apagar|deleta|deletar|exclui|excluir|elimina|eliminar)"
            r"\s+(?:a\s+)?(?:agenda(?:\s+compartilhada)?\s+)?[«\"']?\s*([^«\"'\n.?]+)",
            raw,
        )
        if m:
            cal_name = _trim_calendar_name_tail(m.group(1))
    if not cal_name:
        return None
    return {"calendar_name": cal_name}


def process_shared_delete(
    supabase: Client | None,
    user_id: str,
    data: dict[str, Any],
) -> tuple[str, list[str], bool]:
    """Remove agenda compartilhada para todos (só criador)."""
    from ego_api import shared_calendars as sc

    cal_name = str(data.get("calendar_name") or data.get("name") or "").strip()
    calendar_id = str(data.get("calendar_id") or "").strip()
    warnings: list[str] = []

    if calendar_id and cal_name:
        bound = sc.get_calendar(supabase, user_id, calendar_id)
        if bound:
            bound_name = str(bound.get("name") or "").strip()
            if bound_name and sc.calendar_name_key(bound_name) != sc.calendar_name_key(
                cal_name
            ):
                calendar_id = ""

    if not calendar_id and cal_name:
        calendar_id = sc.find_calendar_id_by_name(supabase, user_id, cal_name) or ""

    if not calendar_id:
        hint = (
            f"Agenda «{cal_name}» não encontrada."
            if cal_name
            else "Agenda não encontrada."
        )
        return cal_name, [hint], False

    existing = sc.get_calendar(supabase, user_id, calendar_id)
    if existing:
        cal_name = str(existing.get("name") or cal_name or "Agenda").strip()

    ok, err = sc.delete_calendar(supabase, user_id, calendar_id)
    if ok:
        return cal_name or "Agenda", [], True
    warnings.append(err or "Não foi possível apagar a agenda.")
    return cal_name or "Agenda", warnings, False


_DISMISS_VERBS = re.compile(
    r"(?i)\b(cancela|cancelar|apaga|apagar|deleta|deletar|exclui|excluir|"
    r"remove|remover|elimina|eliminar|desmarca|desmarcar)\b"
)
_COMMITMENT_NOUNS = re.compile(
    r"(?i)\b(reunião|reuniao|reuniões|reunioes|compromisso|compromissos|"
    r"lembrete|lembretes|marcação|marcacao|marcações|marcacoes|consulta|"
    r"evento|eventos|agendamento|agendamentos)\b"
)


def looks_like_dismiss_commitment_intent(text: str) -> bool:
    """Cancelar/apagar um compromisso (não a agenda inteira)."""
    from ego_api.db import VOICE_MESSAGE_MARKER

    raw = (text or "").strip()
    if not raw or raw == VOICE_MESSAGE_MARKER:
        return False
    if not _DISMISS_VERBS.search(raw):
        return False
    cal_del = parse_delete_shared_calendar_from_plain_text(raw)
    if cal_del and str(cal_del.get("calendar_name") or "").strip():
        if re.search(
            r"(?i)(?:apaga|apagar|deleta|deletar|exclui|excluir|remove|remover)\s+"
            r"(?:a\s+)?agenda\b",
            raw,
        ):
            return False
    if re.search(r"(?i)\b(hábito|habito|rotina)\b", raw):
        return True
    if _COMMITMENT_NOUNS.search(raw):
        return True
    if re.search(r"(?i)\b(iss[oa]|aquil[oa]|esse|essa|aquela|aquele)\b", raw):
        return True
    return False


def _extract_dismiss_title_hint(text: str) -> str:
    raw = (text or "").strip()
    patterns = [
        r"(?i)(?:cancela|cancelar|apaga|apagar|deleta|deletar|exclui|excluir|"
        r"remove|remover|desmarca|desmarcar)\s+(?:a\s+)?(?:reunião|reuniao|"
        r"compromisso|lembrete|consulta|marcação|marcacao|evento|agendamento)\s+"
        r"(?:de\s+|do\s+|da\s+)?[«\"']?([^«\"'\n.?]+)",
        r"(?i)(?:cancela|cancelar|apaga|apagar|remove|remover|desmarca|desmarcar)\s+[«\"']?([^«\"'\n.?]+)",
    ]
    for pat in patterns:
        m = re.search(pat, raw)
        if m:
            hint = _trim_calendar_name_tail(m.group(1))
            if hint and len(hint) >= 2:
                return hint
    return ""


def _title_matches_hint(title: str, hint: str) -> bool:
    t = (title or "").strip().lower()
    h = (hint or "").strip().lower()
    if not h:
        return True
    if h in t or t in h:
        return True
    t_tokens = set(re.findall(r"\w{3,}", t))
    h_tokens = set(re.findall(r"\w{3,}", h))
    return bool(t_tokens & h_tokens)


def _when_matches_hint(
    scheduled_at: str | None, target: datetime.datetime | None, *, slack_hours: int = 18
) -> bool:
    if not target:
        return True
    from ego_api.schedule_tz import utc_to_session_local

    parsed = _parse_scheduled_local(scheduled_at)
    if not parsed:
        return False
    local = utc_to_session_local(parsed)
    if local.date() == target.date():
        if target.hour or target.minute:
            return abs((local - target).total_seconds()) <= slack_hours * 3600
        return True
    return False


def process_dismiss_commitments(
    supabase: Client | None,
    user_id: str,
    text: str,
    *,
    ref: datetime.datetime | None = None,
) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    """Apaga compromissos por comando: lembretes, eventos partilhados, hábitos."""
    from ego_api import db
    from ego_api import shared_calendars as sc
    from ego_api.schedule_tz import local_now_from_session

    ref = ref or local_now_from_session()
    title_hint = _extract_dismiss_title_hint(text)
    when_hint = _parse_pt_schedule_hint(text, ref)
    scope = detect_scope_from_user_text(text, supabase, user_id)
    cal_name = _extract_shared_calendar_name(text)
    dismissed_rem: list[dict] = []
    dismissed_ev: list[dict] = []
    dismissed_habits: list[dict] = []
    warnings: list[str] = []

    if re.search(r"(?i)\b(hábito|habito|rotina)\b", text or ""):
        for habit in db.list_agenda(supabase, user_id):
            tit = str(habit.get("titulo") or "").strip()
            if title_hint and not _title_matches_hint(tit, title_hint):
                continue
            hid = str(habit.get("id") or "")
            if hid and db.delete_agenda(supabase, user_id, hid):
                dismissed_habits.append(habit)

    if scope != "shared":
        rem_candidates: list[dict] = []
        for rem in db.list_reminders(supabase, user_id):
            tit = str(rem.get("title") or "").strip()
            if title_hint and not _title_matches_hint(tit, title_hint):
                continue
            if when_hint and not _when_matches_hint(rem.get("scheduled_at"), when_hint):
                continue
            rem_candidates.append(rem)
        if len(rem_candidates) > 1 and not title_hint and not when_hint:
            warnings.append(
                "Há vários compromissos. Diga qual apagar, ex.: «cancela reunião de amanhã»."
            )
        else:
            for rem in rem_candidates[:1] if not title_hint and not when_hint else rem_candidates:
                rid = str(rem.get("id") or "")
                if rid and db.dismiss_reminder(supabase, user_id, rid):
                    dismissed_rem.append(rem)

    if scope != "personal":
        try:
            calendars = sc.list_calendars_for_user(supabase, user_id)
        except Exception:
            calendars = []
        ev_candidates: list[tuple[dict, str, str]] = []
        for cal in calendars:
            cname = str(cal.get("name") or "").strip()
            if cal_name and sc.calendar_name_key(cname) != sc.calendar_name_key(cal_name):
                continue
            cid = str(cal.get("id") or "")
            if not cid:
                continue
            for ev in cal.get("events") or []:
                if ev.get("dismissed"):
                    continue
                tit = str(ev.get("title") or "").strip()
                if title_hint and not _title_matches_hint(tit, title_hint):
                    continue
                if when_hint and not _when_matches_hint(ev.get("scheduled_at"), when_hint):
                    continue
                ev_candidates.append((ev, cid, cname))
        if len(ev_candidates) > 1 and not title_hint and not when_hint:
            warnings.append(
                "Há vários compromissos em grupo. Diga o nome ou a data para apagar."
            )
        else:
            picks = ev_candidates[:1] if not title_hint and not when_hint else ev_candidates
            for ev, cid, cname in picks:
                eid = str(ev.get("id") or "")
                if eid and sc.dismiss_event(supabase, user_id, cid, eid):
                    dismissed_ev.append({**ev, "calendar_id": cid, "calendar_name": cname})

    if not dismissed_rem and not dismissed_ev and not dismissed_habits:
        if looks_like_dismiss_commitment_intent(text):
            warnings.append(
                "Não encontrei esse compromisso. Diga o nome ou a data, "
                "ex.: «cancela reunião de amanhã» ou «apaga consulta sexta 10h»."
            )
    return dismissed_rem, dismissed_ev, dismissed_habits, warnings


_TODAY_AGENDA_QUERY = re.compile(
    r"(?i)(?:"
    r"\bcompromissos?\s+(?:de\s+)?hoje\b|"
    r"\bcompromissos?\s+hoje\b|"
    r"\bo\s+que\s+(?:eu\s+)?(?:tenho|tem)\s+hoje\b|"
    r"\bagenda\s+(?:de\s+)?hoje\b|"
    r"\b(?:reuniões?|lembretes?|marcações?)\s+(?:de\s+)?hoje\b|"
    r"\bhoje\s+(?:tenho|tem)\s+(?:algum|alguma|quais?)\b|"
    r"(?:quais?|mostra(?:r)?|lista(?:r)?|ver)\s+(?:os\s+)?(?:meus\s+)?compromissos?\b"
    r")"
)
_SCHEDULE_CREATE_TODAY = re.compile(
    r"(?i)\b(marcar|marca|agendar|agenda|criar|colocar|ponha|põe|poem)\b"
)


def looks_like_today_agenda_query(text: str) -> bool:
    """Pergunta sobre compromissos de hoje (não pedido para marcar novo)."""
    t = (text or "").strip()
    if not t or not _TODAY_AGENDA_QUERY.search(t):
        return False
    if _SCHEDULE_CREATE_TODAY.search(t):
        return False
    return True


def _local_day_bounds(
    day: datetime.date | None = None,
) -> tuple[datetime.datetime, datetime.datetime]:
    from ego_api.schedule_tz import local_now_from_session

    ref = local_now_from_session()
    local_day = day or ref.date()
    start = datetime.datetime.combine(local_day, datetime.time.min, tzinfo=ref.tzinfo)
    end = start + datetime.timedelta(days=1)
    return start, end


def _parse_scheduled_local(value: object) -> datetime.datetime | None:
    if not value or not str(value).strip():
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        from ego_api.schedule_tz import utc_to_session_local

        return utc_to_session_local(dt)
    except ValueError:
        return None


def _habit_applies_today(dias_csv: object, today_code: str) -> bool:
    raw = str(dias_csv or "").strip().lower()
    if not raw:
        return False
    tokens: set[str] = set()
    for part in re.split(r"[,;\s]+", raw):
        p = part.strip()[:3]
        if not p:
            continue
        aliases = {
            "segunda": "seg",
            "terça": "ter",
            "terca": "ter",
            "quarta": "qua",
            "quinta": "qui",
            "sexta": "sex",
            "sábado": "sab",
            "sabado": "sab",
            "domingo": "dom",
        }
        code = aliases.get(part.strip().lower(), p)
        tokens.add(code)
    return today_code in tokens


def _habit_sort_dt(horario: object, day_start: datetime.datetime) -> datetime.datetime:
    raw = str(horario or "").strip()
    if not raw:
        return day_start
    parts = raw.replace(".", ":").split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return day_start.replace(hour=h, minute=m, second=0, microsecond=0)
    except (ValueError, IndexError):
        return day_start


def build_today_commitments_reply(
    supabase: Client | None, user_id: str
) -> str:
    """Lista compromissos de hoje: pessoal + compartilhadas, com rótulo na frente."""
    from ego_api import db
    from ego_api.config import SUPABASE_REMINDERS_TABLE
    from ego_api import shared_calendars as sc
    from ego_api.db import DOW_PT_ORDER
    from ego_api.supabase_client import apply_user_auth

    from ego_api.schedule_tz import local_now_from_session

    now = local_now_from_session()
    today_code = DOW_PT_ORDER[now.weekday()]
    day_start, day_end = _local_day_bounds(now.date())
    start_utc = day_start.astimezone(datetime.timezone.utc).isoformat()
    end_utc = day_end.astimezone(datetime.timezone.utc).isoformat()

    rows: list[tuple[datetime.datetime, str]] = []

    if supabase and user_id:
        apply_user_auth(supabase)
        try:
            rem = (
                supabase.table(SUPABASE_REMINDERS_TABLE)
                .select("title,scheduled_at")
                .eq("user_id", user_id)
                .eq("dismissed", False)
                .gte("scheduled_at", start_utc)
                .lt("scheduled_at", end_utc)
                .order("scheduled_at")
                .execute()
            )
            for row in rem.data or []:
                when = _parse_scheduled_local(row.get("scheduled_at"))
                if not when:
                    continue
                title = (row.get("title") or "Compromisso").strip()
                line = f"Agenda pessoal — {title} às {when.strftime('%H:%M')}"
                rows.append((when, line))
        except Exception:
            pass

        for habit in db.list_agenda(supabase, user_id):
            if not _habit_applies_today(habit.get("dias_da_semana"), today_code):
                continue
            tit = (habit.get("titulo") or "Hábito").strip()
            hor = str(habit.get("horario") or "")[:5]
            sort_dt = _habit_sort_dt(habit.get("horario"), day_start)
            when_txt = hor if hor else sort_dt.strftime("%H:%M")
            line = f"Agenda pessoal — {tit} às {when_txt}"
            rows.append((sort_dt, line))

        try:
            calendars = sc.list_calendars_for_user(supabase, user_id)
        except Exception:
            calendars = []
        for cal in calendars:
            cid = str(cal.get("id") or "")
            cal_name = (cal.get("name") or "Agenda compartilhada").strip()
            if not cid:
                continue
            for ev in sc.list_events_on_local_day(supabase, user_id, cid, now.date()):
                when = _parse_scheduled_local(ev.get("scheduled_at"))
                if not when:
                    continue
                title = (ev.get("title") or "Compromisso").strip()
                line = f"{cal_name} — {title} às {when.strftime('%H:%M')}"
                rows.append((when, line))

    rows.sort(key=lambda r: r[0])
    date_label = now.strftime("%d/%m/%Y")

    if not rows:
        return (
            f"Para hoje ({date_label}) não tem compromissos na agenda pessoal "
            "nem em agendas compartilhadas."
        )

    lines = [f"Os seus compromissos de hoje ({date_label}):"]
    for _, text in rows:
        lines.append(f"• {text}")
    return "\n".join(lines)
