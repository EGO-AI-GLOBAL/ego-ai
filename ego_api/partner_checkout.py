"""Checkout Stripe Connect — Premium Voz R$ 49,90 · split 30% parceiro / 70% EGO.

Usa Destination Charges na Assinatura:
  transfer_data.destination = acct_parceiro
  application_fee_percent = 70  (EGO fica com 70%; parceiro recebe ~30% automático)

NÃO criar Transfer manual no webhook — duplicaria a comissão.
O webhook só audita em partner_revenue_ledger.
"""

from __future__ import annotations

import os
from typing import Any

from ego_api.gym_partners import (
    PREMIUM_PRICE_CENTS,
    get_admin_client,
    get_profile_gym_partner,
    gym_commission_pct,
    lookup_gym_partner,
    normalize_partner_code,
    resolve_connect_account_id,
    split_amounts_cents,
)


def _stripe():
    key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not key:
        return None, "Stripe não configurado (STRIPE_SECRET_KEY)."
    try:
        import stripe
    except ImportError:
        return None, "Pacote stripe em falta no servidor."
    stripe.api_key = key
    return stripe, None


def _premium_price_id() -> str:
    return (
        os.getenv("STRIPE_GYM_PREMIUM_PRICE_ID")
        or os.getenv("STRIPE_PRICE_PREMIUM")
        or os.getenv("STRIPE_PRICE_CONNECTION")
        or ""
    ).strip()


def create_gym_checkout(
    code: str, *, user_id: str | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Session Checkout assinatura Premium Voice com split Connect.
    application_fee_percent = 100 - commission_pct (default 30% parceiro → fee 70%).
    """
    norm = normalize_partner_code(code)
    sb = get_admin_client()
    if not sb:
        return None, "Supabase não configurado."
    row = lookup_gym_partner(sb, norm)
    if not row:
        return None, "Parceiro não encontrado ou inativo."

    acct = resolve_connect_account_id(row)
    if not acct:
        return None, (
            "Parceiro sem Stripe Connect ainda. "
            "Define stripe_connect_account_id / stripe_account_id ou EGO_PARTNERS_JSON."
        )

    stripe, err = _stripe()
    if err:
        return None, err

    price_id = _premium_price_id()
    if not price_id:
        return None, (
            "Falta STRIPE_GYM_PREMIUM_PRICE_ID (ou STRIPE_PRICE_PREMIUM) no Railway."
        )

    commission = int(row.get("commission_pct") or gym_commission_pct())
    commission = max(1, min(90, commission))
    fee_percent = round(100.0 - float(commission), 2)
    amounts = split_amounts_cents(PREMIUM_PRICE_CENTS, commission)

    site = (
        os.getenv("EGO_SITE_URL")
        or os.getenv("EXPO_PUBLIC_WEBSITE_URL")
        or "https://egoai.com.br"
    ).rstrip("/")
    success = f"{site}/planos/?partner=1&c={norm}&ok=1"
    cancel = f"{site}/g.html?c={norm}&cancel=1"

    uid = (user_id or "").strip() or None
    session_meta = {
        "plan": "premium",
        "channel": "partner",
        "partner_code": norm,
        "partner_coupon_code": norm,
        "partner_name": str(row.get("name") or norm),
        "commission_pct": str(commission),
        "platform_fee_percent": str(fee_percent),
        "partner_share_cents": str(amounts["partner_share_cents"]),
        "platform_share_cents": str(amounts["platform_share_cents"]),
        "split_mode": "connect_destination",
    }
    if uid:
        session_meta["user_id"] = uid

    try:
        kwargs: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success,
            "cancel_url": cancel,
            "subscription_data": {
                "application_fee_percent": fee_percent,
                "transfer_data": {"destination": acct},
                "metadata": session_meta,
            },
            "metadata": session_meta,
        }
        if uid:
            kwargs["client_reference_id"] = uid
        session = stripe.checkout.Session.create(**kwargs)
    except Exception as exc:
        return None, f"Stripe Checkout falhou: {exc}"

    url = getattr(session, "url", None) or (
        session.get("url") if isinstance(session, dict) else None
    )
    if not url:
        return None, "Stripe não devolveu URL de checkout."
    return {
        "ok": True,
        "url": url,
        "partner_code": norm,
        "partner_coupon_code": norm,
        "commission_pct": commission,
        "application_fee_percent": fee_percent,
        "partner_share_brl": round(amounts["partner_share_cents"] / 100.0, 2),
        "platform_share_brl": round(amounts["platform_share_cents"] / 100.0, 2),
        "amount_brl": round(PREMIUM_PRICE_CENTS / 100.0, 2),
        "split_mode": "connect_destination",
        "note": (
            "Split automático no Stripe Connect (não usar Transfer manual no webhook)."
        ),
    }, None


def create_checkout_for_user(user_id: str) -> tuple[dict[str, Any] | None, str | None]:
    """Lê partner_coupon_code do perfil e gera Checkout Connect; orgânico → erro claro."""
    sb = get_admin_client()
    if not sb:
        return None, "Supabase não configurado."
    code, partner = get_profile_gym_partner(sb, user_id)
    if not code or not partner:
        return None, (
            "Sem código de parceiro no perfil. "
            "Utilizadores orgânicos usam IAP nas lojas."
        )
    return create_gym_checkout(code, user_id=user_id)
