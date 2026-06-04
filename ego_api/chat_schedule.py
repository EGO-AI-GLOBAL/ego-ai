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
    r"marcar|marca|agendar|agenda|reunião|reuniao|compromisso|"
    r"lembrete|lembrar|encontro|call|chamada|consulta"
    r")\b",
    re.I,
)


def parse_invite_from_plain_text(text: str) -> dict | None:
    """Fallback quando o LLM responde em texto mas não envia [[EGO_SHARED_INVITE:...]]."""
    raw = (text or "").strip()
    if not raw:
        return None
    if not re.search(r"(?i)\b(convida|convite|adiciona|inclui|adicione|add)\b", raw):
        return None
    em_match = re.search(
        r"([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})", raw, re.I
    )
    if not em_match:
        return None
    cal_match = re.search(
        r"(?i)(?:agenda\s+compartilhada|grupo)\s+[«\"']?\s*([^«\"'\n.?]+)",
        raw,
    )
    if not cal_match:
        return None
    email = em_match.group(1).strip().lower()
    cal_name = _extract_shared_calendar_name(raw) or cal_match.group(1).strip().strip("«»\"' ")
    if not email or not cal_name:
        return None
    return {"calendar_name": cal_name, "invite_emails": [email]}


def _extract_shared_calendar_name(raw: str) -> str:
    def _trim_calendar_tail(name: str) -> str:
        trimmed = re.split(
            r"(?i)\s+(?:reuni|marca|agend|amanh|hoje|depois|às|as|\d)",
            name.strip().strip("«»\"' "),
        )[0].strip()
        return trimmed

    patterns = (
        r"(?i)(?:agenda\s+compartilhada|grupo)\s+[«\"']?\s*([^«\"'\n.?]+)",
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


def _extract_shared_event_title(raw: str) -> str:
    low = raw.lower()
    if re.search(r"\breuni", low):
        return "Reunião"
    if re.search(r"\bencontro\b", low):
        return "Encontro"
    if re.search(r"\bchamada\b|\bcall\b", low):
        return "Chamada"
    if re.search(r"\bconsulta\b", low):
        return "Consulta"
    m = re.search(
        r"(?i)(?:título|titulo)\s+[«\"']?\s*([^«\"'\n.?]+)",
        raw,
    )
    if m:
        title = m.group(1).strip().strip("«»\"' ")
        if title:
            return title[:500]
    return "Compromisso"


def _parse_pt_schedule_hint(text: str) -> datetime.datetime | None:
    """Interpreta frases comuns (hoje/amanhã + hora) para ISO local."""
    raw = (text or "").strip()
    if not raw:
        return None
    ref = datetime.datetime.now().astimezone()
    low = raw.lower()
    tm = re.search(
        r"(?:às|as)\s*(\d{1,2})(?::(\d{2}))?\s*(?:h|horas)?",
        low,
    )
    if not tm:
        tm = re.search(r"\b(\d{1,2}):(\d{2})\b", low)
    if not tm:
        return None
    hour = int(tm.group(1))
    minute = int(tm.group(2) or 0)
    if hour > 23 or minute > 59:
        return None

    day = ref.date()
    if re.search(r"\bdepois de amanhã\b|\bdepois de amanha\b", low):
        day = day + datetime.timedelta(days=2)
    elif re.search(r"\bamanhã\b|\bamanha\b", low):
        day = day + datetime.timedelta(days=1)
    elif re.search(r"\bhoje\b", low):
        pass
    else:
        dm = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", low)
        if dm:
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
        else:
            return None

    try:
        return datetime.datetime.combine(
            day, datetime.time(hour, minute), tzinfo=ref.tzinfo
        )
    except ValueError:
        return None


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


def parse_shared_event_from_plain_text(text: str) -> dict | None:
    """Fallback quando o LLM responde em texto mas não envia [[EGO_SHARED_EVENT:...]]."""
    raw = (text or "").strip()
    if not raw:
        return None
    if not looks_like_schedule_intent(raw):
        return None
    if not _SCOPE_SHARED.search(raw):
        return None
    cal_name = _extract_shared_calendar_name(raw)
    when = _parse_pt_schedule_hint(raw)
    if not cal_name or not when:
        return None
    title = _extract_shared_event_title(raw)
    return {
        "calendar_name": cal_name,
        "title": title,
        "scheduled_at": when.isoformat(),
    }


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


def detect_scope_from_user_text(text: str) -> str | None:
    t = (text or "").strip()
    if not t:
        return None
    if _SCOPE_SHARED.search(t) and not _SCOPE_PERSONAL.search(t):
        return "shared"
    if _SCOPE_PERSONAL.search(t):
        return "personal"
    return None


def looks_like_schedule_intent(text: str) -> bool:
    return bool(_SCHEDULE_INTENT.search(text or ""))


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
        "=== AGENDAS COMPARTILHADAS DO UTILIZADOR ===",
    ]
    if not rows:
        lines.append("(nenhuma ainda — pode criar uma nova pelo chat)")
    else:
        for row in rows[:20]:
            cid = str(row.get("id") or "")
            name = (row.get("name") or "Agenda").strip()
            nmem = row.get("member_count") or len(row.get("members") or [])
            owner = " (criou)" if row.get("is_owner") else " (membro)"
            lines.append(
                f'  - id={cid} | «{name}» | {nmem} membros{owner} — qualquer membro pode marcar compromissos'
            )
    lines.append("=== FIM AGENDAS COMPARTILHADAS ===")
    return "\n".join(lines)


def build_schedule_wizard_context(
    schedule: dict[str, Any], user_text: str
) -> str:
    draft = schedule.get("draft") or {}
    scope = draft.get("scope")
    lines = [
        "",
        "=== FLUXO AGENDAMENTO (CHAT) ===",
        "A aba Agenda no app é só consulta. Tudo o que cria ou altera compromissos faz-se no chat.",
        "Quando o utilizador quiser marcar compromisso/reunião/lembrete:",
        "1) Se ainda não souber o tipo, pergunte UMA vez: «Na sua agenda pessoal ou numa agenda compartilhada?»",
        "2) Pessoal → use [[EGO_REMINDER:{...}]] quando título e data/hora estiverem claros.",
        "3) Compartilhada NOVA: nome (obrigatório), opcional compromisso e e-mails → [[EGO_SHARED_SETUP:{...}]]",
        "4) Compartilhada EXISTENTE — marcar: [[EGO_SHARED_EVENT:{...}]]",
        "5) Convidar e-mail em agenda existente (criador): [[EGO_SHARED_INVITE:{...}]]",
        "6) Apagar agenda compartilhada (só criador): [[EGO_SHARED_DELETE:{...}]]",
        "",
        f"Estado actual: step={schedule.get('step') or '—'} draft={json.dumps(draft, ensure_ascii=False)}",
    ]
    if scope == "shared":
        missing = []
        if not draft.get("calendar_id") and not draft.get("calendar_name"):
            missing.append("qual agenda compartilhada (nome ou escolha da lista)")
        if not draft.get("scheduled_at"):
            missing.append("data e hora")
        if not draft.get("title"):
            missing.append("título do compromisso")
        if missing:
            lines.append(f"Falta na agenda compartilhada: {', '.join(missing)}.")
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
    elif looks_like_schedule_intent(user_text):
        lines.append(
            "Parece pedido de agendamento. Comece perguntando pessoal vs compartilhada (sem marcadores ainda)."
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
    if has_cal and emails:
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
    cid = (calendar_id or "").strip()
    if cid:
        return cid
    name = (calendar_name or "").strip()
    if not name or not supabase or not user_id:
        return None
    try:
        from ego_api import shared_calendars as sc

        found = sc.find_calendar_id_by_name(supabase, user_id, name)
        if found:
            return found
    except Exception:
        pass
    return None


def process_shared_event(
    supabase: Client | None,
    user_id: str,
    data: dict[str, Any],
) -> tuple[list[dict], list[str]]:
    """Marca compromisso numa agenda em que o utilizador já é membro."""
    from ego_api import shared_calendars as sc

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
) -> tuple[list[dict], list[dict], list[str]]:
    """Cria agenda (se preciso), convida e-mails e marca compromisso."""
    from ego_api import shared_calendars as sc

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

    if not calendar_id:
        if not calendar_name:
            return calendars, events, ["Informe o nome da agenda compartilhada."]
        calendar_id = (
            _resolve_calendar_id_for_user(supabase, user_id, "", calendar_name) or ""
        )
        if not calendar_id:
            ok, err, cal = sc.create_calendar(supabase, user_id, name=calendar_name)
            if not ok or not cal:
                return calendars, events, [
                    err or "Não foi possível criar a agenda compartilhada."
                ]
            calendar_id = str(cal.get("id") or "")
            calendars.append(cal)
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
        return calendars, events, ["Agenda compartilhada inválida."]

    for em in emails:
        ok, err, _mem = sc.add_member_by_email(
            supabase, user_id, calendar_id, em
        )
        if not ok and err:
            warnings.append(f"{em}: {err}")

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

    return calendars, events, warnings


def process_shared_invite(
    supabase: Client | None,
    user_id: str,
    data: dict[str, Any],
) -> tuple[dict | None, list[str], list[dict]]:
    """Convida e-mail(s) numa agenda compartilhada existente (criador)."""
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
    warnings: list[str] = []
    added: list[dict] = []

    if not calendar_id:
        return None, ["Agenda compartilhada não encontrada."], []
    if not emails:
        return None, ["Informe o e-mail a convidar."], []

    for em in emails:
        ok, err, mem = sc.add_member_by_email(supabase, user_id, calendar_id, em)
        if ok and mem:
            added.append(mem)
        elif err:
            warnings.append(f"{em}: {err}")

    cal = sc.get_calendar(supabase, user_id, calendar_id) if added else None
    if not added and not warnings:
        warnings.append("Não foi possível adicionar os e-mails.")
    return cal, warnings, added


def parse_create_shared_calendar_from_plain_text(text: str) -> dict | None:
    """Fallback quando o LLM responde em texto mas não envia [[EGO_SHARED_SETUP:...]]."""
    raw = (text or "").strip()
    if not raw:
        return None
    if not re.search(r"(?i)\b(cria|criar|crie|abre|abrir|novo|nova)\b", raw):
        return None
    if not (_SCOPE_SHARED.search(raw) or re.search(r"(?i)\bagenda\b", raw)):
        return None
    cal_name = _extract_shared_calendar_name(raw)
    if not cal_name:
        m = re.search(
            r"(?i)(?:cria|criar|crie|abre|abrir)\s+(?:a\s+)?"
            r"(?:agenda\s+compartilhada\s+)?[«\"']?\s*([^«\"'\n.?]+)",
            raw,
        )
        if m:
            cal_name = re.split(
                r"(?i)\s+(?:reuni|marca|agend|convida|amanh|hoje|depois|às|as|\d)",
                m.group(1).strip().strip("«»\"' "),
            )[0].strip()
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


def parse_delete_shared_calendar_from_plain_text(text: str) -> dict | None:
    """Fallback quando o criador pede apagar agenda em texto livre."""
    raw = (text or "").strip()
    if not raw:
        return None
    if not re.search(
        r"(?i)\b(apaga|apagar|deleta|deletar|exclui|excluir|elimina|eliminar)\b",
        raw,
    ):
        return None
    if not (_SCOPE_SHARED.search(raw) or re.search(r"(?i)\bagenda\b", raw)):
        return None
    cal_name = _extract_shared_calendar_name(raw)
    if not cal_name:
        m = re.search(
            r"(?i)(?:apaga|apagar|deleta|deletar|exclui|excluir|elimina|eliminar)"
            r"\s+(?:a\s+)?(?:agenda\s+compartilhada\s+)?[«\"']?\s*([^«\"'\n.?]+)",
            raw,
        )
        if m:
            cal_name = re.split(
                r"(?i)\s+(?:reuni|marca|agend|amanh|hoje|depois|às|as|\d)",
                m.group(1).strip().strip("«»\"' "),
            )[0].strip()
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

    calendar_id = _resolve_calendar_id_for_user(
        supabase,
        user_id,
        str(data.get("calendar_id") or ""),
        str(data.get("calendar_name") or data.get("name") or ""),
    )
    cal_name = str(data.get("calendar_name") or data.get("name") or "").strip()
    warnings: list[str] = []

    if not calendar_id:
        return cal_name, ["Agenda compartilhada não encontrada."], False

    existing = sc.get_calendar(supabase, user_id, calendar_id)
    if existing:
        cal_name = str(existing.get("name") or cal_name or "Agenda").strip()

    ok, err = sc.delete_calendar(supabase, user_id, calendar_id)
    if ok:
        return cal_name or "Agenda", [], True
    warnings.append(err or "Não foi possível apagar a agenda.")
    return cal_name or "Agenda", warnings, False


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
    ref = datetime.datetime.now().astimezone()
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
        return dt.astimezone()
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

    now = datetime.datetime.now().astimezone()
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
