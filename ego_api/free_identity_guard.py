"""Anti-abuso free: apagar + recriar com mesmo e-mail/telefone/OAuth não zera trial_used."""

from __future__ import annotations

import datetime
import logging
from typing import Any

from supabase import Client

_LOG = logging.getLogger("ego.free_identity_guard")

TABLE = "ego_free_identity_guard"
UI_TRIAL_USED_KEY = "trial_used"


def _today_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _table_ready(admin: Client | None) -> bool:
    if not admin:
        return False
    try:
        admin.table(TABLE).select("id").limit(1).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("free_identity_guard table missing: %s", exc)
        return False


def _oauth_keys_from_auth_user(user_obj: Any) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    idents = getattr(user_obj, "identities", None) or []
    for ident in idents:
        if isinstance(ident, dict):
            provider = str(ident.get("provider") or "").strip().lower()
            uid = str(ident.get("id") or ident.get("identity_id") or "").strip()
        else:
            provider = str(getattr(ident, "provider", "") or "").strip().lower()
            uid = str(getattr(ident, "id", "") or "").strip()
        if provider and uid and provider not in ("email", "phone"):
            out.append((provider, uid))
    return out


def _usage_snapshot(prof: dict) -> tuple[str, int, int, int]:
    from ego_api.db import daily_message_counts_from_profile

    hoje = _today_iso()
    usage_date = str(prof.get("daily_usage_date") or hoje).strip()[:10]
    if usage_date != hoje:
        return hoje, 0, 0, 0
    text_used, voice_used = daily_message_counts_from_profile(prof)
    tts_used = int(prof.get("daily_tts_count") or 0)
    return usage_date, text_used, voice_used, tts_used


def _upsert_identity_row(
    admin: Client,
    *,
    kind: str,
    key: str,
    deleted_user_id: str,
    usage_date: str,
    text_used: int,
    voice_used: int,
    tts_used: int,
) -> None:
    key = (key or "").strip()
    if not key:
        return
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        existing = (
            admin.table(TABLE)
            .select("id,delete_count,daily_usage_date,daily_text_used,daily_voice_used,daily_tts_used")
            .eq("identity_kind", kind)
            .eq("identity_key", key)
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        if rows:
            row = rows[0]
            prev_date = str(row.get("daily_usage_date") or "").strip()[:10]
            if prev_date == usage_date:
                text_used = max(text_used, int(row.get("daily_text_used") or 0))
                voice_used = max(voice_used, int(row.get("daily_voice_used") or 0))
                tts_used = max(tts_used, int(row.get("daily_tts_used") or 0))
            admin.table(TABLE).update(
                {
                    "trial_used_at": now,
                    "last_deleted_user_id": deleted_user_id,
                    "daily_usage_date": usage_date,
                    "daily_text_used": text_used,
                    "daily_voice_used": voice_used,
                    "daily_tts_used": tts_used,
                    "delete_count": int(row.get("delete_count") or 0) + 1,
                    "updated_at": now,
                }
            ).eq("id", row["id"]).execute()
        else:
            admin.table(TABLE).insert(
                {
                    "identity_kind": kind,
                    "identity_key": key,
                    "trial_used_at": now,
                    "last_deleted_user_id": deleted_user_id,
                    "daily_usage_date": usage_date,
                    "daily_text_used": text_used,
                    "daily_voice_used": voice_used,
                    "daily_tts_used": tts_used,
                    "delete_count": 1,
                    "updated_at": now,
                }
            ).execute()
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("free_identity_guard upsert %s:%s failed: %s", kind, key[:8], exc)


def record_identities_on_account_delete(user_id: str, prof: dict | None) -> None:
    """Antes de delete_user: grava e-mail/telefone/OAuth + uso diário do dia."""
    uid = (user_id or "").strip()
    if not uid:
        return
    from ego_api.services import normalize_email
    from ego_api.phone_utils import normalize_phone_br
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    if not admin or not _table_ready(admin):
        return

    base = dict(prof or {})
    email_norm, _ = normalize_email(str(base.get("email") or ""))
    phone_norm, _ = normalize_phone_br(str(base.get("phone") or ""))
    usage_date, text_used, voice_used, tts_used = _usage_snapshot(base)

    oauth_keys: list[tuple[str, str]] = []
    try:
        res = admin.auth.admin.get_user_by_id(uid)
        user_obj = getattr(res, "user", None) or res
        oauth_keys = _oauth_keys_from_auth_user(user_obj)
        if not email_norm:
            em = str(getattr(user_obj, "email", "") or "").strip()
            email_norm, _ = normalize_email(em)
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("free_identity_guard auth lookup user=%s: %s", uid[:8], exc)

    if email_norm:
        _upsert_identity_row(
            admin,
            kind="email",
            key=email_norm.lower(),
            deleted_user_id=uid,
            usage_date=usage_date,
            text_used=text_used,
            voice_used=voice_used,
            tts_used=tts_used,
        )
    if phone_norm:
        _upsert_identity_row(
            admin,
            kind="phone",
            key=phone_norm,
            deleted_user_id=uid,
            usage_date=usage_date,
            text_used=text_used,
            voice_used=voice_used,
            tts_used=tts_used,
        )
    for provider, oauth_uid in oauth_keys:
        _upsert_identity_row(
            admin,
            kind="oauth",
            key=f"{provider}:{oauth_uid}",
            deleted_user_id=uid,
            usage_date=usage_date,
            text_used=text_used,
            voice_used=voice_used,
            tts_used=tts_used,
        )
    _LOG.info(
        "free_identity_guard recorded user=%s email=%s phone=%s oauth=%s",
        uid[:8],
        bool(email_norm),
        bool(phone_norm),
        len(oauth_keys),
    )


def _lookup_matches(
    admin: Client, *, email_norm: str = "", phone_norm: str = ""
) -> list[dict]:
    keys: list[tuple[str, str]] = []
    em = (email_norm or "").strip().lower()
    ph = (phone_norm or "").strip()
    if em:
        keys.append(("email", em))
    if ph:
        keys.append(("phone", ph))
    if not keys:
        return []
    out: list[dict] = []
    for kind, key in keys:
        try:
            res = (
                admin.table(TABLE)
                .select("*")
                .eq("identity_kind", kind)
                .eq("identity_key", key)
                .limit(1)
                .execute()
            )
            if res.data:
                out.append(res.data[0])
        except Exception:
            pass
    return out


def identity_already_used_free_tier(
    *, email: str = "", phone: str = ""
) -> bool:
    from ego_api.services import normalize_email
    from ego_api.phone_utils import normalize_phone_br
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    if not admin or not _table_ready(admin):
        return False
    email_norm, _ = normalize_email(email)
    phone_norm, _ = normalize_phone_br(phone)
    return bool(_lookup_matches(admin, email_norm=email_norm, phone_norm=phone_norm or ""))


def apply_guard_to_new_profile(
    supabase: Client | None,
    user_id: str,
    *,
    email: str = "",
    phone: str = "",
) -> bool:
    """
    Após signup: marca trial_used no ui_state e repõe contadores do dia
    se a identidade já existia (anti reset 5 textos + 1 voz).
    """
    if not supabase or not user_id:
        return False
    from ego_api import db
    from ego_api.services import normalize_email
    from ego_api.phone_utils import normalize_phone_br
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    if not admin or not _table_ready(admin):
        return False

    email_norm, _ = normalize_email(email)
    phone_norm, _ = normalize_phone_br(phone)
    matches = _lookup_matches(
        admin, email_norm=email_norm, phone_norm=phone_norm or ""
    )
    if not matches:
        return False

    hoje = _today_iso()
    text_used = voice_used = tts_used = 0
    usage_date = ""
    for row in matches:
        d = str(row.get("daily_usage_date") or "").strip()[:10]
        if d == hoje:
            text_used = max(text_used, int(row.get("daily_text_used") or 0))
            voice_used = max(voice_used, int(row.get("daily_voice_used") or 0))
            tts_used = max(tts_used, int(row.get("daily_tts_used") or 0))
            usage_date = hoje

    prof = db.load_profile(supabase, user_id) or {}
    ui = db._parse_ui_state(prof)  # noqa: SLF001 — uso interno controlado
    ui[UI_TRIAL_USED_KEY] = True
    ui["free_identity_reused_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    patch: dict[str, Any] = {"ui_state": ui}
    if usage_date == hoje and (text_used or voice_used or tts_used):
        ui["daily_messages"] = {
            "date": hoje,
            "text": text_used,
            "voice": voice_used,
        }
        patch["ui_state"] = ui
        patch["daily_usage_date"] = hoje
        patch["daily_tts_count"] = tts_used

    try:
        supabase.table(db.SUPABASE_PROFILES_TABLE).update(patch).eq("id", user_id).execute()
        _LOG.info(
            "free_identity_guard applied user=%s trial_used text=%s voice=%s",
            user_id[:8],
            text_used,
            voice_used,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("free_identity_guard apply user=%s: %s", user_id[:8], exc)
        return False


def profile_has_trial_used(prof: dict | None) -> bool:
    if not prof:
        return False
    from ego_api.db import _parse_ui_state

    ui = _parse_ui_state(prof)
    return bool(ui.get(UI_TRIAL_USED_KEY))
