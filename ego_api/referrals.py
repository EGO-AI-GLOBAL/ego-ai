"""
Programa de indicação: código no cadastro, 10% na 1ª compra (Stripe), R$ 10 ao parceiro no 1º pagamento.
"""

from __future__ import annotations

import csv
import io
import os
import re
from datetime import datetime, timezone
from typing import Any

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

COMMISSION_CENTS_BRL = 1000  # R$ 10,00
_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,31}$")


def normalize_referral_code(raw: str) -> str:
    return (raw or "").strip().upper().replace(" ", "")


def is_valid_code_format(code: str) -> bool:
    return bool(code and _CODE_RE.match(code))


def referral_promo_code() -> str:
    """Código promocional Stripe (10% 1ª compra) — prefilled nos Payment Links."""
    return os.getenv("STRIPE_REFERRAL_PROMO_CODE", "").strip()


def admin_api_key() -> str:
    return os.getenv("REFERRAL_ADMIN_SECRET", "").strip() or os.getenv(
        "EGO_ADMIN_API_KEY", ""
    ).strip()


def get_admin_client() -> Client | None:
    from ego_api.supabase_client import create_service_client

    return create_service_client()


def lookup_partner(supabase: Client, code: str) -> dict | None:
    norm = normalize_referral_code(code)
    if not is_valid_code_format(norm):
        return None
    row = (
        supabase.table("referral_partners")
        .select("id, code, display_name, active")
        .eq("code", norm)
        .eq("active", True)
        .limit(1)
        .execute()
    )
    data = row.data or []
    return data[0] if data else None


def validate_referral_code(code: str) -> tuple[dict | None, str | None]:
    client = get_admin_client()
    if not client:
        return None, "Serviço indisponível."
    norm = normalize_referral_code(code)
    if not norm:
        return None, None
    if not is_valid_code_format(norm):
        return None, "Código inválido."
    partner = lookup_partner(client, norm)
    if not partner:
        return None, "Código não encontrado ou inativo."
    return {
        "code": partner["code"],
        "display_name": partner.get("display_name") or partner["code"],
    }, None


def attach_referral_to_profile(
    supabase: Client, user_id: str, referral_code: str
) -> tuple[bool, str | None]:
    """Grava indicação no perfil (somente se ainda não tiver parceiro)."""
    norm = normalize_referral_code(referral_code)
    if not norm:
        return True, None
    if not is_valid_code_format(norm):
        return False, "Código de indicação inválido."
    admin = get_admin_client() or supabase
    partner = lookup_partner(admin, norm)
    if not partner:
        return False, "Código de indicação não encontrado."

    row = (
        supabase.table("profiles")
        .select("referred_by_partner_id, referral_first_paid_at")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not row.data:
        return False, "Perfil não encontrado."
    prof = row.data[0]
    if prof.get("referred_by_partner_id"):
        return True, None
    if prof.get("referral_first_paid_at"):
        return False, "Indicação só pode ser usada no primeiro cadastro."

    supabase.table("profiles").update(
        {"referred_by_partner_id": partner["id"]}
    ).eq("id", user_id).execute()
    return True, None


def user_eligible_for_referral_discount(profile: dict | None) -> bool:
    if not profile:
        return False
    if profile.get("referral_first_paid_at"):
        return False
    if not profile.get("referred_by_partner_id"):
        return False
    promo = referral_promo_code()
    return bool(promo)


def append_referral_promo_to_url(url: str, profile: dict | None) -> str:
    base = (url or "").strip()
    if not base or not user_eligible_for_referral_discount(profile):
        return base
    promo = referral_promo_code()
    if not promo:
        return base
    if "prefilled_promo_code=" in base:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}prefilled_promo_code={promo}"


def record_first_payment_commission(
    supabase: Client,
    user_id: str,
    *,
    stripe_session_id: str = "",
) -> dict[str, Any] | None:
    """Cria comissão R$ 10 (uma vez) e marca referral_first_paid_at."""
    row = (
        supabase.table("profiles")
        .select("referred_by_partner_id, referral_first_paid_at, email")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    prof = row.data[0]
    partner_id = prof.get("referred_by_partner_id")
    if not partner_id:
        return None
    if prof.get("referral_first_paid_at"):
        return {"skipped": "already_paid"}

    now = datetime.now(timezone.utc)
    payout_month = now.strftime("%Y-%m")

    existing = (
        supabase.table("referral_commissions")
        .select("id")
        .eq("referred_user_id", user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        supabase.table("profiles").update(
            {"referral_first_paid_at": now.isoformat()}
        ).eq("id", user_id).execute()
        return {"skipped": "commission_exists"}

    supabase.table("referral_commissions").insert(
        {
            "partner_id": partner_id,
            "referred_user_id": user_id,
            "stripe_session_id": (stripe_session_id or "")[:200] or None,
            "amount_cents": COMMISSION_CENTS_BRL,
            "currency": "brl",
            "status": "pending",
            "payout_month": payout_month,
        }
    ).execute()

    supabase.table("profiles").update(
        {"referral_first_paid_at": now.isoformat()}
    ).eq("id", user_id).execute()

    return {
        "partner_id": str(partner_id),
        "amount_cents": COMMISSION_CENTS_BRL,
        "payout_month": payout_month,
    }


def create_partner(
    *,
    code: str,
    display_name: str,
    contact_email: str = "",
    payout_pix: str = "",
    notes: str = "",
) -> tuple[dict | None, str | None]:
    client = get_admin_client()
    if not client:
        return None, "Supabase admin não configurado."
    norm = normalize_referral_code(code)
    if not is_valid_code_format(norm):
        return None, "Código deve ter 3–32 caracteres (letras, números, _ ou -)."
    name = (display_name or norm).strip()[:120]
    try:
        res = (
            client.table("referral_partners")
            .insert(
                {
                    "code": norm,
                    "display_name": name,
                    "contact_email": (contact_email or "").strip()[:254] or None,
                    "payout_pix": (payout_pix or "").strip()[:120] or None,
                    "notes": (notes or "").strip()[:500] or None,
                    "active": True,
                }
            )
            .execute()
        )
        return (res.data or [{}])[0], None
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            return None, "Este código já existe."
        return None, str(exc)


def commissions_report_csv(month: str) -> tuple[str, str | None]:
    """month: YYYY-MM. Retorna (csv_text, erro)."""
    if not re.match(r"^\d{4}-\d{2}$", month or ""):
        return "", "Mês inválido (use YYYY-MM)."
    client = get_admin_client()
    if not client:
        return "", "Supabase admin não configurado."

    comm = (
        client.table("referral_commissions")
        .select(
            "id, amount_cents, currency, status, payout_month, created_at, paid_out_at, "
            "referred_user_id, stripe_session_id, "
            "partner:referral_partners(code, display_name, contact_email, payout_pix)"
        )
        .eq("payout_month", month)
        .order("created_at")
        .execute()
    )
    rows = comm.data or []

    user_ids = [r["referred_user_id"] for r in rows if r.get("referred_user_id")]
    emails: dict[str, str] = {}
    if user_ids:
        prof = (
            client.table("profiles")
            .select("id, email")
            .in_("id", user_ids)
            .execute()
        )
        for p in prof.data or []:
            emails[str(p["id"])] = p.get("email") or ""

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(
        [
            "mes",
            "codigo_parceiro",
            "nome_parceiro",
            "email_parceiro",
            "pix_parceiro",
            "email_indicado",
            "valor_comissao_brl",
            "status",
            "data_comissao",
            "stripe_session_id",
        ]
    )

    totals: dict[str, int] = {}
    for r in rows:
        partner = r.get("partner") or {}
        if isinstance(partner, list):
            partner = partner[0] if partner else {}
        code = partner.get("code") or ""
        cents = int(r.get("amount_cents") or COMMISSION_CENTS_BRL)
        totals[code] = totals.get(code, 0) + cents
        w.writerow(
            [
                month,
                code,
                partner.get("display_name") or "",
                partner.get("contact_email") or "",
                partner.get("payout_pix") or "",
                emails.get(str(r.get("referred_user_id")), ""),
                f"{cents / 100:.2f}",
                r.get("status") or "pending",
                (r.get("created_at") or "")[:19],
                r.get("stripe_session_id") or "",
            ]
        )

    w.writerow([])
    w.writerow(["RESUMO_POR_PARCEIRO"])
    w.writerow(["codigo_parceiro", "total_brl", "qtd_indicacoes"])
    counts: dict[str, int] = {}
    for r in rows:
        partner = r.get("partner") or {}
        if isinstance(partner, list):
            partner = partner[0] if partner else {}
        c = partner.get("code") or ""
        if c:
            counts[c] = counts.get(c, 0) + 1
    for code, total_cents in sorted(totals.items()):
        w.writerow([code, f"{total_cents / 100:.2f}", counts.get(code, 0)])

    return buf.getvalue(), None


def partner_signup_link(code: str, *, app_base: str = "") -> str:
    base = (app_base or os.getenv("EGO_APP_SIGNUP_URL", "https://egoai.com.br/signup")).rstrip(
        "/"
    )
    norm = normalize_referral_code(code)
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}ref={norm}"
