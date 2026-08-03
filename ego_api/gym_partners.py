"""Parceiros B2B (canal Connect) — separado de referral_partners (influencers).

Tabela gym_partners + profiles.gym_code / partner_coupon_code.
Parceiro = academia, clínica, consultório, médico, empresa, etc.
"""

from __future__ import annotations

import os
import re
from typing import Any

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

GYM_PARTNERS_TABLE = "gym_partners"
PARTNER_APPLICATIONS_TABLE = "partner_applications"
_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,31}$")
DEFAULT_COMMISSION_PCT = 30
# Premium Voice R$ 49,90
PREMIUM_PRICE_CENTS = 4990


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
    """Busca parceiro ativo por partner_code (ex. GYM_MURIAE_01)."""
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


def lookup_gym_partner_by_id(supabase: Client, partner_id: str) -> dict | None:
    pid = (partner_id or "").strip()
    if not pid:
        return None
    res = (
        supabase.table(GYM_PARTNERS_TABLE)
        .select("*")
        .eq("id", pid)
        .eq("active", True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def partner_checkout_path(code: str) -> str:
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
        "id": row.get("id"),
        "partner_code": row.get("partner_code"),
        "name": row.get("name"),
        "logo_url": row.get("logo_url"),
        "commission_pct": int(row.get("commission_pct") or gym_commission_pct()),
        "active": bool(row.get("active", True)),
    }


def resolve_connect_account_id(row: dict | None) -> str | None:
    """Conta Connect: stripe_connect_account_id | stripe_account_id | EGO_PARTNERS_JSON."""
    if row:
        for key in ("stripe_connect_account_id", "stripe_account_id"):
            acct = str(row.get(key) or "").strip()
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
        gyms = (data.get("gyms") or data.get("partners") or {}) if isinstance(data, dict) else {}
        entry = gyms.get(code.lower()) or gyms.get(code)
        if isinstance(entry, dict):
            acct = str(
                entry.get("stripe_account")
                or entry.get("stripe_account_id")
                or entry.get("account")
                or ""
            ).strip()
            if acct.startswith("acct_"):
                return acct
    except Exception:
        pass
    return None


def profile_partner_code(prof: dict | None) -> str:
    """Lê partner_coupon_code ou gym_code do perfil."""
    if not prof:
        return ""
    return normalize_partner_code(
        str(prof.get("partner_coupon_code") or prof.get("gym_code") or "")
    )


def set_profile_gym_code(
    supabase: Client, user_id: str, raw_code: str
) -> tuple[dict | None, str | None]:
    """
    Liga partner_coupon_code + gym_code (permanente).
    Não troca se já houver outro código.
    """
    code = normalize_partner_code(raw_code)
    if not is_valid_partner_code(code):
        return None, "Código de parceiro inválido."
    partner = lookup_gym_partner(supabase, code)
    if not partner:
        return None, "Parceiro não encontrado ou inativo."

    from ego_api import db as ego_db

    prof = ego_db.load_profile_trusted(supabase, user_id) or {}
    existing = profile_partner_code(prof)
    if existing and existing != code:
        return None, (
            "Já tens um parceiro vinculado. O vínculo é permanente enquanto a conta existir."
        )
    payload = {
        "gym_code": code,
        "partner_coupon_code": code,
    }
    try:
        supabase.table(ego_db.SUPABASE_PROFILES_TABLE).update(payload).eq(
            "id", user_id
        ).execute()
    except Exception as exc:
        # Coluna partner_coupon_code pode ainda não existir — grava só gym_code
        try:
            supabase.table(ego_db.SUPABASE_PROFILES_TABLE).update(
                {"gym_code": code}
            ).eq("id", user_id).execute()
        except Exception as exc2:
            return None, f"Não foi possível gravar código do parceiro: {exc2}"
        print(f"[EGO] partner_coupon_code write fallback: {exc}", flush=True)
    return partner_public_payload(partner), None


def get_profile_gym_partner(
    supabase: Client, user_id: str
) -> tuple[str | None, dict | None]:
    from ego_api import db as ego_db

    prof = ego_db.load_profile_trusted(supabase, user_id) or {}
    code = profile_partner_code(prof)
    if not code:
        return None, None
    partner = lookup_gym_partner(supabase, code)
    return code, partner_public_payload(partner)


def split_amounts_cents(
    total_cents: int = PREMIUM_PRICE_CENTS, commission_pct: int | None = None
) -> dict[str, int]:
    """R$ 49,90 → parceiro ≈ R$ 14,97 (30%) · EGO ≈ R$ 34,93 (70%)."""
    pct = int(commission_pct if commission_pct is not None else gym_commission_pct())
    pct = max(1, min(90, pct))
    partner = int(round(total_cents * pct / 100.0))
    platform = max(0, total_cents - partner)
    return {
        "amount_total_cents": total_cents,
        "partner_share_cents": partner,
        "platform_share_cents": platform,
        "commission_pct": pct,
    }
