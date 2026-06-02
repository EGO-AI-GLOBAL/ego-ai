"""Agendas compartilhadas: calendários, membros (e-mail) e reuniões."""

from __future__ import annotations

import datetime
from typing import Any

from ego_api.config import (
    AGENDA_HORIZON_DAYS,
    SUPABASE_SHARED_CALENDAR_EVENTS_TABLE,
    SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE,
    SUPABASE_SHARED_CALENDARS_TABLE,
)
from ego_api.db import normalize_scheduled_at
from ego_api.supabase_client import apply_user_auth, create_service_client

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]


def _normalize_invite_email(raw: str) -> tuple[str, str | None]:
    email = (raw or "").strip().lower()
    if not email or "@" not in email:
        return "", "Informe um e-mail válido de utilizador do EGO-AI."
    if len(email) > 254:
        return "", "E-mail demasiado longo."
    return email, None


def resolve_user_id_by_email(email: str) -> str | None:
    """Procura perfil por e-mail (service role no servidor)."""
    email_norm, _ = _normalize_invite_email(email)
    if not email_norm:
        return None
    admin = create_service_client()
    if not admin:
        return None
    try:
        res = (
            admin.table("profiles")
            .select("id,email")
            .ilike("email", email_norm)
            .limit(5)
            .execute()
        )
        for row in res.data or []:
            stored = str(row.get("email") or "").strip().lower()
            if stored == email_norm:
                return str(row.get("id") or "")
    except Exception:
        pass
    return None


def _user_is_member(
    supabase: Client | None, user_id: str, calendar_id: str
) -> bool:
    if not supabase or not user_id or not calendar_id:
        return False
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("id")
            .eq("calendar_id", calendar_id)
            .eq("user_id", user_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


def list_calendars_for_user(supabase: Client | None, user_id: str) -> list[dict]:
    if not supabase or not user_id:
        return []
    apply_user_auth(supabase)
    try:
        mem = (
            supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("calendar_id,role")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )
        cal_ids = list(
            dict.fromkeys(
                str(r.get("calendar_id") or "")
                for r in (mem.data or [])
                if r.get("calendar_id")
            )
        )
        if not cal_ids:
            return []
        roles = {
            str(r.get("calendar_id")): str(r.get("role") or "member")
            for r in (mem.data or [])
        }
        cals = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("id,owner_user_id,name,created_at")
            .in_("id", cal_ids)
            .order("created_at", desc=True)
            .execute()
        )
        out: list[dict] = []
        for row in cals.data or []:
            cid = str(row.get("id") or "")
            members = list_members(supabase, user_id, cid)
            events = list_events(supabase, user_id, cid)
            out.append(
                {
                    **row,
                    "is_owner": roles.get(cid) == "owner"
                    or str(row.get("owner_user_id")) == user_id,
                    "member_count": len(members),
                    "members": members,
                    "events": events,
                }
            )
        return out
    except Exception:
        return []


def list_members(
    supabase: Client | None, user_id: str, calendar_id: str
) -> list[dict]:
    if not supabase or not calendar_id or not _user_is_member(supabase, user_id, calendar_id):
        return []
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("id,calendar_id,user_id,invited_email,role,status,created_at")
            .eq("calendar_id", calendar_id)
            .order("created_at")
            .execute()
        )
        return list(res.data or [])
    except Exception:
        return []


def list_events(
    supabase: Client | None, user_id: str, calendar_id: str
) -> list[dict]:
    if not supabase or not calendar_id or not _user_is_member(supabase, user_id, calendar_id):
        return []
    apply_user_auth(supabase)
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now.isoformat()
    end = (now + datetime.timedelta(days=AGENDA_HORIZON_DAYS)).isoformat()
    try:
        res = (
            supabase.table(SUPABASE_SHARED_CALENDAR_EVENTS_TABLE)
            .select("*")
            .eq("calendar_id", calendar_id)
            .eq("dismissed", False)
            .gte("scheduled_at", start)
            .lte("scheduled_at", end)
            .order("scheduled_at")
            .execute()
        )
        return list(res.data or [])
    except Exception:
        return []


def create_calendar(
    supabase: Client | None, user_id: str, *, name: str
) -> tuple[bool, str, dict | None]:
    if not supabase or not user_id:
        return False, "Sessão indisponível.", None
    title = (name or "").strip()[:120]
    if not title:
        return False, "Dê um nome à agenda compartilhada.", None
    if not apply_user_auth(supabase):
        return False, "Sessão expirada.", None
    try:
        from ego_api.supabase_client import insert_returning_rows

        inserted = insert_returning_rows(
            supabase,
            SUPABASE_SHARED_CALENDARS_TABLE,
            {"owner_user_id": user_id, "name": title},
        )
        cal = inserted[0] if inserted else {}
        cid = str(cal.get("id") or "")
        if not cid:
            return False, "Não foi possível criar a agenda.", None
        sess_email = ""
        try:
            from ego_api.request_ctx import get_session

            sess = get_session()
            if sess and sess.email:
                sess_email = sess.email.strip().lower()
        except Exception:
            pass
        if not sess_email:
            from ego_api import db

            prof = db.load_profile(supabase, user_id) or {}
            sess_email = str(prof.get("email") or "").strip().lower()
        owner_row = {
            "calendar_id": cid,
            "user_id": user_id,
            "invited_email": sess_email or f"{user_id}@ego.local",
            "role": "owner",
            "status": "active",
        }
        supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).insert(owner_row).execute()
        return True, "", cal
    except Exception as exc:
        return False, str(exc), None


def team_seat_limit_for_owner(supabase: Client | None, owner_user_id: str) -> int | None:
    """Limite de e-mails do plano equipe (ui_state.team_seats). None = sem teto."""
    if not supabase or not owner_user_id:
        return None
    from ego_api import db
    from ego_api.team_stripe_checkout import parse_team_seats

    prof = db.load_profile(supabase, owner_user_id) or {}
    ui = prof.get("ui_state")
    if isinstance(ui, str) and ui.strip():
        import json

        try:
            ui = json.loads(ui)
        except json.JSONDecodeError:
            ui = {}
    if not isinstance(ui, dict):
        return None
    return parse_team_seats(ui.get("team_seats"))


def count_owner_team_member_slots(
    supabase: Client | None, owner_user_id: str
) -> int:
    """E-mails distintos em agendas que o utilizador criou (inclui o criador)."""
    if not supabase or not owner_user_id:
        return 0
    apply_user_auth(supabase)
    try:
        cals = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("id")
            .eq("owner_user_id", owner_user_id)
            .execute()
        )
        cal_ids = [str(r.get("id")) for r in (cals.data or []) if r.get("id")]
        if not cal_ids:
            return 0
        emails: set[str] = set()
        for cid in cal_ids:
            mem = (
                supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
                .select("invited_email")
                .eq("calendar_id", cid)
                .eq("status", "active")
                .execute()
            )
            for row in mem.data or []:
                em = str(row.get("invited_email") or "").strip().lower()
                if em:
                    emails.add(em)
        return len(emails)
    except Exception:
        return 0


def add_member_by_email(
    supabase: Client | None,
    owner_user_id: str,
    calendar_id: str,
    email: str,
) -> tuple[bool, str, dict | None]:
    if not supabase or not owner_user_id or not calendar_id:
        return False, "Sessão indisponível.", None
    email_norm, err = _normalize_invite_email(email)
    if err:
        return False, err, None
    if not _user_is_member(supabase, owner_user_id, calendar_id):
        return False, "Sem acesso a esta agenda.", None
    try:
        cal = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("owner_user_id")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        rows = cal.data or []
        if not rows or str(rows[0].get("owner_user_id")) != owner_user_id:
            return False, "Só o criador da agenda pode convidar por e-mail.", None
    except Exception:
        return False, "Agenda não encontrada.", None

    target_uid = resolve_user_id_by_email(email_norm)
    if not target_uid:
        return (
            False,
            "Este e-mail ainda não tem conta no EGO-AI. A pessoa precisa criar conta primeiro.",
            None,
        )
    if target_uid == owner_user_id:
        return False, "Você já faz parte desta agenda.", None

    apply_user_auth(supabase)
    seat_limit = team_seat_limit_for_owner(supabase, owner_user_id)
    if seat_limit is not None:
        used = count_owner_team_member_slots(supabase, owner_user_id)
        already = False
        try:
            cals = (
                supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
                .select("id")
                .eq("owner_user_id", owner_user_id)
                .execute()
            )
            for cal in cals.data or []:
                cid = str(cal.get("id") or "")
                if not cid:
                    continue
                chk = (
                    supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
                    .select("id")
                    .eq("calendar_id", cid)
                    .eq("invited_email", email_norm)
                    .limit(1)
                    .execute()
                )
                if chk.data:
                    already = True
                    break
        except Exception:
            pass
        if not already and used >= seat_limit:
            return (
                False,
                f"Limite do plano equipe atingido ({seat_limit} pessoas). "
                "Contrate um plano com mais lugares.",
                None,
            )
    try:
        existing = (
            supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("id,user_id")
            .eq("calendar_id", calendar_id)
            .eq("invited_email", email_norm)
            .limit(1)
            .execute()
        )
        if existing.data:
            return False, "Este e-mail já está nesta agenda.", None
        row = {
            "calendar_id": calendar_id,
            "user_id": target_uid,
            "invited_email": email_norm,
            "role": "member",
            "status": "active",
        }
        from ego_api.supabase_client import insert_returning_rows

        inserted = insert_returning_rows(
            supabase, SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE, row
        )
        data = inserted[0] if inserted else row
        return True, "", data
    except Exception as exc:
        low = str(exc).lower()
        if "unique" in low or "duplicate" in low:
            return False, "Este e-mail já está nesta agenda.", None
        return False, str(exc), None


def remove_member(
    supabase: Client | None,
    actor_user_id: str,
    calendar_id: str,
    member_id: str,
) -> tuple[bool, str]:
    if not supabase or not actor_user_id:
        return False, "Sessão indisponível."
    if not _user_is_member(supabase, actor_user_id, calendar_id):
        return False, "Sem acesso."
    apply_user_auth(supabase)
    try:
        mem = (
            supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("id,role,user_id")
            .eq("id", member_id)
            .eq("calendar_id", calendar_id)
            .limit(1)
            .execute()
        )
        if not mem.data:
            return False, "Membro não encontrado."
        row = mem.data[0]
        if str(row.get("role")) == "owner":
            return False, "Não é possível remover o criador da agenda."
        is_owner = False
        cal = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("owner_user_id")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        if cal.data and str(cal.data[0].get("owner_user_id")) == actor_user_id:
            is_owner = True
        if not is_owner and str(row.get("user_id")) != actor_user_id:
            return False, "Só o criador pode remover outros membros."
        supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).delete().eq(
            "id", member_id
        ).execute()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def insert_event(
    supabase: Client | None,
    user_id: str,
    calendar_id: str,
    *,
    title: str,
    scheduled_at: object,
    announce: str = "",
) -> tuple[bool, str, dict | None]:
    if not supabase or not user_id:
        return False, "Sessão indisponível.", None
    if not _user_is_member(supabase, user_id, calendar_id):
        return False, "Sem acesso a esta agenda.", None
    norm = normalize_scheduled_at(scheduled_at)
    if not norm:
        return False, "Data/hora inválida ou fora do horizonte permitido.", None
    if not apply_user_auth(supabase):
        return False, "Sessão expirada.", None
    row = {
        "calendar_id": calendar_id,
        "created_by_user_id": user_id,
        "title": (title or "Reunião")[:500],
        "scheduled_at": norm.isoformat(),
        "announce": (announce or title or "")[:2000],
    }
    try:
        from ego_api.supabase_client import insert_returning_rows

        inserted = insert_returning_rows(
            supabase, SUPABASE_SHARED_CALENDAR_EVENTS_TABLE, row
        )
        event = inserted[0] if inserted else row
        try:
            from ego_api.shared_calendar_notify import (
                calendar_name_by_id,
                notify_members_new_event,
            )

            admin = create_service_client()
            cal_name = calendar_name_by_id(admin, calendar_id) if admin else ""
            if not cal_name:
                cal_row = (
                    supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
                    .select("name")
                    .eq("id", calendar_id)
                    .limit(1)
                    .execute()
                )
                if cal_row.data:
                    cal_name = str(cal_row.data[0].get("name") or "")
            notify_members_new_event(
                calendar_id,
                creator_user_id=user_id,
                calendar_name=cal_name or "Agenda compartilhada",
                title=row["title"],
                scheduled_at_iso=row["scheduled_at"],
                event_id=str(event.get("id") or ""),
            )
        except Exception:
            pass
        return True, "", event
    except Exception as exc:
        return False, str(exc), None


def dismiss_event(
    supabase: Client | None, user_id: str, calendar_id: str, event_id: str
) -> bool:
    if not supabase or not _user_is_member(supabase, user_id, calendar_id):
        return False
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_SHARED_CALENDAR_EVENTS_TABLE).update(
            {"dismissed": True}
        ).eq("id", event_id).eq("calendar_id", calendar_id).execute()
        return True
    except Exception:
        return False


def get_calendar(
    supabase: Client | None, user_id: str, calendar_id: str
) -> dict[str, Any] | None:
    if not supabase or not _user_is_member(supabase, user_id, calendar_id):
        return None
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("id,owner_user_id,name,created_at")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        cal = dict(res.data[0])
        cal["is_owner"] = str(cal.get("owner_user_id")) == user_id
        cal["members"] = list_members(supabase, user_id, calendar_id)
        cal["events"] = list_events(supabase, user_id, calendar_id)
        return cal
    except Exception:
        return None
