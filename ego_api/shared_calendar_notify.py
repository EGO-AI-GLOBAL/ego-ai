"""Avisos aos membros quando há novo compromisso em agenda compartilhada."""

from __future__ import annotations

import datetime

from ego_api.config import SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE, SUPABASE_SHARED_CALENDARS_TABLE
from ego_api.expo_push import send_expo_push
from ego_api.supabase_client import create_service_client

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]


def _format_when_pt(iso: str) -> str:
    raw = (iso or "").strip()
    if not raw:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        local = dt.astimezone()
        return local.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return raw[:16].replace("T", " ")


def _ui_state_dict(profile: dict | None) -> dict:
    if not profile:
        return {}
    ui = profile.get("ui_state")
    if isinstance(ui, dict):
        return ui
    if isinstance(ui, str) and ui.strip():
        import json

        try:
            parsed = json.loads(ui)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _creator_label(admin: Client, user_id: str) -> str:
    try:
        res = (
            admin.table("profiles")
            .select("email,full_name,name")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        name = str(row.get("full_name") or row.get("name") or "").strip()
        if name:
            return name
        email = str(row.get("email") or "").strip()
        if email and "@" in email:
            return email.split("@")[0]
    except Exception:
        pass
    return "Um membro"


def _member_push_tokens(
    admin: Client, calendar_id: str, exclude_user_id: str
) -> list[tuple[str, str]]:
    """(user_id, expo_push_token) de membros activos, excepto quem criou o evento."""
    out: list[tuple[str, str]] = []
    try:
        mem = (
            admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("user_id")
            .eq("calendar_id", calendar_id)
            .eq("status", "active")
            .execute()
        )
        for row in mem.data or []:
            uid = str(row.get("user_id") or "")
            if not uid or uid == exclude_user_id:
                continue
            prof = (
                admin.table("profiles")
                .select("ui_state")
                .eq("id", uid)
                .limit(1)
                .execute()
            )
            pr = (prof.data or [{}])[0]
            ui = _ui_state_dict(pr if isinstance(pr, dict) else None)
            tok = str(ui.get("expo_push_token") or "").strip()
            if tok:
                out.append((uid, tok))
    except Exception:
        pass
    return out


def notify_members_new_event(
    calendar_id: str,
    *,
    creator_user_id: str,
    calendar_name: str,
    title: str,
    scheduled_at_iso: str,
    event_id: str = "",
) -> int:
    """Push imediato aos outros membros. Devolve nº de tokens notificados."""
    admin = create_service_client()
    if not admin or not calendar_id:
        return 0
    cal_title = (calendar_name or "Agenda compartilhada").strip()[:120]
    event_title = (title or "Compromisso").strip()[:200]
    when = _format_when_pt(scheduled_at_iso)
    actor = _creator_label(admin, creator_user_id)
    body = f"{actor} marcou: {event_title}"
    if when:
        body += f" · {when}"
    tokens = [t for _, t in _member_push_tokens(admin, calendar_id, creator_user_id)]
    return send_expo_push(
        tokens,
        title=f"📅 {cal_title}",
        body=body,
        data={
            "type": "shared_calendar_event",
            "calendar_id": calendar_id,
            "event_id": event_id,
        },
    )


def calendar_name_by_id(admin: Client, calendar_id: str) -> str:
    try:
        res = (
            admin.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("name")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return str(res.data[0].get("name") or "").strip() or "Agenda compartilhada"
    except Exception:
        pass
    return "Agenda compartilhada"


def _push_token_for_user(admin: Client, user_id: str) -> str:
    if not admin or not user_id:
        return ""
    try:
        prof = (
            admin.table("profiles")
            .select("ui_state")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        pr = (prof.data or [{}])[0]
        ui = _ui_state_dict(pr if isinstance(pr, dict) else None)
        return str(ui.get("expo_push_token") or "").strip()
    except Exception:
        return ""


def notify_member_invited_to_calendar(
    calendar_id: str,
    *,
    inviter_user_id: str,
    invited_user_id: str,
) -> int:
    """Push quando alguém é adicionado a Entre Nós / agenda compartilhada."""
    admin = create_service_client()
    if not admin or not calendar_id or not invited_user_id:
        return 0
    if invited_user_id == inviter_user_id:
        return 0
    tok = _push_token_for_user(admin, invited_user_id)
    if not tok:
        return 0
    cal_name = calendar_name_by_id(admin, calendar_id)
    inviter = _creator_label(admin, inviter_user_id)
    try:
        from ego_api.shared_calendars import is_entre_nos_calendar

        entre_nos = is_entre_nos_calendar(cal_name)
    except Exception:
        entre_nos = "entre nos" in cal_name.lower() or "entrenos" in cal_name.lower()
    if entre_nos:
        title = "Entre Nós"
        body = f"{inviter} convidou você para «{cal_name}». Abra a Agenda."
        push_type = "entre_nos_invite"
    else:
        title = f"📅 {cal_name[:80]}"
        body = f"{inviter} convidou você para a agenda «{cal_name}»."
        push_type = "shared_calendar_invite"
    return send_expo_push(
        [tok],
        title=title,
        body=body[:500],
        data={
            "type": push_type,
            "screen": "agenda",
            "calendar_id": calendar_id,
        },
    )


def notify_invite_response(
    calendar_id: str,
    *,
    creator_user_id: str,
    responder_user_id: str,
    event_title: str,
    accepted: bool,
) -> int:
    """Push ao criador do convite quando o parceiro confirma ou recusa."""
    admin = create_service_client()
    if not admin or not calendar_id or not creator_user_id:
        return 0
    if creator_user_id == responder_user_id:
        return 0
    tok = _push_token_for_user(admin, creator_user_id)
    if not tok:
        return 0
    cal_name = calendar_name_by_id(admin, calendar_id)
    who = _creator_label(admin, responder_user_id)
    title_short = (event_title or "Compromisso").strip()[:80]
    try:
        from ego_api.shared_calendars import is_entre_nos_calendar

        entre_nos = is_entre_nos_calendar(cal_name)
    except Exception:
        entre_nos = "entrenos" in cal_name.lower()
    if accepted:
        body = f"{who} confirmou «{title_short}»"
    else:
        body = f"{who} recusou «{title_short}»"
    if entre_nos:
        title = "Entre Nós"
        push_type = "entre_nos_response"
    else:
        title = f"📅 {cal_name[:80]}"
        push_type = "shared_calendar_response"
    return send_expo_push(
        [tok],
        title=title,
        body=body[:500],
        data={
            "type": push_type,
            "screen": "agenda",
            "calendar_id": calendar_id,
        },
    )
