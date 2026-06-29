"""Resolve e backfill telefone do perfil (evita loop «Complete seu cadastro» no app)."""

from __future__ import annotations

from typing import Any

from supabase import Client

from ego_api import db
from ego_api.phone_utils import normalize_phone_br


def _phone_from_metadata(meta: Any) -> str:
    if not isinstance(meta, dict):
        return ""
    for key in ("phone", "profile_phone", "whatsapp", "mobile"):
        raw = str(meta.get(key) or "").strip()
        if not raw:
            continue
        norm, err = normalize_phone_br(raw)
        if not err and norm:
            return norm
    return ""


def resolve_profile_phone(
    supabase: Client | None, user_id: str, prof: dict | None
) -> str:
    """
    Telefone do perfil — com backfill a partir de auth.users metadata
    quando profiles.phone está vazio (cadastro antigo ou sync falhou).
    """
    base = prof if isinstance(prof, dict) else {}
    ph = str(base.get("phone") or "").strip()
    if ph:
        return ph

    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    if not admin or not user_id:
        return ""

    try:
        res = admin.auth.admin.get_user_by_id(user_id)
        user = getattr(res, "user", None) or res
        meta = getattr(user, "user_metadata", None) or getattr(
            user, "raw_user_meta_data", None
        )
        found = _phone_from_metadata(meta)
        if found:
            db.upsert_profile_phone(admin, user_id, found)
            return found
    except Exception:
        pass

    return ""
