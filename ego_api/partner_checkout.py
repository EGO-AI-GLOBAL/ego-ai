"""Checkout Stripe Connect — perfil com partner/gym_code (~30% parceiro, ~70% EGO)."""

from __future__ import annotations

import os
from typing import Any

from ego_api.gym_partners import (
    get_admin_client,
    gym_commission_pct,
    lookup_gym_partner,
    normalize_partner_code,
    resolve_connect_account_id,
)

# Premium mensal R$ 49,90 (centavos) — alinhado à loja / Stripe Payment Link.
PRICE_CENTS = 4990


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


def create_gym_checkout(code: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    Session Checkout assinatura Premium com transfer_data → parceiro.
    application_fee_percent = 100 - commission_pct (default parceiro 30% → fee 70%).
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
            "Define stripe_connect_account_id ou EGO_PARTNERS_JSON."
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

    site = (
        os.getenv("EGO_SITE_URL")
        or os.getenv("EXPO_PUBLIC_WEBSITE_URL")
        or "https://egoai.com.br"
    ).rstrip("/")
    success = f"{site}/planos/?gym=1&c={norm}&ok=1"
    cancel = f"{site}/g.html?c={norm}&cancel=1"

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success,
            cancel_url=cancel,
            subscription_data={
                "application_fee_percent": fee_percent,
                "transfer_data": {"destination": acct},
                "metadata": {
                    "plan": "premium",
                    "channel": "gym",
                    "partner_code": norm,
                    "partner_name": str(row.get("name") or norm),
                    "commission_pct": str(commission),
                    "platform_fee_percent": str(fee_percent),
                },
            },
            metadata={
                "plan": "premium",
                "channel": "gym",
                "partner_code": norm,
            },
        )
    except Exception as exc:
        return None, f"Stripe Checkout falhou: {exc}"

    url = getattr(session, "url", None) or (session.get("url") if isinstance(session, dict) else None)
    if not url:
        return None, "Stripe não devolveu URL de checkout."
    return {
        "ok": True,
        "url": url,
        "partner_code": norm,
        "commission_pct": commission,
        "application_fee_percent": fee_percent,
    }, None
