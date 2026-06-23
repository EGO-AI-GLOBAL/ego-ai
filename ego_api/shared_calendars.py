"""Agendas compartilhadas: calendários, membros (e-mail) e reuniões."""

from __future__ import annotations

import datetime
import re
import unicodedata
from typing import Any


def calendar_name_key(name: str) -> str:
    """Compara nomes sem diferir maiúsculas, acentos, espaços nem pontuação."""
    raw = unicodedata.normalize("NFD", (name or "").strip().lower())
    ascii_only = "".join(c for c in raw if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", ascii_only)


ENTRE_NOS_NAME_KEYS = frozenset(
    {
        "entrenos",
        "nosdois",
        "familia",
        "family",
        "casa",
        "casal",
    }
)


def is_entre_nos_calendar(name: str) -> bool:
    """Agenda casal 1-a-1 (prefixo «Entre Nós · …») — confirmar/recusar convites."""
    key = calendar_name_key(name)
    if not key:
        return False
    return key == "entrenos" or key.startswith("entrenos")


def _normalize_event_row(row: dict) -> dict:
    from ego_api.db import _scheduled_at_api_iso

    out = dict(row)
    if out.get("scheduled_at"):
        out["scheduled_at"] = _scheduled_at_api_iso(out.get("scheduled_at"))
    out["invite_status"] = str(out.get("invite_status") or "none")
    return out


from ego_api.config import (
    AGENDA_HORIZON_DAYS,
    MAX_MEMBERS_PER_SHARED_CALENDAR,
    MAX_SHARED_CALENDARS_PER_OWNER,
    SUPABASE_SHARED_CALENDAR_EVENTS_TABLE,
    SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE,
    SUPABASE_SHARED_CALENDARS_TABLE,
)
from ego_api.db import normalize_scheduled_at
from ego_api.phone_utils import (
    format_phone_display,
    normalize_phone_br,
    phone_invite_email_placeholder,
)
from ego_api.supabase_client import apply_user_auth, create_service_client

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

EMAIL_NO_ACCOUNT_MSG = (
    "Este e-mail ainda não tem conta no EGO-AI. "
    "Peça para a pessoa instalar o app e criar conta com o mesmo e-mail; "
    "o convite fica guardado e a agenda aparece quando ela entrar."
)

PENDING_INVITE_MSG_ENTRE_NOS = (
    "Convite enviado. A pessoa verá na Agenda (Entre Nós) para aceitar "
    "quando entrar no EGO com o mesmo e-mail ou telefone."
)

PENDING_INVITE_MSG_GRUPO = (
    "Convite enviado. A pessoa verá na Agenda compartilhada para aceitar "
    "quando entrar no EGO com o mesmo e-mail ou telefone."
)

# Compatibilidade com código que ainda importa o nome antigo.
PENDING_INVITE_MSG = PENDING_INVITE_MSG_ENTRE_NOS


def _pending_invite_message(supabase: Client | None, calendar_id: str) -> str:
    if is_entre_nos_calendar(_calendar_name(supabase, calendar_id)):
        return PENDING_INVITE_MSG_ENTRE_NOS
    return PENDING_INVITE_MSG_GRUPO


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


PHONE_NO_ACCOUNT_MSG = (
    "Este telefone ainda não tem conta no EGO-AI. "
    "Peça para instalar o app e criar conta com o mesmo número; "
    "o convite fica guardado até entrarem."
)


def resolve_user_id_by_phone(phone: str) -> str | None:
    phone_norm, err = normalize_phone_br(phone)
    if err or not phone_norm:
        return None
    admin = create_service_client()
    if not admin:
        return None
    try:
        res = (
            admin.table("profiles")
            .select("id,phone")
            .eq("phone", phone_norm)
            .limit(3)
            .execute()
        )
        for row in res.data or []:
            if str(row.get("phone") or "").strip() == phone_norm:
                return str(row.get("id") or "") or None
    except Exception:
        pass
    return None


def push_after_member_invited(
    calendar_id: str,
    actor_user_id: str,
    member_row: dict | None,
) -> None:
    """Push ao convidado quando entra no grupo (conta já activa)."""
    if not member_row or not calendar_id:
        return
    if str(member_row.get("status") or "") != "active":
        return
    invited = str(member_row.get("user_id") or "").strip()
    if not invited or invited == actor_user_id:
        return
    try:
        from ego_api.shared_calendar_notify import notify_member_invited_to_calendar

        notify_member_invited_to_calendar(
            calendar_id,
            inviter_user_id=actor_user_id,
            invited_user_id=invited,
        )
    except Exception:
        pass


def _calendar_owner_id(admin, calendar_id: str) -> str:
    try:
        res = (
            admin.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("owner_user_id")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return str(res.data[0].get("owner_user_id") or "")
    except Exception:
        pass
    return ""


def _calendar_name_by_id(admin, calendar_id: str) -> str:
    try:
        res = (
            admin.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("name")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return str(res.data[0].get("name") or "")
    except Exception:
        pass
    return ""


def _owner_display_name(admin, owner_user_id: str) -> str:
    if not owner_user_id:
        return "Alguém"
    try:
        from ego_api import db

        prof = db.load_profile(admin, owner_user_id) or {}
        name = str(prof.get("full_name") or "").strip()
        if name:
            return name
    except Exception:
        pass
    return "Alguém"


def _member_link_patch_for_calendar(
    admin,
    calendar_id: str,
    user_id: str,
    *,
    phone_norm: str | None = None,
) -> dict[str, Any]:
    """Entre Nós fica pendente até aceitar; outras agendas activam ao entrar."""
    patch: dict[str, Any] = {"user_id": user_id}
    if phone_norm:
        patch["invited_phone"] = phone_norm
    cal_name = _calendar_name_by_id(admin, calendar_id)
    if is_entre_nos_calendar(cal_name):
        patch["status"] = "pending"
    else:
        patch["status"] = "active"
    return patch


def _user_contact_keys(
    supabase: Client | None, user_id: str
) -> tuple[str, str, list[str]]:
    """E-mail normalizado, telefone E.164 e placeholders de convite."""
    from ego_api import db
    from ego_api.request_ctx import get_session

    email_norm = ""
    phone_norm = ""
    placeholders: list[str] = []
    try:
        sess = get_session()
        em = (sess.email if sess else "") or ""
        if not em:
            prof = db.load_profile(supabase, user_id) or {}
            em = str(prof.get("email") or "")
        email_norm, _ = _normalize_invite_email(em)
        prof = db.load_profile(supabase, user_id) or {}
        ph = str(prof.get("phone") or "").strip()
        if ph:
            phone_norm, _ = normalize_phone_br(ph)
            if phone_norm:
                placeholders.append(phone_invite_email_placeholder(phone_norm))
    except Exception:
        pass
    return email_norm, phone_norm, placeholders


def _user_is_active_member(admin, user_id: str, calendar_id: str) -> bool:
    try:
        res = (
            admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
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


def link_shared_memberships_for_user_phone(
    supabase: Client | None, user_id: str, phone: str
) -> int:
    phone_norm, err = normalize_phone_br(phone)
    if err or not phone_norm or not user_id:
        return 0
    admin = create_service_client()
    if not admin:
        return 0
    updated = 0
    try:
        placeholder = phone_invite_email_placeholder(phone_norm)
        for field, value in (
            ("invited_phone", phone_norm),
            ("invited_email", placeholder),
        ):
            res = (
                admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
                .select("id,calendar_id,user_id,status")
                .eq(field, value)
                .execute()
            )
            for row in res.data or []:
                rid = str(row.get("id") or "")
                if not rid:
                    continue
                current = str(row.get("user_id") or "")
                status = str(row.get("status") or "")
                cid = str(row.get("calendar_id") or "")
                if current == user_id and status in ("active", "pending"):
                    continue
                patch = _member_link_patch_for_calendar(
                    admin, cid, user_id, phone_norm=phone_norm
                )
                admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).update(
                    patch
                ).eq("id", rid).execute()
                updated += 1
                owner = _calendar_owner_id(admin, cid) if cid else ""
                if patch.get("status") == "active" and cid and owner:
                    push_after_member_invited(
                        cid,
                        owner,
                        {"user_id": user_id, "status": "active"},
                    )
    except Exception as exc:
        print(
            f"[EGO] link_shared_memberships_for_user_phone error user={user_id}: {exc}",
            flush=True,
        )
    return updated


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
        if res.data:
            return True
        cal = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("owner_user_id")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        if cal.data and str(cal.data[0].get("owner_user_id") or "") == user_id:
            _ensure_owner_membership_row(supabase, user_id, calendar_id)
            return True
    except Exception:
        pass
    return False


def _ensure_owner_membership_row(
    supabase: Client | None, user_id: str, calendar_id: str
) -> None:
    """Repara agendas antigas em que o criador não ficou em shared_calendar_members."""
    if not supabase or not user_id or not calendar_id:
        return
    apply_user_auth(supabase)
    try:
        existing = (
            supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("id")
            .eq("calendar_id", calendar_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            return
    except Exception:
        pass

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
        "calendar_id": calendar_id,
        "user_id": user_id,
        "invited_email": sess_email or f"{user_id}@ego.local",
        "role": "owner",
        "status": "active",
    }
    from ego_api.supabase_client import insert_with_admin_fallback

    try:
        insert_with_admin_fallback(
            supabase,
            SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE,
            owner_row,
            raise_errors=False,
        )
    except Exception:
        pass


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
            .select("id,calendar_id,user_id,status")
            .eq("invited_email", email_norm)
            .execute()
        )
        updated = 0
        for row in res.data or []:
            rid = str(row.get("id") or "")
            if not rid:
                continue
            current = str(row.get("user_id") or "")
            status = str(row.get("status") or "")
            cid = str(row.get("calendar_id") or "")
            if current == user_id and status in ("active", "pending"):
                continue
            patch = _member_link_patch_for_calendar(admin, cid, user_id)
            admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).update(patch).eq(
                "id", rid
            ).execute()
            updated += 1
            owner = _calendar_owner_id(admin, cid) if cid else ""
            if patch.get("status") == "active" and cid and owner:
                push_after_member_invited(
                    cid,
                    owner,
                    {"user_id": user_id, "status": "active"},
                )
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
        prof = db.load_profile(supabase, user_id) or {}
        ph = str(prof.get("phone") or "").strip()
        if ph:
            link_shared_memberships_for_user_phone(supabase, user_id, ph)
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


def list_pending_invites_for_user(
    supabase: Client | None, user_id: str
) -> list[dict]:
    """Convites de grupo ainda não aceites (Entre Nós / Família)."""
    if not user_id:
        return []
    admin = create_service_client()
    if not admin:
        return []
    email_norm, phone_norm, placeholders = _user_contact_keys(supabase, user_id)
    seen: set[str] = set()
    rows: list[dict] = []

    def _collect(res) -> None:  # noqa: ANN001
        for row in res.data or []:
            rid = str(row.get("id") or "")
            if not rid or rid in seen:
                continue
            cid = str(row.get("calendar_id") or "")
            if not cid or _user_is_active_member(admin, user_id, cid):
                continue
            seen.add(rid)
            rows.append(row)

    try:
        if email_norm:
            _collect(
                admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
                .select("*")
                .eq("status", "pending")
                .eq("invited_email", email_norm)
                .execute()
            )
        if phone_norm:
            _collect(
                admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
                .select("*")
                .eq("status", "pending")
                .eq("invited_phone", phone_norm)
                .execute()
            )
        for placeholder in placeholders:
            _collect(
                admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
                .select("*")
                .eq("status", "pending")
                .eq("invited_email", placeholder)
                .execute()
            )
        _collect(
            admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("*")
            .eq("status", "pending")
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        print(
            f"[EGO] list_pending_invites_for_user error user={user_id}: {exc}",
            flush=True,
        )
        return []

    out: list[dict] = []
    for row in rows:
        cid = str(row.get("calendar_id") or "")
        cal_name = _calendar_name_by_id(admin, cid)
        owner_id = _calendar_owner_id(admin, cid)
        invited_phone = str(row.get("invited_phone") or "")
        invited_email = str(row.get("invited_email") or "")
        out.append(
            {
                "member_id": str(row.get("id") or ""),
                "calendar_id": cid,
                "calendar_name": cal_name,
                "owner_name": _owner_display_name(admin, owner_id),
                "invited_email": invited_email,
                "invited_phone": invited_phone,
                "invited_phone_display": format_phone_display(invited_phone)
                if invited_phone
                else "",
                "is_entre_nos": is_entre_nos_calendar(cal_name),
                "role": str(row.get("role") or "member"),
            }
        )
    return out


def _member_invite_matches_user(
    row: dict,
    user_id: str,
    email_norm: str,
    phone_norm: str,
    placeholders: list[str],
) -> bool:
    if str(row.get("user_id") or "") == user_id:
        return True
    invited_email = str(row.get("invited_email") or "").strip().lower()
    invited_phone = str(row.get("invited_phone") or "").strip()
    if email_norm and invited_email == email_norm:
        return True
    if phone_norm and invited_phone == phone_norm:
        return True
    if invited_email and invited_email in placeholders:
        return True
    return False


def respond_member_invite(
    supabase: Client | None,
    user_id: str,
    member_id: str,
    *,
    accept: bool,
) -> tuple[bool, str, dict | None]:
    """Aceitar ou recusar convite para entrar numa agenda partilhada."""
    if not user_id or not member_id:
        return False, "Pedido inválido.", None
    admin = create_service_client()
    if not admin:
        return False, "Servidor indisponível.", None
    email_norm, phone_norm, placeholders = _user_contact_keys(supabase, user_id)
    try:
        res = (
            admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("*")
            .eq("id", member_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return False, "Convite não encontrado.", None
        row = res.data[0]
        if str(row.get("status") or "") != "pending":
            return False, "Este convite já foi respondido.", None
        if not _member_invite_matches_user(
            row, user_id, email_norm, phone_norm, placeholders
        ):
            return False, "Este convite não é para a sua conta.", None
        cid = str(row.get("calendar_id") or "")
        if accept:
            if _user_is_active_member(admin, user_id, cid):
                return False, "Você já faz parte desta agenda.", None
            patch = {"user_id": user_id, "status": "active"}
            if phone_norm and not str(row.get("invited_phone") or "").strip():
                patch["invited_phone"] = phone_norm
            admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).update(patch).eq(
                "id", member_id
            ).execute()
            refreshed = (
                admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
                .select("*")
                .eq("id", member_id)
                .limit(1)
                .execute()
            )
            data = (refreshed.data or [row])[0]
            owner = _calendar_owner_id(admin, cid)
            if cid and owner:
                push_after_member_invited(
                    cid, owner, {"user_id": user_id, "status": "active"}
                )
            return True, "", data
        admin.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).delete().eq(
            "id", member_id
        ).execute()
        return True, "", None
    except Exception as exc:
        return False, str(exc), None


def count_owned_calendars(supabase: Client | None, owner_user_id: str) -> int:
    """Agendas de grupo que o utilizador criou (limite de criação)."""
    if not supabase or not owner_user_id:
        return 0
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("id")
            .eq("owner_user_id", owner_user_id)
            .execute()
        )
        return len(res.data or [])
    except Exception:
        return 0


def find_calendar_id_by_name(
    supabase: Client | None, user_id: str, calendar_name: str
) -> str | None:
    """Procura agenda do utilizador por nome (sem acento/caixa; ou única agenda)."""
    needle_key = calendar_name_key(calendar_name)
    if not supabase or not user_id:
        return None
    try:
        rows = list_calendars_for_user(supabase, user_id)
    except Exception:
        return None
    if not rows:
        return None
    if not needle_key and len(rows) == 1:
        return str(rows[0].get("id") or "") or None
    if not needle_key:
        return None
    exact: str | None = None
    partial: list[str] = []
    for row in rows:
        cid = str(row.get("id") or "")
        row_key = calendar_name_key(str(row.get("name") or ""))
        if not cid or not row_key:
            continue
        if row_key == needle_key:
            exact = cid
            break
        if needle_key in row_key or row_key in needle_key:
            partial.append(cid)
    if exact:
        return exact
    if len(partial) == 1:
        return partial[0]
    # Não usar a única agenda existente se o nome pedido não coincide
    # (ex. «360 nas alturas» com só «Família» criada → deve criar agenda nova).
    return None


def resolve_calendar_for_user(
    supabase: Client | None,
    user_id: str,
    *,
    calendar_id: str = "",
    calendar_name: str = "",
) -> tuple[str, str]:
    """Devolve (id, nome canónico na base) para marcar/convidar."""
    cid = (calendar_id or "").strip()
    name = (calendar_name or "").strip()
    if not supabase or not user_id:
        return "", name
    try:
        rows = list_calendars_for_user(supabase, user_id)
    except Exception:
        rows = []
    if cid:
        for row in rows:
            if str(row.get("id") or "") == cid:
                return cid, str(row.get("name") or name).strip()
        return cid, name
    found = find_calendar_id_by_name(supabase, user_id, name)
    if found:
        for row in rows:
            if str(row.get("id") or "") == found:
                return found, str(row.get("name") or name).strip()
    # Só usa a única agenda existente quando o pedido não nomeia outra (evita
    # «cria agenda 360» virar reutilizar «Família»).
    if not name.strip() and len(rows) == 1:
        only = rows[0]
        return str(only.get("id") or ""), str(only.get("name") or "").strip()
    return "", name


def _pretty_name_from_email(email: str) -> str:
    """Sem perfil ainda: evita mostrar e-mail cru (usa parte local legível)."""
    em = (email or "").strip().lower()
    if not em:
        return "Membro"
    local = em.split("@", 1)[0] if "@" in em else em
    parts = [p for p in re.sub(r"[._+\-]+", " ", local).split() if p]
    if not parts:
        return "Convidado"
    return " ".join(p[:1].upper() + p[1:].lower() for p in parts)[:80]


def _is_email_like(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(t) and ("@" in t or t.endswith(".com") or t.endswith(".br"))


def _clean_person_name(name: str, email_norm: str) -> str:
    """Descarta valores que são só e-mail ou alias do e-mail."""
    n = (name or "").strip()
    if not n or _is_email_like(n):
        return ""
    em = (email_norm or "").strip().lower()
    local = em.split("@", 1)[0] if "@" in em else ""
    if n.lower() in (em, local):
        return ""
    return n[:120]


def _profile_full_name(admin: Client | None, user_id: str) -> str:
    if not admin or not user_id:
        return ""
    try:
        res = (
            admin.table("profiles")
            .select("full_name,name")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if rows:
            return str(rows[0].get("full_name") or rows[0].get("name") or "").strip()
    except Exception:
        pass
    return ""


def _profile_full_name_by_email(admin: Client | None, email_norm: str) -> str:
    if not admin or not email_norm:
        return ""
    try:
        res = (
            admin.table("profiles")
            .select("full_name,name,email")
            .eq("email", email_norm)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            res = (
                admin.table("profiles")
                .select("full_name,name,email")
                .ilike("email", email_norm)
                .limit(5)
                .execute()
            )
            rows = [
                r
                for r in (res.data or [])
                if str(r.get("email") or "").strip().lower() == email_norm
            ]
        if rows:
            return str(rows[0].get("full_name") or rows[0].get("name") or "").strip()
    except Exception:
        pass
    return ""


def _member_display_name(
    admin: Client | None,
    user_id: str | None,
    email: str,
    invited_phone: str | None = None,
) -> str:
    """Nome amigável (profiles.full_name = «como quer ser chamado»). Nunca e-mail cru."""
    phone_norm = (invited_phone or "").strip()
    email_norm, _err = _normalize_invite_email(email)
    if _err:
        email_norm = (email or "").strip().lower()

    uid = (user_id or "").strip()
    if not uid:
        try:
            uid = resolve_user_id_by_email(email_norm or email) or ""
        except Exception:
            uid = ""

    for candidate in (
        _profile_full_name(admin, uid) if uid else "",
        _profile_full_name_by_email(admin, email_norm),
    ):
        name = _clean_person_name(candidate, email_norm)
        if name:
            return name

    if phone_norm:
        return format_phone_display(phone_norm)

    from ego_api.phone_utils import is_phone_invite_email

    if is_phone_invite_email(email_norm):
        digits = email_norm.split("@")[0].replace("phone", "")
        if digits:
            return format_phone_display("+" + digits)
        return "Convidado"

    return _pretty_name_from_email(email_norm or email)


def list_members(
    supabase: Client | None, user_id: str, calendar_id: str
) -> list[dict]:
    if not supabase or not calendar_id or not _user_is_member(supabase, user_id, calendar_id):
        return []
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select(
                "id,calendar_id,user_id,invited_email,invited_phone,role,status,created_at"
            )
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
                str(row.get("invited_phone") or "") or None,
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
        return [_normalize_event_row(r) for r in (res.data or [])]
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
    from ego_api.schedule_tz import local_now_from_session

    ref = local_now_from_session()
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
        return [_normalize_event_row(r) for r in (res.data or [])]
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

    if is_entre_nos_calendar(title):
        owned_en = count_owned_entre_nos_calendars(supabase, user_id)
        if owned_en >= ENTRE_NOS_MAX_CALENDARS_PER_OWNER:
            return (
                False,
                f"Você já tem {owned_en} agendas Entre Nós (limite "
                f"{ENTRE_NOS_MAX_CALENDARS_PER_OWNER}). Apague uma para criar outra.",
                None,
            )
    else:
        cap = max(1, MAX_SHARED_CALENDARS_PER_OWNER)
        owned = count_owned_calendars(supabase, user_id)
        if owned >= cap:
            return (
                False,
                f"Você já tem {owned} agendas compartilhadas (limite {cap} listas). "
                "Apague uma no app ou convide/marque numa agenda existente.",
                None,
            )

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


ENTRE_NOS_MAX_MEMBERS = 2
ENTRE_NOS_MAX_CALENDARS_PER_OWNER = 10


def normalize_entre_nos_group_name(raw: str) -> str:
    """Nome escolhido pelo utilizador → formato Entre Nós (ex.: Maria → Entre Nós · Maria)."""
    t = (raw or "").strip()[:120]
    if not t:
        return "Entre Nós"
    if is_entre_nos_calendar(t):
        return t
    prefix = "Entre Nós · "
    rest = t[: max(0, 120 - len(prefix))]
    return f"{prefix}{rest}" if rest else "Entre Nós"


def count_owned_entre_nos_calendars(
    supabase: Client | None, owner_user_id: str
) -> int:
    if not supabase or not owner_user_id:
        return 0
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("id,name")
            .eq("owner_user_id", owner_user_id)
            .execute()
        )
        return sum(
            1
            for r in (res.data or [])
            if is_entre_nos_calendar(str(r.get("name") or ""))
        )
    except Exception:
        return 0


def _calendar_name(supabase: Client | None, calendar_id: str) -> str:
    if not supabase or not calendar_id:
        return ""
    try:
        apply_user_auth(supabase)
        cal = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("name")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        if cal.data:
            return str(cal.data[0].get("name") or "")
    except Exception:
        pass
    return ""


def calendar_member_cap_for(supabase: Client | None, calendar_id: str) -> int:
    """Entre Nós = criador + 1 parceiro; outras agendas usam limite global."""
    if is_entre_nos_calendar(_calendar_name(supabase, calendar_id)):
        return ENTRE_NOS_MAX_MEMBERS
    return calendar_member_cap()


def calendar_member_cap() -> int:
    """Pessoas por agenda (membros ativos + convites pendentes)."""
    return max(1, MAX_MEMBERS_PER_SHARED_CALENDAR)


def count_calendar_members(supabase: Client | None, calendar_id: str) -> int:
    if not supabase or not calendar_id:
        return 0
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("id")
            .eq("calendar_id", calendar_id)
            .execute()
        )
        return len(res.data or [])
    except Exception:
        return 0


def _ensure_calendar_member_capacity(
    supabase: Client | None, calendar_id: str
) -> tuple[bool, str]:
    cap = calendar_member_cap_for(supabase, calendar_id)
    used = count_calendar_members(supabase, calendar_id)
    if used >= cap:
        if cap == ENTRE_NOS_MAX_MEMBERS:
            return (
                False,
                "Nesta agenda já há um parceiro (Entre Nós = vocês dois). "
                "Para outra pessoa, crie uma nova agenda Entre Nós.",
            )
        return (
            False,
            f"Esta agenda já tem {used} pessoas (limite {cap} por lista).",
        )
    return True, ""


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


def _add_pending_member_by_email(
    supabase: Client | None,
    owner_user_id: str,
    calendar_id: str,
    email_norm: str,
) -> tuple[bool, str, dict | None]:
    """Convite por e-mail sem conta ainda — liga ao login (link_shared_memberships)."""
    apply_user_auth(supabase)
    try:
        existing = (
            supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("id,user_id,status")
            .eq("calendar_id", calendar_id)
            .eq("invited_email", email_norm)
            .limit(1)
            .execute()
        )
        if existing.data:
            prev = existing.data[0]
            if str(prev.get("role") or "") == "owner":
                return (
                    False,
                    "Esse e-mail é o seu (conta com que você entrou). "
                    "Use o e-mail de outra pessoa para convidar.",
                    None,
                )
            member_id = str(prev.get("id") or "")
            if member_id:
                admin = create_service_client()
                client = admin or supabase
                client.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).update(
                    {
                        "invited_email": email_norm,
                        "status": "pending",
                        "role": "member",
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
                return True, _pending_invite_message(supabase, calendar_id), data
            return False, "Este e-mail já está nesta agenda.", None
        ok_cap, cap_err = _ensure_calendar_member_capacity(supabase, calendar_id)
        if not ok_cap:
            return False, cap_err, None
        row = {
            "calendar_id": calendar_id,
            "user_id": None,
            "invited_email": email_norm,
            "role": "member",
            "status": "pending",
        }
        from ego_api.supabase_client import insert_with_admin_fallback

        inserted = insert_with_admin_fallback(
            supabase, SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE, row, raise_errors=True
        )
        data = inserted[0] if inserted else row
        return True, _pending_invite_message(supabase, calendar_id), data
    except Exception as exc:
        low = str(exc).lower()
        if "unique" in low or "duplicate" in low:
            return False, "Este e-mail já está nesta agenda.", None
        return False, str(exc), None


def add_member_by_email(
    supabase: Client | None,
    actor_user_id: str,
    calendar_id: str,
    email: str,
) -> tuple[bool, str, dict | None]:
    """Qualquer membro ativo pode convidar; limite de lugares aplica-se ao dono da agenda."""
    if not supabase or not actor_user_id or not calendar_id:
        return False, "Sessão indisponível.", None
    email_norm, err = _normalize_invite_email(email)
    if err:
        return False, err, None
    if not _user_is_member(supabase, actor_user_id, calendar_id):
        return False, "Sem acesso a esta agenda.", None
    calendar_owner_id = ""
    try:
        cal = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("owner_user_id")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        rows = cal.data or []
        if not rows:
            return False, "Agenda não encontrada.", None
        calendar_owner_id = str(rows[0].get("owner_user_id") or "")
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
        return _add_pending_member_by_email(
            supabase, actor_user_id, calendar_id, email_norm
        )
    if target_uid == actor_user_id:
        return False, "Você já faz parte desta agenda.", None

    apply_user_auth(supabase)
    seat_owner = calendar_owner_id or actor_user_id
    seat_limit = team_seat_limit_for_owner(supabase, seat_owner)
    if seat_limit is not None:
        used = count_owner_team_member_slots(supabase, seat_owner)
        already = False
        try:
            cals = (
                supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
                .select("id")
                .eq("owner_user_id", seat_owner)
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
            if str(prev.get("role") or "") == "owner":
                return (
                    False,
                    "Esse e-mail é o seu (conta com que você entrou). "
                    "Use o e-mail de outra pessoa para convidar.",
                    None,
                )
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
                            "status": "pending",
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
                    return True, _pending_invite_message(supabase, calendar_id), data
                except Exception as exc:
                    return False, str(exc), None
            return False, "Este e-mail já está nesta agenda.", None
        ok_cap, cap_err = _ensure_calendar_member_capacity(supabase, calendar_id)
        if not ok_cap:
            return False, cap_err, None
        row = {
            "calendar_id": calendar_id,
            "user_id": target_uid,
            "invited_email": email_norm,
            "role": "member",
            "status": "pending",
        }
        from ego_api.supabase_client import insert_with_admin_fallback

        inserted = insert_with_admin_fallback(
            supabase, SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE, row, raise_errors=True
        )
        data = inserted[0] if inserted else row
        return True, _pending_invite_message(supabase, calendar_id), data
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


def _add_pending_member_by_phone(
    supabase: Client | None,
    owner_user_id: str,
    calendar_id: str,
    phone_norm: str,
) -> tuple[bool, str, dict | None]:
    apply_user_auth(supabase)
    placeholder = phone_invite_email_placeholder(phone_norm)
    try:
        existing = (
            supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
            .select("id,user_id,status")
            .eq("calendar_id", calendar_id)
            .eq("invited_phone", phone_norm)
            .limit(1)
            .execute()
        )
        if not existing.data:
            existing = (
                supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
                .select("id,user_id,status")
                .eq("calendar_id", calendar_id)
                .eq("invited_email", placeholder)
                .limit(1)
                .execute()
            )
        if existing.data:
            prev = existing.data[0]
            member_id = str(prev.get("id") or "")
            if member_id:
                admin = create_service_client()
                client = admin or supabase
                client.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).update(
                    {
                        "invited_phone": phone_norm,
                        "invited_email": placeholder,
                        "status": "pending",
                        "role": "member",
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
                return True, _pending_invite_message(supabase, calendar_id), data
            return False, "Este telefone já está nesta agenda.", None
        ok_cap, cap_err = _ensure_calendar_member_capacity(supabase, calendar_id)
        if not ok_cap:
            return False, cap_err, None
        row = {
            "calendar_id": calendar_id,
            "user_id": None,
            "invited_email": placeholder,
            "invited_phone": phone_norm,
            "role": "member",
            "status": "pending",
        }
        from ego_api.supabase_client import insert_with_admin_fallback

        inserted = insert_with_admin_fallback(
            supabase, SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE, row, raise_errors=True
        )
        data = inserted[0] if inserted else row
        return True, _pending_invite_message(supabase, calendar_id), data
    except Exception as exc:
        low = str(exc).lower()
        if "unique" in low or "duplicate" in low:
            return False, "Este telefone já está nesta agenda.", None
        return False, str(exc), None


def add_member_by_phone(
    supabase: Client | None,
    actor_user_id: str,
    calendar_id: str,
    phone: str,
) -> tuple[bool, str, dict | None]:
    if not supabase or not actor_user_id or not calendar_id:
        return False, "Sessão indisponível.", None
    phone_norm, err = normalize_phone_br(phone)
    if err:
        return False, err, None
    if not _user_is_member(supabase, actor_user_id, calendar_id):
        return False, "Sem acesso a esta agenda.", None

    target_uid = resolve_user_id_by_phone(phone_norm)
    if not target_uid:
        if not create_service_client():
            return (
                False,
                "Convites indisponíveis no servidor. Confirme SUPABASE_SERVICE_ROLE_KEY.",
                None,
            )
        return _add_pending_member_by_phone(
            supabase, actor_user_id, calendar_id, phone_norm
        )

    placeholder = phone_invite_email_placeholder(phone_norm)
    apply_user_auth(supabase)
    try:
        existing = None
        for field, value in (
            ("invited_phone", phone_norm),
            ("invited_email", placeholder),
        ):
            res = (
                supabase.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE)
                .select("id,user_id")
                .eq("calendar_id", calendar_id)
                .eq(field, value)
                .limit(1)
                .execute()
            )
            if res.data:
                existing = res
                break
        if existing and existing.data:
            prev = existing.data[0]
            if str(prev.get("user_id") or "") == target_uid:
                return False, "Este telefone já está nesta agenda.", None
            member_id = str(prev.get("id") or "")
            if member_id:
                admin = create_service_client()
                client = admin or supabase
                client.table(SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE).update(
                    {
                        "user_id": target_uid,
                        "invited_phone": phone_norm,
                        "invited_email": placeholder,
                        "status": "pending",
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
                return True, _pending_invite_message(supabase, calendar_id), data
        ok_cap, cap_err = _ensure_calendar_member_capacity(supabase, calendar_id)
        if not ok_cap:
            return False, cap_err, None
        row = {
            "calendar_id": calendar_id,
            "user_id": target_uid,
            "invited_email": placeholder,
            "invited_phone": phone_norm,
            "role": "member",
            "status": "pending",
        }
        from ego_api.supabase_client import insert_with_admin_fallback

        inserted = insert_with_admin_fallback(
            supabase, SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE, row, raise_errors=True
        )
        data = inserted[0] if inserted else row
        return True, _pending_invite_message(supabase, calendar_id), data
    except Exception as exc:
        low = str(exc).lower()
        if "unique" in low or "duplicate" in low:
            return False, "Este telefone já está nesta agenda.", None
        return False, str(exc), None


def add_member_by_contact(
    supabase: Client | None,
    actor_user_id: str,
    calendar_id: str,
    contact: str,
) -> tuple[bool, str, dict | None]:
    raw = (contact or "").strip()
    if not raw:
        return False, "Informe e-mail ou telefone.", None
    if "@" in raw:
        ok, err, row = add_member_by_email(supabase, actor_user_id, calendar_id, raw)
    else:
        ok, err, row = add_member_by_phone(supabase, actor_user_id, calendar_id, raw)
    if ok and row:
        push_after_member_invited(calendar_id, actor_user_id, row)
    return ok, err, row


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
    partner_invite: bool | None = None,
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
    cal_name = ""
    try:
        cal_row = (
            supabase.table(SUPABASE_SHARED_CALENDARS_TABLE)
            .select("name")
            .eq("id", calendar_id)
            .limit(1)
            .execute()
        )
        if cal_row.data:
            cal_name = str(cal_row.data[0].get("name") or "")
    except Exception:
        pass
    if partner_invite is None:
        partner_invite = is_entre_nos_calendar(cal_name)
    row = {
        "calendar_id": calendar_id,
        "created_by_user_id": user_id,
        "title": (title or "Reunião")[:500],
        "scheduled_at": norm.isoformat(),
        "announce": (announce or title or "")[:2000],
        "invite_status": "pending" if partner_invite else "none",
    }
    try:
        from ego_api.supabase_client import insert_with_admin_fallback

        inserted = insert_with_admin_fallback(
            supabase, SUPABASE_SHARED_CALENDAR_EVENTS_TABLE, row, raise_errors=True
        )
        event = inserted[0] if inserted else row
        if isinstance(event, dict):
            event = _normalize_event_row(event)
        try:
            from ego_api.shared_calendar_notify import (
                calendar_name_by_id,
                notify_members_new_event,
            )

            admin = create_service_client()
            if not cal_name and admin:
                cal_name = calendar_name_by_id(admin, calendar_id) or ""
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
                calendar_name=cal_name or "Entre Nós",
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


def respond_to_event(
    supabase: Client | None,
    user_id: str,
    calendar_id: str,
    event_id: str,
    *,
    accept: bool,
) -> tuple[bool, str, dict | None]:
    """Parceiro confirma ou recusa convite Entre Nós (manual)."""
    if not supabase or not user_id:
        return False, "Sessão indisponível.", None
    if not _user_is_member(supabase, user_id, calendar_id):
        return False, "Sem acesso a esta agenda.", None
    if not apply_user_auth(supabase):
        return False, "Sessão expirada.", None
    try:
        res = (
            supabase.table(SUPABASE_SHARED_CALENDAR_EVENTS_TABLE)
            .select("*")
            .eq("id", event_id)
            .eq("calendar_id", calendar_id)
            .eq("dismissed", False)
            .limit(1)
            .execute()
        )
        if not res.data:
            return False, "Compromisso não encontrado.", None
        ev = res.data[0]
        if str(ev.get("created_by_user_id") or "") == user_id:
            return False, "Quem enviou o convite já vê aqui — a outra pessoa é quem confirma.", None
        status = str(ev.get("invite_status") or "none")
        if status != "pending":
            return False, "Este convite já foi respondido.", None
        patch = {
            "invite_status": "confirmed" if accept else "declined",
            "responded_by_user_id": user_id,
            "responded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        upd = (
            supabase.table(SUPABASE_SHARED_CALENDAR_EVENTS_TABLE)
            .update(patch)
            .eq("id", event_id)
            .eq("calendar_id", calendar_id)
            .execute()
        )
        rows = list(upd.data or [])
        if not rows:
            admin = create_service_client()
            if admin:
                upd2 = (
                    admin.table(SUPABASE_SHARED_CALENDAR_EVENTS_TABLE)
                    .update(patch)
                    .eq("id", event_id)
                    .eq("calendar_id", calendar_id)
                    .execute()
                )
                rows = list(upd2.data or [])
        row = rows[0] if rows else {**ev, **patch}
        try:
            from ego_api.shared_calendar_notify import notify_invite_response

            notify_invite_response(
                calendar_id,
                creator_user_id=str(ev.get("created_by_user_id") or ""),
                responder_user_id=user_id,
                event_title=str(ev.get("title") or "Compromisso"),
                accepted=accept,
            )
        except Exception:
            pass
        return True, "", _normalize_event_row(row if isinstance(row, dict) else ev)
    except Exception as exc:
        return False, str(exc), None


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
        admin = create_service_client()
        clients: list = []
        if admin:
            clients.append(admin)
        if supabase and supabase not in clients:
            clients.append(supabase)
        last_err = ""
        for client in clients:
            try:
                client.table(SUPABASE_SHARED_CALENDARS_TABLE).delete().eq(
                    "id", calendar_id
                ).execute()
                check = client.table(SUPABASE_SHARED_CALENDARS_TABLE).select(
                    "id"
                ).eq("id", calendar_id).limit(1).execute()
                if not (check.data or []):
                    return True, ""
                last_err = "A agenda ainda aparece na base após apagar."
            except Exception as exc:
                last_err = str(exc)
        return False, last_err or "Não foi possível apagar a agenda."
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
