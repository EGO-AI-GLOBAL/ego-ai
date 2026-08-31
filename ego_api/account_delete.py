"""Exclusão de conta (Guideline Apple 5.1.1 — apagar dentro do app)."""

from __future__ import annotations

import logging

_LOG = logging.getLogger(__name__)

MSG_DELETE_OK = "Conta excluída com sucesso."
MSG_DELETE_FAIL = (
    "Não foi possível excluir a conta. Tente de novo ou escreva para contato@egoai.com.br."
)


def delete_user_account(user_id: str) -> tuple[bool, str | None]:
    """Remove auth.users — grava identidade free (trial_used) antes do cascade."""
    uid = (user_id or "").strip()
    if not uid:
        return False, "Utilizador inválido."
    from ego_api import db
    from ego_api.free_identity_guard import record_identities_on_account_delete
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    if not admin:
        return False, "Servidor indisponível. Tente mais tarde."

    prof = db.load_profile(admin, uid) or {}
    try:
        record_identities_on_account_delete(uid, prof)
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("free_identity_guard pre-delete user=%s: %s", uid[:8], exc)

    try:
        admin.auth.admin.delete_user(uid)
        _LOG.info("account_delete ok user=%s", uid[:8])
        return True, None
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("account_delete failed user=%s: %s", uid[:8], exc)
        low = str(exc).lower()
        if "not found" in low or "user not found" in low:
            return True, None
        return False, MSG_DELETE_FAIL
