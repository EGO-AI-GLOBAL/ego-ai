"""Cadastro e recuperação — mensagens claras, sem conta fantasma."""

from __future__ import annotations

import logging
from typing import Any

_LOG = logging.getLogger("ego.auth_signup")

MSG_EMAIL_TAKEN = "Este e-mail já está cadastrado. Use Entrar ou Esqueci a senha."
MSG_NO_ACCOUNT = (
    "Não encontramos conta com este e-mail. "
    "Se o cadastro parou com erro vermelho, use Criar conta — não Entrar."
)
MSG_RESET_SENT = (
    "Enviamos um link de Ego-IA (contato@egoai.com.br) para criar nova senha. "
    "Verifique a caixa de entrada e a pasta de spam."
)
MSG_SIGNUP_PHONE_REQUIRED = "Informe o telefone com DDD."


def mask_email_for_hint(email: str) -> str:
    e = (email or "").strip().lower()
    if "@" not in e:
        return ""
    local, domain = e.split("@", 1)
    if not local or not domain:
        return ""
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def _profile_email_for_user(user_id: str) -> str:
    from ego_api import db
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    if not admin or not user_id:
        return ""
    try:
        res = (
            admin.table(db.SUPABASE_PROFILES_TABLE)
            .select("email")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        return str(row.get("email") or "").strip()
    except Exception:
        return ""


def duplicate_phone_message(phone_norm: str) -> str:
    from ego_api.shared_calendars import resolve_user_id_by_phone

    hint = ""
    uid = resolve_user_id_by_phone(phone_norm)
    if uid:
        masked = mask_email_for_hint(_profile_email_for_user(uid))
        if masked:
            hint = f" Já existe conta com {masked}."
    return (
        "Este telefone já está cadastrado."
        + hint
        + " Use Entrar com esse e-mail ou Esqueci a senha — não crie outra conta."
    )


def auth_account_exists(email_norm: str) -> bool:
    from ego_api.shared_calendars import resolve_user_id_by_email

    return bool(resolve_user_id_by_email(email_norm))


def check_signup_eligibility(email: str, phone: str) -> dict[str, Any]:
    """Valida e-mail/telefone antes de criar conta (app + API)."""
    from ego_api.phone_utils import normalize_phone_br
    from ego_api.services import normalize_email
    from ego_api.shared_calendars import resolve_user_id_by_email, resolve_user_id_by_phone

    email_norm, email_err = normalize_email(email)
    if email_err:
        return {
            "ok": False,
            "reason": "invalid_email",
            "message": email_err,
            "action": "signup",
            "masked_email": "",
        }

    phone_norm, phone_err = normalize_phone_br(phone)
    if phone_err:
        return {
            "ok": False,
            "reason": "invalid_phone",
            "message": phone_err,
            "action": "signup",
            "masked_email": "",
        }
    if not phone_norm:
        return {
            "ok": False,
            "reason": "phone_required",
            "message": MSG_SIGNUP_PHONE_REQUIRED,
            "action": "signup",
            "masked_email": "",
        }

    if resolve_user_id_by_email(email_norm):
        return {
            "ok": False,
            "reason": "email_taken",
            "message": MSG_EMAIL_TAKEN,
            "action": "forgot_password",
            "masked_email": mask_email_for_hint(email_norm),
        }

    phone_uid = resolve_user_id_by_phone(phone_norm)
    if phone_uid:
        owner_email = _profile_email_for_user(phone_uid)
        return {
            "ok": False,
            "reason": "phone_taken",
            "message": duplicate_phone_message(phone_norm),
            "action": "login",
            "masked_email": mask_email_for_hint(owner_email),
        }

    return {
        "ok": True,
        "reason": "",
        "message": "",
        "action": "signup",
        "masked_email": "",
    }


def delete_auth_user(user_id: str) -> None:
    """Remove auth.users órfão após falha no perfil."""
    if not user_id:
        return
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    if not admin:
        return
    try:
        admin.auth.admin.delete_user(user_id)
        _LOG.info("signup cleanup deleted auth user=%s", user_id[:8])
    except Exception as exc:
        _LOG.warning("signup cleanup failed user=%s: %s", user_id[:8], exc)


def signup_failure_message(raw_err: str, phone_norm: str = "") -> str:
    low = (raw_err or "").lower()
    if "profiles_phone_unique" in low or (
        "duplicate key" in low and "phone" in low
    ):
        return duplicate_phone_message(phone_norm)
    if "phone" in low and "cadastrado" in low:
        return duplicate_phone_message(phone_norm)
    return raw_err or "Não foi possível criar o perfil."


def login_failure_message(email_norm: str, default: str) -> str:
    if "incorretos" not in (default or "").lower():
        return default
    if auth_account_exists(email_norm):
        return default
    return MSG_NO_ACCOUNT
