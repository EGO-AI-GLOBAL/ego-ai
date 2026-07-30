"""Academias parceiras (gym) — separado de referral_partners (influencers)."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

GYM_PARTNERS_TABLE = "gym_partners"
PARTNER_APPLICATIONS_TABLE = "partner_applications"
_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,31}$")
DEFAULT_COMMISSION_PCT = 30


def normalize_partner_code(raw: str) -> str:
    return (raw or "").strip().upper().replace(" ", "")


def is_valid_partner_code(code: str) -> bool:
    return bool(code and _CODE_RE.match(code))


def normalize_cnpj(raw: str) -> str:
    return re.sub(r"\D+", "", (raw or "").strip())


def gym_commission_pct() -> int:
    try:
        n = int(os.getenv("EGO_GYM_COMMISSION_PCT", str(DEFAULT_COMMISSION_PCT)).strip())
    except ValueError:
        n = DEFAULT_COMMISSION_PCT
    return max(1, min(90, n))


def get_admin_client() -> Client | None:
    from ego_api.supabase_client import create_service_client

    return create_service_client()


def lookup_gym_partner(supabase: Client, code: str) -> dict | None:
    norm = normalize_partner_code(code)
    if not is_valid_partner_code(norm):
        return None
    res = (
        supabase.table(GYM_PARTNERS_TABLE)
        .select("*")
        .eq("partner_code", norm)
        .eq("active", True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def partner_checkout_path(code: str) -> str:
    """URL pública checkout academia (g.html → /checkout/gym/)."""
    base = (
        os.getenv("EGO_SITE_URL")
        or os.getenv("EXPO_PUBLIC_WEBSITE_URL")
        or "https://egoai.com.br"
    ).rstrip("/")
    return f"{base}/g.html?c={normalize_partner_code(code)}"


def partner_public_payload(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "partner_code": row.get("partner_code"),
        "name": row.get("name"),
        "logo_url": row.get("logo_url"),
        "commission_pct": int(row.get("commission_pct") or gym_commission_pct()),
        "active": bool(row.get("active", True)),
    }


def resolve_connect_account_id(row: dict | None) -> str | None:
    """Conta Connect: coluna DB ou EGO_PARTNERS_JSON.gyms.<code>.stripe_account."""
    if row:
        acct = str(row.get("stripe_connect_account_id") or "").strip()
        if acct.startswith("acct_"):
            return acct
        code = normalize_partner_code(str(row.get("partner_code") or ""))
    else:
        code = ""
    if not code:
        return None
    raw = (os.getenv("EGO_PARTNERS_JSON") or "").strip()
    if not raw:
        return None
    try:
        import json

        data = json.loads(raw)
        gyms = (data.get("gyms") or {}) if isinstance(data, dict) else {}
        entry = gyms.get(code.lower()) or gyms.get(code)
        if isinstance(entry, dict):
            acct = str(entry.get("stripe_account") or entry.get("account") or "").strip()
            if acct.startswith("acct_"):
                return acct
    except Exception:
        pass
    return None


def set_profile_gym_code(
    supabase: Client, user_id: str, raw_code: str
) -> tuple[dict | None, str | None]:
    """
    Liga profiles.gym_code de forma permanente (só zera ao apagar conta).
    Não troca se já houver outro código.
    """
    code = normalize_partner_code(raw_code)
    if not is_valid_partner_code(code):
        return None, "Código de academia inválido."
    partner = lookup_gym_partner(supabase, code)
    if not partner:
        return None, "Academia não encontrada ou inativa."

    from ego_api import db as ego_db

    prof = ego_db.load_profile_trusted(supabase, user_id) or {}
    existing = normalize_partner_code(str(prof.get("gym_code") or ""))
    if existing and existing != code:
        return None, (
            "Já tens academia vinculada. O vínculo é permanente enquanto a conta existir."
        )
    try:
        supabase.table(ego_db.SUPABASE_PROFILES_TABLE).update(
            {"gym_code": code}
        ).eq("id", user_id).execute()
    except Exception as exc:
        return None, f"Não foi possível gravar gym_code: {exc}"
    return partner_public_payload(partner), None


def get_profile_gym_partner(
    supabase: Client, user_id: str
) -> tuple[str | None, dict | None]:
    from ego_api import db as ego_db

    prof = ego_db.load_profile_trusted(supabase, user_id) or {}
    code = normalize_partner_code(str(prof.get("gym_code") or ""))
    if not code:
        return None, None
    partner = lookup_gym_partner(supabase, code)
    return code, partner_public_payload(partner)
