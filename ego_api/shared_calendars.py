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

EMAIL_NO_ACCOUNT_MSG = (
    "Este e-mail ainda não tem conta no EGO-AI. "
    "Peça para a pessoa instalar o app, criar conta com o mesmo e-mail "
    "e só depois adicioná-la aqui."
)


def _normalize_invite_email(raw: str) -> tuple[str, str | None]:
    email = (raw or "").strip().lower()
    if not email or "@" not in email:
        return "", "Informe um e-mail válido de utilizador do EGO-AI."
    if len(email) > 254:
        return "", "E-mail demasiado longo."
    return email, None


def _backfill_profile_email(admin: Client, user_id: str, email: str) -> None:
    """Garante e-mail em profiles (convites usam auth.users como fallback)."""
    if not user_id or not email:
        return
    try:
        admin.table("profiles").update({"email": email}).eq("id", user_id).execute()
    except Exception:
        pass


def _lookup_profile_id_by_email(admin: Client, email_norm: str) -> str | None:
    try:
        res = (
            admin.table("profiles")
            .select("id,email")
            .not_.is_("email", "null")
            .ilike("email", email_norm)
            .limit(10)
            .execute()
        )
        for row in res.data or []:
            stored = str(row.get("email") or "").strip().lower()
            if stored == email_norm:
                return str(row.get("id") or "")
    except Exception:
        pass
    return None


def _lookup_auth_user_id_by_email(email_norm: str) -> str | None:
    """auth.users via Admin API (service role). profiles.email pode estar vazio."""
    from ego_api.config import read_env, supabase_url

    base = supabase_url().rstrip("/")
    key = read_env("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not key:
        return None

    try:
        import httpx
    except ImportError:
        return None

    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    try:
        with httpx.Client(timeout=12.0) as client:
            for params in (
                {"page": 1, "per_page": 50, "email": email_norm},
                {"page": 1, "per_page": 50, "keyword": email_norm},
            ):
                resp = client.get(
                    f"{base}/auth/v1/admin/users",
                    params=params,
                    headers=headers,
                )
                if resp.status_code >= 400:
                    continue
                payload = resp.json()
                users = (
                    payload.get("users")
                    if isinstance(payload, dict)
                    else (payload if isinstance(payload, list) else [])
                )
                for user in users or []:
                    if not isinstance(user, dict):
                        continue
                    stored = str(user.get("email") or "").strip().lower()
                    if stored == email_norm:
                        return str(user.get("id") or "")

            page = 1
            while page <= 3:
                resp = client.get(
                    f"{base}/auth/v1/admin/users",
                    params={"page": page, "per_page": 200},
                    headers=headers,
                )
                if resp.status_code >= 400:
                    break
                payload = resp.json()
                users = (
                    payload.get("users")
                    if isinstance(payload, dict)
                    else (payload if isinstance(payload, list) else [])
                )
                if not users:
                    break
                for user in users:
                    if not isinstance(user, dict):
                        continue
                    stored = str(user.get("email") or "").strip().lower()
                    if stored == email_norm:
                        return str(user.get("id") or "")
                if len(users) < 200:
                    break
                page += 1
    except Exception:
        pass
    return None


def _lookup_user_id_via_rpc(admin: Client, email_norm: str) -> str | None:
    try:
        res = admin.rpc("lookup_user_id_by_email", {"p_email": email_norm}).execute()
        raw = res.data
        if raw is None:
            return None
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        if isinstance(raw, list) and raw:
            return str(raw[0]).strip() or None
    except Exception:
        pass
    return None


def resolve_user_id_by_email(email: str) -> str | None:
    """Procura utilizador por e-mail (profiles, RPC auth ou Admin API)."""
    email_norm, _ = _normalize_invite_email(email)
    if not email_norm:
        return None
    admin = create_service_client()
    if not admin:
        return None

    uid = _lookup_profile_id_by_email(admin, email_norm)
    if uid:
        return uid

    uid = _lookup_user_id_via_rpc(admin, email_norm)
    if uid:
        _backfill_profile_email(admin, uid, email_norm)
        return uid

    uid = _lookup_auth_user_id_by_email(email_norm)
    if uid:
        _backfill_profile_email(admin, uid, email_norm)
        return uid

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


def _user_day_start_utc() -> datetime.datetime:
    """Início do dia local do utilizador (para listar compromissos de hoje)."""
    try:
        from ego_api.request_ctx import get_session

        sess = get_session()
        if sess and isinstance(sess.tz_offset_min, int):
            tz = datetime.timezone(datetime.timedelta(minutes=int(sess.tz_offset_min)))
            now_local = datetime.datetime.now(tz)
            day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            return day_start.astimezone(datetime.timezone.utc)
    except Exception:
        pass
    return datetime.datetime.now(datetime.timezone.utc)


def link_shared_memberships_for_user(
    supabase: Client | None, user_id: str, email: str
) -> int:
    """Associa convites gravados por e-mail ao user_id actual (login / bootstrap)."""
    email_norm, err = _normalize_invite_email(email)
    if err or not email_norm or not user_id:
        return 0
    admin = create_service_client()
    if not admin:
        return 0
    try:
        res = (
            admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("id,user_id,status")
            .eq("invited_email", email_norm)
            .execute()
        )
        updated = 0
        for row in res.data or []:
            rid = str(row.get("id") or "")
            current = str(row.get("user_id") or "")
            if not rid or current == user_id:
                continue
            admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).update(
                {"user_id": user_id, "status": "active"}
            ).eq("id", rid).execute()
            updated += 1
        return updated
    except Exception as exc:
        print(
            f"[EGO] link_shared_memberships_for_user error user={user_id}: {exc}",
            flush=True,
        )
        return 0


def list_calendars_for_user(supabase: Client | None, user_id: str) -> list[dict]:
    if not supabase or not user_id:
        return []
    try:
        from ego_api import db
        from ego_api.request_ctx import get_session

        sess = get_session()
        em = (sess.email if sess else "") or ""
        if not em:
            prof = db.load_profile(supabase, user_id) or {}
            em = str(prof.get("email") or "")
        if em:
            link_shared_memberships_for_user(supabase, user_id, em)
    except Exception:
        pass
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
    except Exception as exc:
        print(f"[EGO] list_calendars_for_user error user={user_id}: {exc}", flush=True)
        return []


def find_calendar_id_by_name(
    supabase: Client | None, user_id: str, calendar_name: str
) -> str | None:
    """Procura agenda do utilizador por nome (exacto ou parcial, case-insensitive)."""
    needle = (calendar_name or "").strip().lower()
    if not needle or not supabase or not user_id:
        return None
    try:
        rows = list_calendars_for_user(supabase, user_id)
    except Exception:
        return None
    exact: str | None = None
    partial: list[str] = []
    for row in rows:
        cid = str(row.get("id") or "")
        row_name = str(row.get("name") or "").strip().lower()
        if not cid or not row_name:
            continue
        if row_name == needle:
            exact = cid
            break
        if needle in row_name or row_name in needle:
            partial.append(cid)
    if exact:
        return exact
    if len(partial) == 1:
        return partial[0]
    return None


def _member_display_name(
    admin: Client | None, user_id: str | None, email: str
) -> str:
    """Nome amigável (profiles.full_name = «como quer ser chamado»)."""
    uid = (user_id or "").strip()
    if admin and uid:
        try:
            res = (
                admin.table("profiles")
                .select("full_name,name")
                .eq("id", uid)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if rows:
                name = str(rows[0].get("full_name") or rows[0].get("name") or "").strip()
                if name:
                    return name[:120]
        except Exception:
            pass
    em = (email or "").strip().lower()
    if em and "@" in em:
        return em.split("@", 1)[0][:80]
    return "Membro"


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
        members = list(res.data or [])
        admin = create_service_client()
        for row in members:
            row["display_name"] = _member_display_name(
                admin,
                str(row.get("user_id") or "") or None,
                str(row.get("invited_email") or ""),
            )
        return members
    except Exception:
        return []


def list_events(
    supabase: Client | None, user_id: str, calendar_id: str
) -> list[dict]:
    if not supabase or not calendar_id or not _user_is_member(supabase, user_id, calendar_id):
        return []
    apply_user_auth(supabase)
    start = _user_day_start_utc().isoformat()
    end = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=AGENDA_HORIZON_DAYS)
    ).isoformat()
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


def list_events_on_local_day(
    supabase: Client | None,
    user_id: str,
    calendar_id: str,
    day: datetime.date | None = None,
) -> list[dict]:
    """Compromissos de um dia (fuso local), incluindo os que já passaram hoje."""
    if not supabase or not calendar_id or not _user_is_member(supabase, user_id, calendar_id):
        return []
    apply_user_auth(supabase)
    ref = datetime.datetime.now().astimezone()
    local_day = day or ref.date()
    start_local = datetime.datetime.combine(local_day, datetime.time.min, tzinfo=ref.tzinfo)
    end_local = start_local + datetime.timedelta(days=1)
    start = start_local.astimezone(datetime.timezone.utc).isoformat()
    end = end_local.astimezone(datetime.timezone.utc).isoformat()
    try:
        res = (
            supabase.table(SUPABASE_SHARED_CALENDAR_EVENTS_TABLE)
            .select("*")
            .eq("calendar_id", calendar_id)
            .eq("dismissed", False)
            .gte("scheduled_at", start)
            .lt("scheduled_at", end)
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

    from ego_api.supabase_client import create_service_client, insert_returning_rows

    cal_row = {"owner_user_id": user_id, "name": title}
    last_err = ""

    def _insert_calendar(client) -> list[dict]:
        return insert_returning_rows(
            client,
            SUPABASE_SHARED_CALENDARS_TABLE,
            cal_row,
            raise_errors=True,
        )

    inserted: list[dict] = []
    try:
        inserted = _insert_calendar(supabase)
    except Exception as exc:
        last_err = str(exc)
        if "SyncQueryRequestBuilder" in last_err and "select" in last_err:
            return (
                False,
                "Servidor em atualização. Aguarde 2 minutos e tente de novo.",
                None,
            )

    admin = create_service_client()
    if not inserted and admin:
        try:
            inserted = _insert_calendar(admin)
            last_err = ""
        except Exception as exc:
            last_err = str(exc) or last_err

    cal = inserted[0] if inserted else {}
    cid = str(cal.get("id") or "")

    if not cid and supabase:
        try:
            lookup = (
                supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
                .select("id,owner_user_id,name,created_at")
                .eq("owner_user_id", user_id)
                .eq("name", title)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if lookup.data:
                cal = lookup.data[0]
                cid = str(cal.get("id") or "")
        except Exception:
            pass

    if not cid:
        low = last_err.lower()
        if "42p01" in low or "does not exist" in low or "shared_calendars" in low:
            return (
                False,
                "Tabela shared_calendars em falta. Execute a migration no Supabase SQL Editor.",
                None,
            )
        return (
            False,
            last_err or "Não foi possível criar a agenda. Confirme SUPABASE_SERVICE_ROLE_KEY no Railway.",
            None,
        )

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
    try:
        member_client = admin or supabase
        insert_returning_rows(
            member_client,
            SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE,
            owner_row,
            raise_errors=True,
        )
    except Exception as exc:
        return False, str(exc), None

    return True, "", cal


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
        if not create_service_client():
            return (
                False,
                "Convites por e-mail indisponíveis no servidor. "
                "Confirme SUPABASE_SERVICE_ROLE_KEY no Railway e faça redeploy.",
                None,
            )
        return False, EMAIL_NO_ACCOUNT_MSG, None
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
            prev = existing.data[0]
            prev_uid = str(prev.get("user_id") or "")
            if prev_uid == target_uid:
                return False, "Este e-mail já está nesta agenda.", None
            member_id = str(prev.get("id") or "")
            if member_id:
                admin = create_service_client()
                client = admin or supabase
                try:
                    client.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).update(
                        {
                            "user_id": target_uid,
                            "invited_email": email_norm,
                            "status": "active",
                        }
                    ).eq("id", member_id).execute()
                    refreshed = (
                        client.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
                        .select("*")
                        .eq("id", member_id)
                        .limit(1)
                        .execute()
                    )
                    data = (refreshed.data or [prev])[0]
                    return True, "", data
                except Exception as exc:
                    return False, str(exc), None
            return False, "Este e-mail já está nesta agenda.", None
        row = {
            "calendar_id": calendar_id,
            "user_id": target_uid,
            "invited_email": email_norm,
            "role": "member",
            "status": "active",
        }
        from ego_api.supabase_client import insert_with_admin_fallback

        inserted = insert_with_admin_fallback(
            supabase, SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE, row, raise_errors=True
        )
        data = inserted[0] if inserted else row
        return True, "", data
    except Exception as exc:
        low = str(exc).lower()
        if "unique" in low or "duplicate" in low:
            return False, "Este e-mail já está nesta agenda.", None
        if "SyncQueryRequestBuilder" in str(exc) and "select" in str(exc):
            return (
                False,
                "Servidor em atualização. Aguarde 2 minutos e tente de novo.",
                None,
            )
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
        from ego_api.supabase_client import insert_with_admin_fallback

        inserted = insert_with_admin_fallback(
            supabase, SUPABASE_SHARED_CALENDAR_EVENTS_TABLE, row, raise_errors=True
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


def delete_calendar(
    supabase: Client | None, owner_user_id: str, calendar_id: str
) -> tuple[bool, str]:
    """Remove a agenda para todos (membros e eventos em cascade). Só o criador."""
    if not supabase or not owner_user_id or not calendar_id:
        return False, "Sessão indisponível."
    if not apply_user_auth(supabase):
        return False, "Sessão expirada."
    try:
        cal = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("id,owner_user_id,name")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        if not cal.data:
            return False, "Agenda não encontrada."
        row = cal.data[0]
        if str(row.get("owner_user_id")) != owner_user_id:
            return False, "Só quem criou a agenda pode apagá-la."
        try:
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE).delete().eq(
                "id", calendar_id
            ).execute()
            return True, ""
        except Exception as exc:
            admin = create_service_client()
            if not admin:
                return False, str(exc)
            admin.table(SUPABASE_SHARED_CALENDARS_TABLE).delete().eq(
                "id", calendar_id
            ).execute()
            return True, ""
    except Exception as exc:
        return False, str(exc)


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
